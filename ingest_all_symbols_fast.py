#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script để ingest TẤT CẢ symbols NHANH với batch embeddings + parallel processing

OPTIMIZATIONS:
- Batch embeddings (50-100x faster than single embeddings)
- Parallel symbol processing (với rate limiting)
- Skip symbols without data
- Progress tracking

Usage:
    python ingest_all_symbols_fast.py
    python ingest_all_symbols_fast.py --limit 10  # Test với 10 symbols
    python ingest_all_symbols_fast.py --workers 3  # Process 3 symbols in parallel
    python ingest_all_symbols_fast.py --batch-size 100  # Larger batch size
"""

import sys
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from vnstock_data import Listing
from ingest_financial_data import ingest_to_qdrant
from config import Config

def main():
    parser = argparse.ArgumentParser(description='Fast ingest all stock symbols to Qdrant')
    parser.add_argument('--limit', type=int, default=None, 
                       help='Limit number of symbols to process (for testing)')
    parser.add_argument('--start-from', type=int, default=0,
                       help='Start from index (useful for resuming)')
    parser.add_argument('--workers', type=int, default=1,
                       help='Number of parallel symbol workers (default: 1, max: 5 recommended)')
    parser.add_argument('--skip-errors', action='store_true',
                       help='Continue processing even if a symbol fails')
    parser.add_argument('--force', action='store_true',
                       help='Skip confirmation prompt for high worker counts')
    
    args = parser.parse_args()
    
    # Validate workers
    if args.workers > 5 and not args.force:
        print(f"⚠️  Warning: {args.workers} workers may cause rate limiting. Recommended max: 5")
        response = input("Continue? (y/n): ")
        if response.lower() != 'y':
            sys.exit(0)
    
    print("=" * 60)
    print("🚀 FAST INGESTING ALL STOCK SYMBOLS")
    print("=" * 60)
    
    # Lấy tất cả symbols
    print("\n📋 Đang lấy danh sách tất cả mã chứng khoán từ VNStock...")
    try:
        listing = Listing(source='VCI')
        df = listing.all_symbols()
    except Exception as e:
        print(f"❌ Lỗi khi lấy danh sách symbols: {e}")
        sys.exit(1)
    
    # Lọc lấy cột ticker
    if 'ticker' in df.columns:
        all_tickers = df['ticker'].tolist()
    elif 'symbol' in df.columns:
        all_tickers = df['symbol'].tolist()
    else:
        print(f"❌ Không tìm thấy cột ticker/symbol. Các cột có sẵn: {df.columns.tolist()}")
        sys.exit(1)
    
    # Lọc bỏ giá trị NaN/None
    all_tickers = [str(t).upper() for t in all_tickers if t and str(t).strip()]
    
    print(f"✅ Tìm thấy {len(all_tickers)} mã chứng khoán")
    
    # Apply filters
    start_idx = args.start_from
    end_idx = min(start_idx + args.limit, len(all_tickers)) if args.limit else len(all_tickers)
    tickers = all_tickers[start_idx:end_idx]
    
    print(f"\n🎯 Sẽ xử lý {len(tickers)} mã (từ index {start_idx} đến {end_idx-1})")
    print(f"🔧 Qdrant: {Config.QDRANT_HOST}")
    print(f"📦 Collection: {Config.QDRANT_COLLECTION}")
    print(f"⚡ Workers: {args.workers} symbols in parallel")
    print(f"🛡️  Skip errors: {args.skip_errors}")
    print(f"💡 Batch embeddings: ENABLED (50-100x faster!)")
    
    # Statistics
    success_count = 0
    error_count = 0
    error_symbols = []
    lock = Lock()
    
    start_time = time.time()
    
    # Process function for each ticker
    def process_ticker(i, ticker):
        nonlocal success_count, error_count
        ticker = str(ticker).upper()
        
        print(f"\n{'='*60}")
        print(f"[{i+1}/{end_idx}] Processing {ticker}")
        print(f"{'='*60}")
        
        try:
            # First ticker: recreate collection, rest: add to collection
            recreate = (i == start_idx)
            ingest_to_qdrant(ticker, recreate_collection=recreate)
            
            with lock:
                success_count += 1
            
            print(f"✅ Thành công: {ticker}")
            return (ticker, True, None)
            
        except Exception as e:
            with lock:
                error_count += 1
            
            error_msg = str(e)
            print(f"❌ Lỗi khi xử lý {ticker}: {error_msg}")
            return (ticker, False, error_msg)
    
    # Process with ThreadPoolExecutor
    if args.workers > 1:
        print(f"\n🚀 Chạy parallel với {args.workers} workers...")
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(process_ticker, start_idx + idx, ticker): ticker 
                for idx, ticker in enumerate(tickers)
            }
            
            for future in as_completed(futures):
                ticker, success, error = future.result()
                
                if not success:
                    error_symbols.append(ticker)
                    if not args.skip_errors:
                        print(f"\n⚠️  Dừng xử lý do gặp lỗi. Để tiếp tục bỏ qua lỗi, dùng --skip-errors")
                        # Cancel remaining futures
                        for f in futures:
                            f.cancel()
                        break
    else:
        # Sequential processing
        print(f"\n🔄 Chạy tuần tự (1 symbol mỗi lần)...")
        for idx, ticker in enumerate(tickers):
            ticker_result = process_ticker(start_idx + idx, ticker)
            ticker, success, error = ticker_result
            
            if not success:
                error_symbols.append(ticker)
                if not args.skip_errors:
                    print(f"\n⚠️  Dừng xử lý do gặp lỗi. Để tiếp tục bỏ qua lỗi, dùng --skip-errors")
                    break
    
    # Summary
    elapsed_time = time.time() - start_time
    print("\n" + "="*60)
    print("📊 THỐNG KÊ")
    print("="*60)
    print(f"✅ Thành công: {success_count}/{len(tickers)} symbols")
    print(f"❌ Thất bại: {error_count}/{len(tickers)} symbols")
    print(f"⏱️  Thời gian: {elapsed_time:.2f}s ({elapsed_time/60:.2f} phút)")
    
    if success_count > 0:
        avg_time = elapsed_time / success_count
        print(f"⚡ Trung bình: {avg_time:.2f}s/symbol")
        
        # Estimate remaining time
        remaining = len(all_tickers) - end_idx
        if remaining > 0:
            est_time = remaining * avg_time
            print(f"📈 Ước tính thời gian còn lại cho {remaining} symbols: {est_time/3600:.2f} giờ")
    
    if error_symbols:
        print(f"\n❌ Các symbol bị lỗi:")
        for sym in error_symbols[:20]:  # Show first 20
            print(f"   - {sym}")
        if len(error_symbols) > 20:
            print(f"   ... và {len(error_symbols) - 20} symbols khác")
        
        print(f"\n💡 Để xử lý lại các symbol bị lỗi:")
        print(f"   python ingest_financial_data.py {' '.join(error_symbols[:10])}")
    
    print("\n" + "="*60)
    if error_count == 0:
        print("✅ HOÀN TẤT TẤT CẢ!")
    else:
        print("⚠️  HOÀN TẤT VỚI MỘT SỐ LỖI")
    print("="*60)
    
    # Performance summary
    print("\n💡 TIPS TO IMPROVE:")
    if args.workers == 1:
        print("  - Tăng workers: --workers 3 (xử lý 3 symbols song song)")
    if success_count > 0 and avg_time > 10:
        print("  - Thời gian trung bình còn cao, kiểm tra network/API")

if __name__ == "__main__":
    main()

