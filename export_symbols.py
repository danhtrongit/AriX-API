#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script để export danh sách symbols từ VNStock ra JSON

Usage:
    python export_symbols.py

Output:
    symbols.json - File chứa tất cả mã CK, được sử dụng bởi:
    - services/smart_query_classifier.py (để extract symbols từ query)
    
Note:
    - Chạy lại script này định kỳ để cập nhật danh sách mã mới
    - File được tự động load bởi SmartQueryClassifier
"""

import json
from vnstock_data import Listing


def export_symbols_to_json(output_file='symbols.json'):
    """Export danh sách symbols ra file JSON"""
    try:
        print("🔍 Đang lấy danh sách symbols từ VNStock...")
        listing = Listing(source='VCI')
        df = listing.all_symbols()
        
        # Lấy cột ticker hoặc symbol
        if 'ticker' in df.columns:
            symbols = df['ticker'].tolist()
        elif 'symbol' in df.columns:
            symbols = df['symbol'].tolist()
        else:
            print(f"⚠️  Không tìm thấy cột ticker/symbol. Columns: {df.columns.tolist()}")
            return False
        
        # Sort và loại bỏ trùng lặp
        symbols = sorted(list(set(symbols)))
        
        # Export ra JSON
        data = {
            'total': len(symbols),
            'symbols': symbols,
            'source': 'VCI',
            'description': 'Danh sách tất cả mã chứng khoán từ VNStock'
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Đã export {len(symbols)} symbols ra file: {output_file}")
        print(f"\n📊 Một số mã đầu tiên: {', '.join(symbols[:20])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Lỗi khi export symbols: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("📤 EXPORT SYMBOLS TO JSON")
    print("=" * 60 + "\n")
    
    success = export_symbols_to_json()
    
    if success:
        print("\n" + "=" * 60)
        print("💡 Sử dụng trong code:")
        print("-" * 60)
        print("import json")
        print("with open('symbols.json', 'r') as f:")
        print("    data = json.load(f)")
        print("    symbols = data['symbols']")
        print("=" * 60)

