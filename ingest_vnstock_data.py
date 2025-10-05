#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script để ingest dữ liệu tài chính từ VNStock vào Qdrant Vector Database với 32 workers

Usage:
    python ingest_vnstock_data.py --all               # Ingest tất cả symbol (APPEND - mặc định)
    python ingest_vnstock_data.py VCI HPG FPT         # Ingest các symbol cụ thể (APPEND)
    python ingest_vnstock_data.py --all --delete      # XÓA collection cũ và ingest tất cả
    python ingest_vnstock_data.py VCI --delete        # XÓA collection cũ và ingest VCI
"""

import sys
import argparse
import requests
import json
from qdrant_client import QdrantClient, models
from config import Config
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from threading import Lock
from vnstock_data import Listing, Finance
import time
from datetime import datetime


# ---------- EMBEDDING ----------
def get_embedding(text: str, show_time: bool = False):
    """Get embedding from OpenAI API"""
    headers = {
        "Authorization": f"Bearer {Config.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": Config.EMBEDDING_MODEL,
        "input": text
    }
    max_retries = 3
    for attempt in range(max_retries):
        try:
            api_start = time.time()
            resp = requests.post(f"{Config.OPENAI_BASE}/embeddings", headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            api_time = time.time() - api_start
            
            if show_time and api_time > 2:  # Log nếu API chậm > 2s
                print(f"      ⏱️  API embedding mất {api_time:.2f}s")
            
            return resp.json()["data"][0]["embedding"]
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"      ⚠️  Lỗi API (attempt {attempt+1}/{max_retries}), retry sau 1s...")
                time.sleep(1)
                continue
            else:
                raise e


# ---------- LẤY DANH SÁCH SYMBOL ----------
def get_all_symbols():
    """Lấy danh sách tất cả mã cổ phiếu từ VNStock"""
    print("📋 Đang lấy danh sách tất cả mã cổ phiếu...")
    try:
        listing = Listing(source='VCI')
        df = listing.all_symbols()
        symbols = df['ticker'].tolist() if 'ticker' in df.columns else df['symbol'].tolist()
        print(f"✅ Đã lấy {len(symbols)} mã cổ phiếu")
        return symbols
    except Exception as e:
        print(f"❌ Lỗi khi lấy danh sách symbol: {e}")
        return []


# ---------- LẤY DỮ LIỆU TÀI CHÍNH TỪ VNSTOCK ----------
def fetch_financial_data(symbol: str):
    """
    Lấy dữ liệu tài chính từ VNStock cho một symbol
    Bao gồm: Balance Sheet, Income Statement, Cash Flow
    """
    try:
        print(f"  🔹 Đang lấy dữ liệu cho {symbol}...")
        fin = Finance(symbol=symbol, period='year', source='VCI')
        
        data_blocks = []
        
        # 1. Balance Sheet (Bảng cân đối kế toán)
        try:
            balance_sheet = fin.balance_sheet(lang='vi')
            if balance_sheet is not None and not balance_sheet.empty:
                data_blocks.append({
                    'type': 'balance_sheet',
                    'data': balance_sheet.to_dict(orient='records'),
                    'name': 'Bảng cân đối kế toán'
                })
        except Exception as e:
            print(f"    ⚠️  Không lấy được Balance Sheet cho {symbol}: {e}")
        
        # 2. Income Statement (Báo cáo kết quả kinh doanh)
        try:
            income_statement = fin.income_statement(lang='vi')
            if income_statement is not None and not income_statement.empty:
                data_blocks.append({
                    'type': 'income_statement',
                    'data': income_statement.to_dict(orient='records'),
                    'name': 'Báo cáo kết quả kinh doanh'
                })
        except Exception as e:
            print(f"    ⚠️  Không lấy được Income Statement cho {symbol}: {e}")
        
        # 3. Cash Flow (Báo cáo lưu chuyển tiền tệ)
        try:
            cash_flow = fin.cash_flow(lang='vi')
            if cash_flow is not None and not cash_flow.empty:
                data_blocks.append({
                    'type': 'cash_flow',
                    'data': cash_flow.to_dict(orient='records'),
                    'name': 'Báo cáo lưu chuyển tiền tệ'
                })
        except Exception as e:
            print(f"    ⚠️  Không lấy được Cash Flow cho {symbol}: {e}")
        
        print(f"  ✅ Đã lấy {len(data_blocks)} loại báo cáo cho {symbol}")
        return data_blocks
        
    except Exception as e:
        print(f"  ❌ Lỗi khi lấy dữ liệu cho {symbol}: {e}")
        return []


# ---------- CHUYỂN DỮ LIỆU THÀNH TEXT ----------
def financial_data_to_text(symbol: str, data_blocks: list):
    """
    Chuyển đổi dữ liệu tài chính thành các đoạn text có ý nghĩa
    Mỗi đoạn text đại diện cho một nhóm chỉ tiêu tài chính
    """
    texts = []
    
    for block in data_blocks:
        block_type = block['type']
        block_name = block['name']
        data = block['data']
        
        if not data:
            continue
        
        # Gộp các record theo năm
        for record in data:
            # Lọc các chỉ tiêu có giá trị
            metrics = []
            period_info = ""
            
            for key, value in record.items():
                # Skip null, empty, or zero values
                if value is None or value == "" or value == 0:
                    continue
                
                # Lấy thông tin kỳ báo cáo
                if key in ['report_period', 'year', 'quarter', 'Mã CP']:
                    if key == 'Mã CP':
                        continue  # Skip vì đã có trong metadata
                    period_info += f" {key}: {value}"
                else:
                    # Format giá trị
                    if isinstance(value, (int, float)):
                        metrics.append(f"{key}: {value:,.0f}")
                    else:
                        metrics.append(f"{key}: {value}")
            
            # Tạo text chunk (giới hạn 50 chỉ tiêu mỗi chunk để tránh quá dài)
            if metrics:
                chunk_size = 50
                for i in range(0, len(metrics), chunk_size):
                    chunk_metrics = metrics[i:i+chunk_size]
                    text = f"Mã cổ phiếu: {symbol}\n"
                    text += f"Loại báo cáo: {block_name}\n"
                    if period_info:
                        text += f"Kỳ báo cáo:{period_info}\n"
                    text += "\n" + "\n".join(chunk_metrics)
                    
                    texts.append({
                        'text': text,
                        'type': block_type,
                        'name': block_name
                    })
    
    return texts


# ---------- XỬ LÝ MỘT SYMBOL ----------
def process_single_symbol(symbol: str, qdrant_client, collection_name: str, offset_id: int, lock: Lock):
    """
    Xử lý một symbol: lấy dữ liệu, tạo embedding, và lưu vào Qdrant
    """
    try:
        start_time = time.time()
        
        # 1. Lấy dữ liệu
        data_blocks = fetch_financial_data(symbol)
        if not data_blocks:
            return 0, symbol, "No data"
        
        # 2. Chuyển thành text
        text_chunks = financial_data_to_text(symbol, data_blocks)
        if not text_chunks:
            return 0, symbol, "No text chunks"
        
        print(f"  📝 {symbol}: Đã tạo {len(text_chunks)} text chunks, bắt đầu embedding song song...")
        
        # 3. Tạo embedding và points SONG SONG với ThreadPool
        points = []
        embedding_start = time.time()
        
        def create_embedding_for_chunk(idx_chunk):
            idx, chunk = idx_chunk
            try:
                embedding = get_embedding(chunk['text'], show_time=False)
                
                with lock:
                    point_id = offset_id[0]
                    offset_id[0] += 1
                
                return {
                    'id': point_id,
                    'embedding': embedding,
                    'chunk': chunk,
                    'idx': idx
                }
            except Exception as e:
                print(f"    ⚠️  Lỗi khi tạo embedding cho chunk {idx} của {symbol}: {e}")
                return None
        
        # Xử lý song song với 10 workers cho mỗi symbol (tránh quá tải API)
        with ThreadPoolExecutor(max_workers=10) as embed_executor:
            embedding_futures = list(embed_executor.map(create_embedding_for_chunk, enumerate(text_chunks)))
        
        # Tạo points từ kết quả
        successful_embeddings = [f for f in embedding_futures if f is not None]
        for result in successful_embeddings:
            point = models.PointStruct(
                id=result['id'],
                vector=result['embedding'],
                payload={
                    'ticker': symbol,
                    'text': result['chunk']['text'],
                    'type': result['chunk']['type'],
                    'report_name': result['chunk']['name'],
                    'timestamp': datetime.now().isoformat()
                }
            )
            points.append(point)
        
        embedding_time = time.time() - embedding_start
        print(f"    ⚡ {symbol}: Hoàn thành {len(points)}/{len(text_chunks)} embeddings trong {embedding_time:.2f}s")
        
        # 4. Lưu vào Qdrant
        if points:
            upsert_start = time.time()
            qdrant_client.upsert(collection_name=collection_name, points=points)
            upsert_time = time.time() - upsert_start
            total_time = time.time() - start_time
            
            print(f"  ✅ {symbol}: Đã lưu {len(points)} điểm dữ liệu (total: {total_time:.2f}s, upsert: {upsert_time:.2f}s)")
            return len(points), symbol, "Success"
        else:
            return 0, symbol, "No points created"
            
    except Exception as e:
        print(f"  ❌ Lỗi khi xử lý {symbol}: {e}")
        return 0, symbol, str(e)


# ---------- INGEST VÀO QDRANT ----------
def ingest_to_qdrant(symbols: list, recreate_collection: bool = True, max_workers: int = 32):
    """
    Ingest dữ liệu tài chính vào Qdrant với multi-threading
    
    Args:
        symbols: Danh sách mã cổ phiếu
        recreate_collection: Nếu True, xóa và tạo lại collection
        max_workers: Số lượng worker song song
    """
    # 1. Kết nối Qdrant
    qdrant = QdrantClient(host=Config.QDRANT_HOST, port=Config.QDRANT_PORT)
    collection_name = Config.QDRANT_COLLECTION
    
    # 2. Tạo/kiểm tra collection
    if recreate_collection:
        if qdrant.collection_exists(collection_name):
            print(f"🗑️  XÓA collection cũ: {collection_name}")
            qdrant.delete_collection(collection_name)
        
        print(f"🆕 Tạo collection mới: {collection_name}")
        qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=3072, distance=models.Distance.COSINE)
        )
    else:
        if not qdrant.collection_exists(collection_name):
            print(f"🆕 Collection chưa tồn tại, tạo mới: {collection_name}")
            qdrant.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=3072, distance=models.Distance.COSINE)
            )
        else:
            print(f"➕ APPEND - Thêm dữ liệu vào collection hiện tại: {collection_name}")
    
    # 3. Get offset ID
    offset_id = [0]
    try:
        scroll_result = qdrant.scroll(
            collection_name=collection_name, 
            limit=1, 
            with_payload=False, 
            with_vectors=False
        )
        if scroll_result[0]:
            offset_id[0] = max([p.id for p in scroll_result[0]]) + 1
    except:
        offset_id[0] = 0
    
    # 4. Xử lý song song với ThreadPoolExecutor
    print(f"\n🚀 Bắt đầu xử lý {len(symbols)} symbol với {max_workers} workers...")
    print(f"💡 Mỗi symbol sẽ có 3 loại báo cáo, mỗi báo cáo có nhiều text chunks cần embedding\n")
    
    lock = Lock()
    results = []
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_single_symbol, symbol, qdrant, collection_name, offset_id, lock): symbol 
            for symbol in symbols
        }
        
        completed = 0
        for future in as_completed(futures):
            completed += 1
            symbol = futures[future]
            try:
                num_points, sym, status = future.result()
                results.append({'symbol': sym, 'points': num_points, 'status': status})
                elapsed = time.time() - start_time
                avg_time = elapsed / completed if completed > 0 else 0
                eta = avg_time * (len(symbols) - completed) if completed > 0 else 0
                print(f"\n📊 Tiến độ: {completed}/{len(symbols)} ({completed*100//len(symbols)}%) | Thời gian: {elapsed:.1f}s | ETA: {eta:.1f}s\n")
            except Exception as e:
                print(f"  ❌ Lỗi khi xử lý {symbol}: {e}")
                results.append({'symbol': symbol, 'points': 0, 'status': f'Error: {e}'})
    
    # 5. Tổng kết
    elapsed_time = time.time() - start_time
    total_points = sum(r['points'] for r in results)
    success_count = sum(1 for r in results if r['points'] > 0)
    
    print("\n" + "="*60)
    print("📊 KẾT QUẢ TỔNG HỢP")
    print("="*60)
    print(f"⏱️  Thời gian: {elapsed_time:.2f} giây")
    print(f"✅ Thành công: {success_count}/{len(symbols)} symbol")
    print(f"💾 Tổng số điểm dữ liệu: {total_points:,}")
    print(f"⚡ Tốc độ: {len(symbols)/elapsed_time:.2f} symbol/giây")
    
    # Chi tiết các symbol thất bại
    failed = [r for r in results if r['points'] == 0]
    if failed:
        print(f"\n⚠️  Các symbol thất bại ({len(failed)}):")
        for r in failed[:10]:  # Hiển thị 10 symbol đầu tiên
            print(f"  - {r['symbol']}: {r['status']}")
        if len(failed) > 10:
            print(f"  ... và {len(failed)-10} symbol khác")
        
        # Lưu danh sách symbol thất bại vào file
        failed_file = 'failed_symbols.txt'
        with open(failed_file, 'w') as f:
            for r in failed:
                f.write(f"{r['symbol']}\t{r['status']}\n")
        print(f"\n💾 Đã lưu danh sách {len(failed)} symbol thất bại vào: {failed_file}")
        print(f"💡 Retry: python ingest_vnstock_data.py --retry {failed_file}")
    
    return results


# ---------- MAIN ----------
def main():
    parser = argparse.ArgumentParser(
        description='Ingest dữ liệu tài chính từ VNStock vào Qdrant',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
  python ingest_vnstock_data.py --all                   # Ingest tất cả symbol (APPEND - mặc định)
  python ingest_vnstock_data.py VCI HPG FPT             # Ingest các symbol cụ thể (APPEND)
  python ingest_vnstock_data.py --all --workers 64      # Dùng 64 workers (APPEND)
  python ingest_vnstock_data.py --all --delete          # XÓA collection cũ và tạo mới
  python ingest_vnstock_data.py VCI --delete            # Ingest VCI và XÓA collection cũ
  python ingest_vnstock_data.py --retry failed_symbols.txt  # Retry các symbol thất bại
        """
    )
    
    parser.add_argument('symbols', nargs='*', help='Danh sách mã cổ phiếu (để trống nếu dùng --all hoặc --retry)')
    parser.add_argument('--all', action='store_true', help='Ingest tất cả symbol từ VNStock')
    parser.add_argument('--retry', metavar='FILE', help='Retry các symbol từ file (ví dụ: failed_symbols.txt)')
    parser.add_argument('--workers', type=int, default=32, help='Số lượng workers song song (mặc định: 32)')
    parser.add_argument('--delete', action='store_true', help='XÓA collection cũ và tạo mới (mặc định: thêm vào collection hiện tại)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 VNSTOCK DATA INGESTION TOOL")
    print("=" * 60)
    print(f"🔧 Qdrant: {Config.QDRANT_HOST}:{Config.QDRANT_PORT}")
    print(f"📦 Collection: {Config.QDRANT_COLLECTION}")
    print(f"⚙️  Workers: {args.workers}")
    print(f"🔄 Mode: {'DELETE & RECREATE' if args.delete else 'APPEND (mặc định)'}")
    print("=" * 60 + "\n")
    
    # Lấy danh sách symbols
    if args.retry:
        # Đọc từ file retry
        try:
            with open(args.retry, 'r') as f:
                lines = f.readlines()
            symbols = [line.split('\t')[0].strip().upper() for line in lines if line.strip()]
            print(f"📂 Đọc {len(symbols)} symbol từ file: {args.retry}")
        except FileNotFoundError:
            print(f"❌ Không tìm thấy file: {args.retry}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Lỗi khi đọc file: {e}")
            sys.exit(1)
    elif args.all:
        symbols = get_all_symbols()
        if not symbols:
            print("❌ Không lấy được danh sách symbol!")
            sys.exit(1)
    elif args.symbols:
        symbols = [s.upper() for s in args.symbols]
    else:
        parser.print_help()
        sys.exit(1)
    
    print(f"\n📋 Sẽ xử lý {len(symbols)} mã cổ phiếu")
    
    # Confirm nếu xóa collection với nhiều symbol
    if len(symbols) > 50 and args.delete:
        response = input(f"\n⚠️  Bạn sắp xử lý {len(symbols)} symbol và XÓA toàn bộ dữ liệu cũ. Tiếp tục? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("❌ Đã hủy")
            sys.exit(0)
    
    # Ingest
    recreate = args.delete  # Chỉ recreate khi có flag --delete
    results = ingest_to_qdrant(symbols, recreate_collection=recreate, max_workers=args.workers)
    
    print("\n" + "="*60)
    print("✅ HOÀN TẤT!")
    print("="*60)


if __name__ == "__main__":
    main()

