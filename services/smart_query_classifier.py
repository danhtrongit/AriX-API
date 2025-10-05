# -*- coding: utf-8 -*-
"""
Smart Query Classifier - Lightweight AI classification

Thay vì:
1. Rule-based với hàng trăm keywords (khó maintain)
2. Full AI parsing (chậm, tốn token)

Dùng:
- AI nhẹ chỉ để classify: financial_detail vs price vs news vs company
- Regex extract symbols
- Tiết kiệm 70% token, nhanh hơn 50%
"""

import re
import requests
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class SmartQueryClassifier:
    """
    Hybrid approach: 
    - AI để classify query type (nhanh, ít token)
    - Regex để extract symbols
    - Rule để build API calls
    """
    
    # Danh sách mã chứng khoán phổ biến
    COMMON_SYMBOLS = [
        'VCB', 'TCB', 'MBB', 'ACB', 'BID', 'CTG', 'VPB', 'STB', 'TPB', 'HDB',
        'VIC', 'VHM', 'VRE', 'NVL', 'PDR', 'DXG', 'KDH', 'BCM', 'HDG', 'NLG',
        'SSI', 'VND', 'HCM', 'VCI', 'MBS', 'FTS', 'VIX', 'AGR', 'BSI', 'SHS',
        'HPG', 'HSG', 'NKG', 'TLG', 'DTL', 'POM', 'DGC', 'VCS', 'TNG',
        'FPT', 'CMG', 'VGI', 'SAM', 'ELC', 'ITD',
        'MWG', 'PNJ', 'FRT', 'DGW',
        'GAS', 'PVD', 'PVS', 'PVT', 'PVC', 'NT2', 'POW',
        'VNM', 'MSN', 'SAB', 'VHC', 'KDC', 'ANV', 'MCH', 'SBT',
        'GMD', 'VJC', 'HVN', 'ACV', 'VOS', 'VSC',
        'DHG', 'IMP', 'DMC', 'TRA', 'DBD',
        'PLX', 'GEX', 'HAG', 'REE', 'PC1', 'BWE', 'ASM', 'VPI'
    ]
    
    def __init__(self, openai_api_key: str, openai_base: str, model: str = "gpt-4o-mini"):
        self.api_key = openai_api_key
        self.api_base = openai_base
        self.model = model
        self.logger = logging.getLogger(__name__)
    
    def extract_symbols(self, text: str) -> List[str]:
        """Extract stock symbols using regex"""
        symbols = []
        text_upper = text.upper()
        
        # Tìm tất cả symbols trong danh sách
        for symbol in self.COMMON_SYMBOLS:
            if re.search(r'\b' + symbol + r'\b', text_upper):
                symbols.append(symbol)
        
        # Loại bỏ trùng lặp
        return list(dict.fromkeys(symbols))
    
    def classify_query(self, user_query: str) -> str:
        """
        Classify query type bằng AI - nhẹ và nhanh
        
        Returns:
            'financial_detail' | 'price' | 'news' | 'company' | 'comparison' | 'market' | 'general'
        """
        try:
            # Prompt siêu ngắn gọn - chỉ classify
            prompt = f"""Classify this Vietnamese stock market question into ONE category:

Question: "{user_query}"

Categories:
- financial_detail: Hỏi về BCTC, tài sản, nợ, doanh thu, lợi nhuận, chỉ tiêu tài chính (CFA1, ISA1...), ROE/ROA/PE theo năm/quý
- price: Hỏi về giá cổ phiếu hiện tại hoặc lịch sử
- news: Hỏi về tin tức, bài viết
- company: Hỏi về thông tin công ty, lãnh đạo, cổ đông
- comparison: So sánh nhiều mã
- market: Top tăng/giảm, thống kê thị trường
- general: Câu hỏi chung không liên quan CK

Reply with ONLY the category name (one word), no explanation."""

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 10
            }
            
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()['choices'][0]['message']['content'].strip().lower()
            
            # Validate category
            valid_categories = ['financial_detail', 'price', 'news', 'company', 'comparison', 'market', 'general']
            if result in valid_categories:
                self.logger.info(f"🤖 AI Classification: {result}")
                return result
            else:
                self.logger.warning(f"AI returned invalid category: {result}, defaulting to general")
                return 'general'
                
        except Exception as e:
            self.logger.error(f"Error in AI classification: {e}")
            return 'general'
    
    def parse(self, user_query: str) -> Dict:
        """
        Parse query với hybrid approach
        
        Returns:
            {
                'symbols': ['VIC'],
                'api_calls': [...],
                'query_intent': 'financial_detail',
                'confidence': 'high'
            }
        """
        # 1. Extract symbols (regex - fast)
        symbols = self.extract_symbols(user_query)
        
        # 2. Classify query type (AI - nhẹ, ~10 tokens)
        query_type = self.classify_query(user_query)
        
        # 3. Build API calls based on classification
        api_calls = []
        
        if symbols:
            if query_type == 'financial_detail':
                # RAG cho tất cả symbols
                for symbol in symbols:
                    api_calls.append({
                        'service': 'rag_query',
                        'params': {'symbol': symbol}
                    })
            
            elif query_type == 'price':
                # Price API
                for symbol in symbols:
                    api_calls.append({
                        'service': 'get_current_price',
                        'params': {'symbol': symbol}
                    })
            
            elif query_type == 'news':
                # News API
                for symbol in symbols:
                    api_calls.append({
                        'service': 'get_stock_news',
                        'params': {'symbol': symbol}
                    })
            
            elif query_type == 'company':
                # Company info
                for symbol in symbols:
                    api_calls.append({
                        'service': 'get_company_info',
                        'params': {'symbol': symbol}
                    })
            
            elif query_type == 'comparison':
                # So sánh - lấy price + company
                for symbol in symbols:
                    api_calls.append({
                        'service': 'get_current_price',
                        'params': {'symbol': symbol}
                    })
            
            else:
                # General - lấy price làm default
                for symbol in symbols:
                    api_calls.append({
                        'service': 'get_current_price',
                        'params': {'symbol': symbol}
                    })
        
        else:
            # Không có symbols - market queries
            if query_type == 'market':
                # Default: top gainers
                api_calls.append({
                    'service': 'get_top_gainers',
                    'params': {'index': 'VNINDEX', 'limit': 10}
                })
        
        # Calculate confidence
        confidence = 'high' if symbols and api_calls else 'medium' if api_calls else 'low'
        
        result = {
            'symbols': symbols,
            'api_calls': api_calls,
            'query_intent': query_type,
            'confidence': confidence,
            'parsing_method': 'smart_hybrid'
        }
        
        self.logger.info("="*60)
        self.logger.info(f"📝 SMART QUERY PARSING")
        self.logger.info(f"📨 Input: {user_query}")
        self.logger.info(f"🏷️  Symbols: {symbols}")
        self.logger.info(f"🤖 AI Classification: {query_type}")
        self.logger.info(f"📡 Services: {[c['service'] for c in api_calls]}")
        self.logger.info(f"✅ Confidence: {confidence}")
        self.logger.info("="*60)
        
        return result

