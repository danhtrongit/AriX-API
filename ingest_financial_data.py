#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script để ingest dữ liệu tài chính vào Qdrant Vector Database

Usage:
    python ingest_financial_data.py VIC
    python ingest_financial_data.py HPG FPT VIC
"""

import sys
import requests
from qdrant_client import QdrantClient, models
from config import Config
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# ---------- EMBEDDING ----------
def get_embedding(text: str):
    headers = {
        "Authorization": f"Bearer {Config.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": Config.EMBEDDING_MODEL,
        "input": text
    }
    resp = requests.post(f"{Config.OPENAI_BASE}/embeddings", headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


# ---------- LẤY DỮ LIỆU IQX ----------
def fetch_company_data(ticker: str):
    base = f"https://proxy.iqx.vn/proxy/trading/api/iq-insight-service/v1/company/{ticker}"
    sections = [
        "financial-statement/metrics",
        "financial-statement?section=CASH_FLOW",
        "financial-statement?section=INCOME_STATEMENT",
        "financial-statement?section=BALANCE_SHEET",
        "statistics-financial",
    ]

    data_blocks = []
    field_map = {}  # Lưu mapping field name -> readable name
    
    for s in sections:
        url = f"{base}/{s}"
        print(f"🔹 Fetching {url}")
        r = requests.get(url)
        if r.status_code == 200:
            content = r.json()
            data_blocks.append({"section": s, "content": content})
            
            # Nếu là metrics, lưu field mapping
            if s == "financial-statement/metrics" and "data" in content:
                for category, items in content["data"].items():
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict):
                                name = item.get("name", "")
                                title = item.get("titleVi") or item.get("titleEn", "")
                                if name and title:
                                    field_map[name.lower()] = title
        else:
            print(f"⚠️  Lỗi khi fetch {s}: {r.status_code}")
    
    return data_blocks, field_map


# ---------- CHUYỂN JSON THÀNH TEXT ----------
def flatten_json_to_text(section, data, field_map=None):
    texts = []
    if not isinstance(data, dict):
        return texts
    if "data" not in data:
        return texts

    raw_data = data["data"]
    
    # Case 1: data is a list (statistics-financial) - GỘP THEO KỲ BÁO CÁO
    if isinstance(raw_data, list):
        for item in raw_data:
            if not isinstance(item, dict):
                continue
            year = item.get("year", "")
            quarter = item.get("quarter", "")
            period = f"Q{quarter}/{year}" if quarter and year else str(year) if year else ""
            
            # Gộp các chỉ số quan trọng vào 1 đoạn text
            key_metrics = []
            important_fields = [
                "marketCap", "pe", "pb", "ps", "roe", "roa", "eps", "bvps",
                "grossMargin", "ebitMargin", "afterTaxProfitMargin",
                "currentRatio", "quickRatio", "debtPerEquity", "debtToEquity",
                "revenue", "grossProfit", "netProfit", "totalAssets", "totalEquity"
            ]
            
            for key in important_fields:
                value = item.get(key)
                if value is not None and value != "":
                    key_metrics.append(f"{key}: {value}")
            
            if key_metrics and period:
                line = f"{section} ({period})\n" + "\n".join(key_metrics)
                texts.append(line)
    
    # Case 2: data is a dict with categories (financial-statement)
    elif isinstance(raw_data, dict):
        # Case 2A: financial-statement với giá trị thực tế (có key 'years')
        if 'years' in raw_data and isinstance(raw_data['years'], list):
            # Sử dụng field_map được truyền vào (từ financial-statement/metrics)
            
            # Xử lý từng năm
            for year_data in raw_data['years'][-3:]:  # Lấy 3 năm gần nhất
                year = year_data.get('yearReport', '')
                if not year:
                    continue
                
                # Lấy các chỉ tiêu quan trọng
                year_metrics = []
                important_prefixes = ['cfa', 'isa', 'bsa']  # CASH_FLOW, INCOME_STATEMENT, BALANCE_SHEET
                
                for key, value in year_data.items():
                    if value is None or value == "" or value == 0:
                        continue
                    # Chỉ lấy các field bắt đầu bằng cfa, isa, bsa
                    if any(key.lower().startswith(prefix) for prefix in important_prefixes):
                        if field_map:
                            field_name = field_map.get(key.lower(), key.upper())
                        else:
                            field_name = key.upper()
                        year_metrics.append(f"{key.upper()}: {field_name} = {value:,.0f}")
                
                if year_metrics and year:
                    # Giới hạn 30 chỉ tiêu quan trọng nhất
                    line = f"{section} - Năm {year}\n" + "\n".join(year_metrics[:30])
                    texts.append(line)
        
        # Case 2B: financial-statement/metrics (chỉ metadata)
        else:
            for category, items in raw_data.items():
                if not isinstance(items, list):
                    continue
                
                # Gộp các chỉ tiêu trong cùng category
                category_items = []
                for item in items[:50]:  # Giới hạn 50 item đầu tiên
                    if not isinstance(item, dict):
                        continue
                    title = item.get("titleVi") or item.get("titleEn", "")
                    name = item.get("name", "")
                    if title and name:
                        category_items.append(f"{name}: {title}")
                
                if category_items:
                    line = f"{section} - {category}\n" + "\n".join(category_items)
                    texts.append(line)
    
    return texts


# ---------- NẠP DỮ LIỆU VÀO QDRANT ----------
def ingest_to_qdrant(ticker="VIC", recreate_collection=True):
    """
    Ingest financial data to Qdrant
    
    Args:
        ticker: Stock ticker symbol
        recreate_collection: If True, delete and recreate collection. 
                           If False, add to existing collection.
    """
    # 1️⃣ Kết nối
    qdrant = QdrantClient(host=Config.QDRANT_HOST, port=Config.QDRANT_PORT)

    # 2️⃣ Tạo/kiểm tra collection
    collection_name = Config.QDRANT_COLLECTION
    
    if recreate_collection:
        if qdrant.collection_exists(collection_name):
            print(f"🗑️  Xóa collection cũ: {collection_name}")
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
            print(f"➕ Thêm dữ liệu vào collection hiện tại: {collection_name}")

    # 3️⃣ Lấy dữ liệu IQX
    print(f"\n📈 Đang lấy dữ liệu cho mã {ticker}...")
    data_blocks, field_map = fetch_company_data(ticker)
    print(f"📋 Đã load {len(field_map)} field mappings")

    # 4️⃣ Tạo text & embedding với 128 workers song song
    all_texts = []
    for block in data_blocks:
        texts = flatten_json_to_text(block["section"], block["content"], field_map)
        for t in texts:
            all_texts.append({"text": t, "section": block["section"]})
    
    print(f"🚀 Bắt đầu xử lý {len(all_texts)} điểm dữ liệu với 128 workers...")
    
    points = []
    lock = Lock()
    processed_count = [0]
    
    # Get offset ID for multi-ticker ingestion
    if not recreate_collection:
        try:
            scroll_result = qdrant.scroll(collection_name=collection_name, limit=1, with_payload=False, with_vectors=False)
            if scroll_result[0]:
                offset_id = max([p.id for p in scroll_result[0]]) + 1
            else:
                offset_id = 0
        except:
            offset_id = 0
    else:
        offset_id = 0
    
    def process_text(idx, item):
        try:
            emb = get_embedding(item["text"])
            point = models.PointStruct(
                id=offset_id + idx,
                vector=emb,
                payload={"ticker": ticker, "text": item["text"], "section": item["section"]}
            )
            
            with lock:
                processed_count[0] += 1
                if processed_count[0] % 10 == 0:
                    print(f"📊 Đã xử lý {processed_count[0]}/{len(all_texts)} điểm dữ liệu...")
            
            return point
        except Exception as e:
            print(f"❌ Lỗi khi xử lý điểm {idx}: {e}")
            return None
    
    # Xử lý song song với ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=128) as executor:
        futures = {executor.submit(process_text, idx, item): idx for idx, item in enumerate(all_texts)}
        for future in as_completed(futures):
            point = future.result()
            if point:
                points.append(point)

    # 5️⃣ Ghi vào Qdrant
    print(f"💾 Đang ghi {len(points)} điểm vào Qdrant...")
    qdrant.upsert(collection_name=collection_name, points=points)
    print(f"✅ Đã nạp {len(points)} đoạn dữ liệu cho {ticker}.\n")


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 FINANCIAL DATA INGESTION SCRIPT")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("\n❌ Sử dụng: python ingest_financial_data.py <TICKER1> [TICKER2] ...")
        print("Ví dụ: python ingest_financial_data.py VIC")
        print("Ví dụ: python ingest_financial_data.py VIC HPG FPT\n")
        sys.exit(1)
    
    tickers = sys.argv[1:]
    print(f"\n📋 Danh sách mã cổ phiếu: {', '.join(tickers)}")
    print(f"🔧 Qdrant: {Config.QDRANT_HOST}:{Config.QDRANT_PORT}")
    print(f"📦 Collection: {Config.QDRANT_COLLECTION}\n")
    
    for i, ticker in enumerate(tickers):
        ticker = ticker.upper()
        print(f"\n{'='*60}")
        print(f"[{i+1}/{len(tickers)}] Processing {ticker}")
        print(f"{'='*60}")
        
        # First ticker: recreate collection, rest: add to collection
        recreate = (i == 0)
        ingest_to_qdrant(ticker, recreate_collection=recreate)
    
    print("\n" + "="*60)
    print("✅ HOÀN TẤT TẤT CẢ!")
    print("="*60)

