from vnstock_data import Finance
import json

fin = Finance(symbol='VCI', period='year', source='VCI')

# Bảng cân đối kế toán
balance_sheet_data = fin.balance_sheet(lang='vi')

# Convert to JSON and save
with open('balance_sheet.json', 'w', encoding='utf-8') as f:
    json.dump(balance_sheet_data.to_dict(orient='records'), f, ensure_ascii=False, indent=2)

print("Đã export dữ liệu ra file balance_sheet.json")