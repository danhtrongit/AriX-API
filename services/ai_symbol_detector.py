import google.generativeai as genai
from config import Config
from typing import List, Dict, Optional
import json
import logging

class AISymbolDetector:
    def __init__(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-flash-lite-latest')
        self.logger = logging.getLogger(__name__)

        # Cache for validated symbols to avoid repeated API calls
        self.symbol_cache = {
            'valid': set(),
            'invalid': set()
        }

        # Known Vietnamese stock symbols for faster validation
        self.known_symbols = {
            # Major banks
            'VCB', 'TCB', 'ACB', 'MBB', 'STB', 'VPB', 'CTG', 'BID', 'VIB', 'SHB',

            # Large caps
            'VIC', 'VHM', 'VRE', 'HPG', 'HSG', 'FPT', 'CMG', 'VNM', 'MSN', 'MWG',
            'PLX', 'GAS', 'POW', 'NT2', 'REE', 'GEX', 'DGC', 'DPM', 'PNJ', 'SAB',

            # Tech & Industrial
            'ITD', 'ELC', 'CMT', 'TNG', 'DHG', 'IMP', 'GMD', 'VSC', 'PPC', 'DRC',

            # Real Estate & Construction
            'NVL', 'KDH', 'DXG', 'PDR', 'NLG', 'CII', 'HBC', 'IJC', 'SCR', 'CEO',

            # Others
            'SSI', 'VND', 'HCM', 'VGC', 'VJC', 'BVH', 'VCI', 'BSI', 'ORS', 'VIG'
        }

    def extract_and_validate_symbols(self, user_message: str) -> Dict:
        """
        Use AI to extract and validate stock symbols from user message
        """
        try:
            # First check cache and known symbols for quick validation
            quick_symbols = self._quick_symbol_check(user_message)
            if quick_symbols['symbols']:
                return {
                    'valid_symbols': quick_symbols['symbols'],
                    'invalid_symbols': [],
                    'confidence': 'high',
                    'source': 'cache/known',
                    'has_stock_intent': True
                }

            # Use AI for complex validation
            ai_result = self._ai_symbol_analysis(user_message)

            # Update cache
            self._update_cache(ai_result['valid_symbols'], ai_result['invalid_symbols'])

            return ai_result

        except Exception as e:
            self.logger.error(f"Error in symbol detection: {e}")
            # Fallback to regex-based detection
            return self._fallback_symbol_detection(user_message)

    def _quick_symbol_check(self, message: str) -> Dict:
        """
        Quick check using cache and known symbols
        """
        import re

        # Extract potential symbols using regex
        potential_symbols = re.findall(r'\b([A-Z]{3,4})\b', message.upper())

        valid_symbols = []
        for symbol in potential_symbols:
            if symbol in self.known_symbols or symbol in self.symbol_cache['valid']:
                valid_symbols.append(symbol)

        return {'symbols': valid_symbols}

    def _ai_symbol_analysis(self, user_message: str) -> Dict:
        """
        Use AI to analyze and extract valid Vietnamese stock symbols
        """
        prompt = f"""
        Phân tích câu hỏi sau về chứng khoán Việt Nam và trích xuất thông tin:

        NHIỆM VỤ:
        1. Xác định có phải câu hỏi về chứng khoán không
        2. Trích xuất mã chứng khoán hợp lệ (nếu có)
        3. Phân biệt mã thật vs từ không phải mã

        QUY TẮC MÃ CHỨNG KHOÁN VIỆT NAM:
        - Độ dài: 3-4 ký tự viết hoa
        - Chỉ chứa chữ cái A-Z
        - Ví dụ hợp lệ: VCB, FPT, HPG, TCBS
        - KHÔNG hợp lệ: USA, CEO, IT, AI, API, SQL

        CÂU HỎI: "{user_message}"

        RESPONSE FORMAT (JSON):
        {{
            "has_stock_intent": true/false,
            "valid_symbols": ["VCB", "FPT"],
            "invalid_symbols": ["CEO", "IT"],
            "confidence": "high/medium/low",
            "reasoning": "Giải thích ngắn gọn"
        }}

        CHỈ TRẢ VỀ JSON, KHÔNG GIẢI THÍCH THÊM.
        """

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

            # Try to extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                result = json.loads(json_text)
            else:
                # Fallback to full response
                result = json.loads(response_text)

            # Validate response format
            if not all(key in result for key in ['has_stock_intent', 'valid_symbols', 'invalid_symbols']):
                raise ValueError("Invalid response format")

            # Ensure symbols are uppercase and valid format
            result['valid_symbols'] = [s.upper() for s in result.get('valid_symbols', [])
                                     if self._is_valid_symbol_format(s)]
            result['invalid_symbols'] = [s.upper() for s in result.get('invalid_symbols', [])]

            return result

        except (json.JSONDecodeError, ValueError, Exception) as e:
            self.logger.warning(f"AI symbol analysis failed: {e}")
            return self._fallback_symbol_detection(user_message)

    def _is_valid_symbol_format(self, symbol: str) -> bool:
        """
        Check if symbol matches Vietnamese stock symbol format
        """
        import re
        if not symbol or not isinstance(symbol, str):
            return False

        symbol = symbol.upper().strip()

        # Basic format check
        if not re.match(r'^[A-Z]{3,4}$', symbol):
            return False

        # Exclude common English words that match pattern
        excluded_words = {
            'CEO', 'CFO', 'CTO', 'USA', 'API', 'SQL', 'XML', 'HTML', 'CSS', 'PHP',
            'NET', 'COM', 'ORG', 'GOV', 'EDU', 'INFO', 'JOBS', 'NEWS', 'HELP',
            'TIPS', 'CHAT', 'CODE', 'DATA', 'FILE', 'TEXT', 'JSON', 'HTTP', 'HTTPS',
            'AJAX', 'REST', 'SOAP', 'CRUD', 'AUTH', 'BLOG', 'DOCS', 'DEMO', 'TEST',
            'PROD', 'LIVE', 'BETA', 'WIKI', 'MAIL', 'SMTP', 'HOST', 'PORT', 'PATH',
            'USER', 'PASS', 'HASH', 'SALT', 'UUID', 'GUID', 'TEMP', 'LOGS', 'DIST'
        }

        if symbol in excluded_words:
            return False

        return True

    def _fallback_symbol_detection(self, message: str) -> Dict:
        """
        Fallback symbol detection using regex and known symbols
        """
        import re

        # Extract potential symbols
        potential_symbols = re.findall(r'\b([A-Z]{3,4})\b', message.upper())

        valid_symbols = []
        invalid_symbols = []

        for symbol in potential_symbols:
            if (symbol in self.known_symbols or
                symbol in self.symbol_cache['valid'] or
                (self._is_valid_symbol_format(symbol) and symbol not in self.symbol_cache['invalid'])):
                valid_symbols.append(symbol)
            else:
                invalid_symbols.append(symbol)

        # Check if message has stock intent
        stock_keywords = [
            'giá', 'price', 'cổ phiếu', 'stock', 'chứng khoán', 'phân tích', 'analysis',
            'mua', 'bán', 'buy', 'sell', 'đầu tư', 'invest', 'báo cáo', 'report',
            'tài chính', 'financial', 'doanh thu', 'revenue', 'lợi nhuận', 'profit'
        ]

        has_stock_intent = (
            any(keyword in message.lower() for keyword in stock_keywords) or
            bool(valid_symbols)
        )

        return {
            'has_stock_intent': has_stock_intent,
            'valid_symbols': list(set(valid_symbols)),
            'invalid_symbols': list(set(invalid_symbols)),
            'confidence': 'medium',
            'source': 'fallback'
        }

    def _update_cache(self, valid_symbols: List[str], invalid_symbols: List[str]):
        """
        Update symbol cache with new results
        """
        for symbol in valid_symbols:
            if symbol and len(symbol) >= 3:
                self.symbol_cache['valid'].add(symbol.upper())

        for symbol in invalid_symbols:
            if symbol and len(symbol) >= 3:
                self.symbol_cache['invalid'].add(symbol.upper())

    def is_stock_related_query(self, user_message: str) -> bool:
        """
        Quick check if message is stock-related without full analysis
        """
        stock_indicators = [
            'giá', 'price', 'cổ phiếu', 'stock', 'chứng khoán',
            'phân tích', 'analysis', 'chart', 'báo cáo', 'report',
            'tài chính', 'financial', 'P/E', 'ROE', 'ROA'
        ]

        message_lower = user_message.lower()

        # Check for stock keywords
        has_keywords = any(keyword in message_lower for keyword in stock_indicators)

        # Check for potential symbols
        import re
        has_symbols = bool(re.search(r'\b[A-Z]{3,4}\b', user_message))

        # Check against known symbols
        has_known_symbols = any(symbol in user_message.upper() for symbol in self.known_symbols)

        return has_keywords or has_symbols or has_known_symbols

    def get_symbol_suggestions(self, partial_symbol: str, limit: int = 5) -> List[str]:
        """
        Get symbol suggestions based on partial input
        """
        if not partial_symbol or len(partial_symbol) < 2:
            return []

        partial_upper = partial_symbol.upper()
        suggestions = []

        # Search in known symbols
        for symbol in sorted(self.known_symbols):
            if symbol.startswith(partial_upper):
                suggestions.append(symbol)
                if len(suggestions) >= limit:
                    break

        return suggestions

    def validate_symbol_exists(self, symbol: str) -> Dict:
        """
        Validate if a symbol actually exists in the market
        This can be enhanced with real market data API
        """
        if not symbol:
            return {'valid': False, 'reason': 'Empty symbol'}

        symbol = symbol.upper()

        # Check cache first
        if symbol in self.symbol_cache['valid']:
            return {'valid': True, 'reason': 'Cached as valid'}

        if symbol in self.symbol_cache['invalid']:
            return {'valid': False, 'reason': 'Cached as invalid'}

        # Check against known symbols
        if symbol in self.known_symbols:
            self.symbol_cache['valid'].add(symbol)
            return {'valid': True, 'reason': 'Known symbol'}

        # Check format
        if not self._is_valid_symbol_format(symbol):
            self.symbol_cache['invalid'].add(symbol)
            return {'valid': False, 'reason': 'Invalid format'}

        # Default to potentially valid for unknown symbols
        return {'valid': True, 'reason': 'Format valid, unknown symbol', 'confidence': 'low'}

    def clear_cache(self):
        """
        Clear the symbol cache
        """
        self.symbol_cache = {'valid': set(), 'invalid': set()}
        self.logger.info("Symbol cache cleared")