from models.gemini_client import GeminiClient
from typing import Dict, List, Optional
import logging
import json

class QueryAnalyzer:
    """
    AI-powered query analyzer that determines symbols and appropriate API calls
    """
    def __init__(self):
        self.gemini_client = GeminiClient()
        self.logger = logging.getLogger(__name__)

    def analyze_query(self, user_query: str) -> Dict:
        """
        Phân tích câu hỏi bằng AI để:
        1. Xác định mã cổ phiếu (symbols)
        2. Chọn các API service cần gọi
        3. Xác định tham số cho mỗi API

        Returns:
            {
                'symbols': ['VCB', 'TCB'],
                'api_calls': [
                    {
                        'service': 'get_current_price',
                        'params': {'symbol': 'VCB'}
                    },
                    {
                        'service': 'get_company_info',
                        'params': {'symbol': 'VCB'}
                    }
                ],
                'query_intent': 'compare_stocks',
                'needs_analysis': True
            }
        """
        try:
            analysis_prompt = self._build_analysis_prompt(user_query)

            # Gọi AI để phân tích
            response = self.gemini_client.model.generate_content(analysis_prompt)
            analysis_result = self._parse_ai_response(response.text)

            self.logger.info(f"Query analysis: {analysis_result}")
            return analysis_result

        except Exception as e:
            self.logger.error(f"Error analyzing query: {e}")
            return self._get_fallback_analysis(user_query)

    def _build_analysis_prompt(self, user_query: str) -> str:
        """
        Tạo prompt cho AI để phân tích câu hỏi
        """
        return f"""Phân tích câu hỏi về chứng khoán sau và trả về JSON:

Câu hỏi: "{user_query}"

Các API service có sẵn:
1. get_current_price(symbol) - Giá hiện tại
2. get_stock_price_history(symbol, start_date, end_date) - Lịch sử giá
3. get_company_info(symbol) - Thông tin công ty
4. get_financial_reports(symbol, period='year'|'quarter') - Báo cáo tài chính
5. get_stock_news(symbol) - Tin tức
6. get_all_symbols() - Danh sách mã
7. get_price_board(symbols) - Bảng giá nhiều mã
8. get_order_stats(symbol) - Thống kê lệnh
9. get_foreign_trade(symbol) - Giao dịch ngoại
10. get_prop_trade(symbol) - Giao dịch tự doanh
11. get_insider_deal(symbol) - Giao dịch nội bộ
12. get_top_gainers(index, limit) - Top tăng giá
13. get_top_losers(index, limit) - Top giảm giá
14. get_top_by_value(index, limit) - Top giá trị GD
15. get_top_by_volume(index, limit) - Top khối lượng GD
16. get_top_foreign_buy(date) - Top ngoại mua
17. get_top_foreign_sell(date) - Top ngoại bán
18. get_market_pe(index, duration) - P/E thị trường
19. get_market_pb(index, duration) - P/B thị trường
20. get_market_evaluation(index, duration) - Định giá TT
21. get_fund_listing(fund_type) - Danh sách quỹ
22. get_fund_nav(symbol) - NAV quỹ
23. get_fund_top_holding(symbol) - Danh mục quỹ
24. get_gold_vn(start, end) - Giá vàng VN
25. get_gold_global(start, end) - Giá vàng TG
26. get_oil_crude(start, end) - Giá dầu
27. get_commodity_price(type, start, end) - Giá hàng hóa
28. get_gdp(start, end, period) - GDP
29. get_cpi(start, end, period) - CPI
30. get_industry_production(start, end, period) - Sản xuất CN
31. get_retail(start, end, period) - Bán lẻ
32. get_import_export(start, end, period) - XNK

Trả về JSON với format sau (chỉ trả JSON, không thêm text khác):
{{
    "symbols": ["VCB", "TCB"],
    "api_calls": [
        {{
            "service": "get_current_price",
            "params": {{"symbol": "VCB"}}
        }}
    ],
    "query_intent": "get_price|compare_stocks|get_news|market_analysis|...",
    "needs_analysis": true|false,
    "date_range": {{"start": "2024-01-01", "end": "2024-12-31"}},
    "confidence": "high|medium|low"
}}

Lưu ý:
- Chỉ trích xuất mã CK thật (VCB, FPT, HPG...)
- Chọn đúng API service theo nhu cầu
- Nếu hỏi về top/thống kê thị trường, dùng get_top_* hoặc get_market_*
- Nếu hỏi về hàng hóa, dùng commodity APIs
- Nếu hỏi về kinh tế vĩ mô, dùng macro APIs
- Nếu hỏi về quỹ mở, dùng fund APIs
- needs_analysis=true nếu cần AI phân tích kết quả
- Với câu hỏi không liên quan chứng khoán, trả về {{"symbols": [], "api_calls": [], "query_intent": "general", "needs_analysis": false}}
"""

    def _parse_ai_response(self, response_text: str) -> Dict:
        """
        Parse JSON response từ AI
        """
        try:
            # Remove markdown code blocks if present
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            result = json.loads(response_text.strip())

            # Validate structure
            if 'symbols' not in result:
                result['symbols'] = []
            if 'api_calls' not in result:
                result['api_calls'] = []
            if 'query_intent' not in result:
                result['query_intent'] = 'general'
            if 'needs_analysis' not in result:
                result['needs_analysis'] = False

            return result

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse AI response: {e}\nResponse: {response_text}")
            return self._get_empty_analysis()

    def _get_fallback_analysis(self, user_query: str) -> Dict:
        """
        Fallback analysis khi AI fail
        """
        # Simple pattern matching fallback
        query_lower = user_query.lower()

        result = {
            'symbols': [],
            'api_calls': [],
            'query_intent': 'general',
            'needs_analysis': False,
            'confidence': 'low'
        }

        # Extract common stock symbols
        import re
        potential_symbols = re.findall(r'\b([A-Z]{3})\b', user_query.upper())
        if potential_symbols:
            result['symbols'] = potential_symbols[:3]  # Limit to 3

        # Determine basic intent
        if any(word in query_lower for word in ['giá', 'price']):
            result['query_intent'] = 'get_price'
            for symbol in result['symbols']:
                result['api_calls'].append({
                    'service': 'get_current_price',
                    'params': {'symbol': symbol}
                })
        elif any(word in query_lower for word in ['tin tức', 'news']):
            result['query_intent'] = 'get_news'
            for symbol in result['symbols']:
                result['api_calls'].append({
                    'service': 'get_stock_news',
                    'params': {'symbol': symbol, 'limit': 10}
                })
        elif any(word in query_lower for word in ['công ty', 'company']):
            result['query_intent'] = 'get_company_info'
            for symbol in result['symbols']:
                result['api_calls'].append({
                    'service': 'get_company_info',
                    'params': {'symbol': symbol}
                })

        return result

    def _get_empty_analysis(self) -> Dict:
        """
        Return empty analysis structure
        """
        return {
            'symbols': [],
            'api_calls': [],
            'query_intent': 'general',
            'needs_analysis': False,
            'confidence': 'low'
        }