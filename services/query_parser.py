import re
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
from services.ai_symbol_detector import AISymbolDetector

class QueryParser:
    def __init__(self):
        # Initialize AI Symbol Detector
        self.ai_detector = AISymbolDetector()

        # Define patterns for different types of queries (keep existing ones)
        self.patterns = {
            'date_range': re.compile(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}).*?(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})'),
            'single_date': re.compile(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})'),
            'time_period': re.compile(r'(hôm nay|tuần này|tháng này|năm nay|hôm qua|tuần trước|tháng trước|năm trước)'),
            'relative_time': re.compile(r'(\d+)\s*(ngày|tuần|tháng|năm)\s*(trước|gần đây|vừa qua)')
        }

        # Define query types and keywords
        self.query_types = {
            'company_info': [
                'thông tin công ty', 'công ty', 'doanh nghiệp', 'tổng quan',
                'cổ đông', 'ban lãnh đạo', 'công ty con', 'sự kiện'
            ],
            'stock_price': [
                'giá', 'giá cổ phiếu', 'price', 'lịch sử giá', 'biến động giá',
                'giá hôm nay', 'giá hiện tại', 'closing price'
            ],
            'financial_reports': [
                'báo cáo tài chính', 'kết quả kinh doanh', 'bảng cân đối kế toán',
                'lưu chuyển tiền tệ', 'tài chính', 'doanh thu', 'lợi nhuận',
                'tài sản', 'nợ phải trả'
            ],
            'news': [
                'tin tức', 'news', 'tin mới', 'thông tin mới', 'bài viết',
                'tin tức mới nhất', 'tin gần đây', 'update', 'cập nhật',
                'tin gì', 'có tin', 'tin về', 'thông tin về', 'tin tức về'
            ],
            'analysis': [
                'phân tích', 'đánh giá', 'analysis', 'nhận xét', 'xu hướng',
                'khuyến nghị', 'triển vọng'
            ],
            'comparison': [
                'so sánh', 'compare', 'so với', 'đối thủ cạnh tranh'
            ]
        }

    def parse_query(self, query: str) -> Dict:
        """
        Enhanced query parsing with AI symbol detection
        """
        query_lower = query.lower()

        # First, use AI to detect and validate symbols
        symbol_analysis = self.ai_detector.extract_and_validate_symbols(query)

        # Parse other components
        result = {
            'original_query': query,
            'query_type': self._identify_query_type(query_lower),
            'stock_symbols': symbol_analysis['valid_symbols'],
            'invalid_symbols': symbol_analysis.get('invalid_symbols', []),
            'symbol_confidence': symbol_analysis.get('confidence', 'medium'),
            'has_stock_intent': symbol_analysis.get('has_stock_intent', False),
            'date_info': self._extract_date_info(query_lower),
            'entities': self._extract_entities(query_lower),
            'intent': self._determine_intent(query_lower, symbol_analysis),
            'ai_analysis': symbol_analysis
        }

        return result

    def _determine_intent(self, query: str, symbol_analysis: Dict) -> str:
        """
        Enhanced intent determination using AI classification
        """
        # If AI detected valid symbols, use AI to classify intent
        if symbol_analysis['valid_symbols']:
            # Use AI to classify intent based on query context
            ai_intent = self.ai_detector.classify_query_intent(query, symbol_analysis['valid_symbols'])
            if ai_intent:
                return ai_intent

            # Fallback to pattern matching if AI fails
            symbol_intent_patterns = [
                ('get_stock_news', ['tin tức', 'news', 'tin mới', 'thông tin mới', 'cập nhật', 'tin tức mới nhất', 'tin gì', 'có tin', 'tin về', 'thông tin về', 'tin tức về']),
                ('get_financial_report', ['báo cáo tài chính', 'kết quả kinh doanh', 'tài chính']),
                ('get_stock_analysis', ['phân tích', 'đánh giá', 'analysis', 'nhận xét']),
                ('get_price_history', ['lịch sử giá', 'biến động giá', 'price history']),
                ('get_current_price', ['giá hiện tại', 'giá hôm nay', 'current price', 'giá']),
                ('get_company_info', ['thông tin công ty', 'công ty', 'company info']),
                ('compare_stocks', ['so sánh', 'compare'])
            ]

            for intent, keywords in symbol_intent_patterns:
                if any(keyword in query for keyword in keywords):
                    return intent

            # Default intent for queries with valid symbols
            return 'get_current_price'

        # If no valid symbols but has stock intent
        elif symbol_analysis.get('has_stock_intent'):
            return 'general_stock_inquiry'

        # Original intent determination for non-stock queries
        intent_patterns = [
            ('general_inquiry', ['là gì', 'what is', 'giải thích', 'explain']),
            ('help_request', ['giúp', 'help', 'hướng dẫn', 'guide']),
            ('greeting', ['xin chào', 'hello', 'chào', 'hi'])
        ]

        for intent, keywords in intent_patterns:
            if any(keyword in query for keyword in keywords):
                return intent

        return 'general_inquiry'

    def validate_symbols_before_query(self, symbols: List[str]) -> Dict:
        """
        Validate symbols before making API calls
        """
        if not symbols:
            return {
                'should_proceed': False,
                'valid_symbols': [],
                'reason': 'No symbols to validate'
            }

        valid_symbols = []
        validation_results = {}

        for symbol in symbols:
            validation = self.ai_detector.validate_symbol_exists(symbol)
            validation_results[symbol] = validation

            if validation['valid']:
                valid_symbols.append(symbol)

        return {
            'should_proceed': bool(valid_symbols),
            'valid_symbols': valid_symbols,
            'validation_details': validation_results,
            'reason': f"Validated {len(valid_symbols)}/{len(symbols)} symbols"
        }

    def suggest_corrections(self, query: str) -> Dict:
        """
        Suggest corrections for queries with invalid symbols
        """
        symbol_analysis = self.ai_detector.extract_and_validate_symbols(query)

        suggestions = {
            'corrected_query': query,
            'symbol_suggestions': {},
            'has_suggestions': False
        }

        # Get suggestions for invalid symbols
        for invalid_symbol in symbol_analysis.get('invalid_symbols', []):
            if len(invalid_symbol) >= 2:
                symbol_suggestions = self.ai_detector.get_symbol_suggestions(invalid_symbol[:2])
                if symbol_suggestions:
                    suggestions['symbol_suggestions'][invalid_symbol] = symbol_suggestions
                    suggestions['has_suggestions'] = True

        return suggestions

    def is_stock_query_worth_processing(self, query: str) -> Dict:
        """
        Determine if a query is worth processing for stock data
        """
        # Quick check first
        if not self.ai_detector.is_stock_related_query(query):
            return {
                'worth_processing': False,
                'reason': 'Not stock-related query',
                'confidence': 'high'
            }

        # Full AI analysis
        symbol_analysis = self.ai_detector.extract_and_validate_symbols(query)

        # Decide based on analysis
        if symbol_analysis['valid_symbols']:
            return {
                'worth_processing': True,
                'reason': f"Found valid symbols: {', '.join(symbol_analysis['valid_symbols'])}",
                'confidence': symbol_analysis.get('confidence', 'medium'),
                'symbols': symbol_analysis['valid_symbols']
            }

        elif symbol_analysis.get('has_stock_intent'):
            return {
                'worth_processing': True,
                'reason': 'Has stock intent but no specific symbols',
                'confidence': 'low',
                'symbols': []
            }

        else:
            return {
                'worth_processing': False,
                'reason': 'No valid symbols or stock intent detected',
                'confidence': symbol_analysis.get('confidence', 'medium')
            }

    def _identify_query_type(self, query: str) -> List[str]:
        """
        Identify the type of query based on keywords
        """
        identified_types = []

        for query_type, keywords in self.query_types.items():
            for keyword in keywords:
                if keyword in query:
                    if query_type not in identified_types:
                        identified_types.append(query_type)
                    break

        # Default to company_info if no specific type identified
        if not identified_types:
            identified_types = ['company_info']

        return identified_types

    def _extract_stock_symbols(self, query: str) -> List[str]:
        """
        Extract stock symbols from the query
        """
        matches = self.patterns['stock_symbol'].findall(query.upper())
        return list(set(matches))  # Remove duplicates

    def _extract_date_info(self, query: str) -> Dict:
        """
        Extract date information from the query
        """
        date_info = {
            'start_date': None,
            'end_date': None,
            'period_type': None,
            'relative_period': None
        }

        # Check for date range
        date_range_match = self.patterns['date_range'].search(query)
        if date_range_match:
            start_date_str, end_date_str = date_range_match.groups()
            date_info['start_date'] = self._parse_date_string(start_date_str)
            date_info['end_date'] = self._parse_date_string(end_date_str)
            date_info['period_type'] = 'custom_range'
            return date_info

        # Check for single date
        single_date_match = self.patterns['single_date'].search(query)
        if single_date_match:
            date_str = single_date_match.group(1)
            parsed_date = self._parse_date_string(date_str)
            date_info['start_date'] = parsed_date
            date_info['end_date'] = parsed_date
            date_info['period_type'] = 'single_date'
            return date_info

        # Check for time periods (hôm nay, tuần này, etc.)
        time_period_match = self.patterns['time_period'].search(query)
        if time_period_match:
            period = time_period_match.group(1)
            date_info.update(self._get_period_dates(period))
            date_info['period_type'] = 'named_period'
            date_info['relative_period'] = period
            return date_info

        # Check for relative time (3 tháng trước, etc.)
        relative_match = self.patterns['relative_time'].search(query)
        if relative_match:
            number, unit, direction = relative_match.groups()
            date_info.update(self._get_relative_dates(int(number), unit, direction))
            date_info['period_type'] = 'relative_period'
            date_info['relative_period'] = f"{number} {unit} {direction}"
            return date_info

        # Only add default date range for explicit historical queries
        if any(keyword in query for keyword in ['lịch sử', 'historical', 'trong', 'từ', 'đến', 'period']):
            date_info.update(self._get_period_dates('tháng này'))
            date_info['period_type'] = 'default_recent'

        return date_info

    def _parse_date_string(self, date_str: str) -> Optional[str]:
        """
        Parse date string and convert to YYYY-MM-DD format
        """
        try:
            # Try different date formats
            formats = ['%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y']

            for fmt in formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue

            return None
        except Exception:
            return None

    def _get_period_dates(self, period: str) -> Dict:
        """
        Get start and end dates for named periods
        """
        today = datetime.now()
        result = {}

        if period == 'hôm nay':
            result['start_date'] = today.strftime('%Y-%m-%d')
            result['end_date'] = today.strftime('%Y-%m-%d')
        elif period == 'hôm qua':
            yesterday = today - timedelta(days=1)
            result['start_date'] = yesterday.strftime('%Y-%m-%d')
            result['end_date'] = yesterday.strftime('%Y-%m-%d')
        elif period == 'tuần này':
            start_of_week = today - timedelta(days=today.weekday())
            result['start_date'] = start_of_week.strftime('%Y-%m-%d')
            result['end_date'] = today.strftime('%Y-%m-%d')
        elif period == 'tuần trước':
            start_of_last_week = today - timedelta(days=today.weekday() + 7)
            end_of_last_week = start_of_last_week + timedelta(days=6)
            result['start_date'] = start_of_last_week.strftime('%Y-%m-%d')
            result['end_date'] = end_of_last_week.strftime('%Y-%m-%d')
        elif period == 'tháng này':
            start_of_month = today.replace(day=1)
            result['start_date'] = start_of_month.strftime('%Y-%m-%d')
            result['end_date'] = today.strftime('%Y-%m-%d')
        elif period == 'tháng trước':
            if today.month == 1:
                start_of_last_month = today.replace(year=today.year-1, month=12, day=1)
            else:
                start_of_last_month = today.replace(month=today.month-1, day=1)

            # Last day of previous month
            end_of_last_month = today.replace(day=1) - timedelta(days=1)
            result['start_date'] = start_of_last_month.strftime('%Y-%m-%d')
            result['end_date'] = end_of_last_month.strftime('%Y-%m-%d')
        elif period == 'năm này':
            start_of_year = today.replace(month=1, day=1)
            result['start_date'] = start_of_year.strftime('%Y-%m-%d')
            result['end_date'] = today.strftime('%Y-%m-%d')
        elif period == 'năm trước':
            start_of_last_year = today.replace(year=today.year-1, month=1, day=1)
            end_of_last_year = today.replace(year=today.year-1, month=12, day=31)
            result['start_date'] = start_of_last_year.strftime('%Y-%m-%d')
            result['end_date'] = end_of_last_year.strftime('%Y-%m-%d')

        return result

    def _get_relative_dates(self, number: int, unit: str, direction: str) -> Dict:
        """
        Get dates for relative periods (3 tháng trước, etc.)
        """
        today = datetime.now()
        result = {}

        if direction in ['trước', 'vừa qua', 'gần đây']:
            if unit == 'ngày':
                start_date = today - timedelta(days=number)
                result['start_date'] = start_date.strftime('%Y-%m-%d')
                result['end_date'] = today.strftime('%Y-%m-%d')
            elif unit == 'tuần':
                start_date = today - timedelta(weeks=number)
                result['start_date'] = start_date.strftime('%Y-%m-%d')
                result['end_date'] = today.strftime('%Y-%m-%d')
            elif unit == 'tháng':
                # Approximate months as 30 days
                start_date = today - timedelta(days=number * 30)
                result['start_date'] = start_date.strftime('%Y-%m-%d')
                result['end_date'] = today.strftime('%Y-%m-%d')
            elif unit == 'năm':
                start_date = today.replace(year=today.year - number)
                result['start_date'] = start_date.strftime('%Y-%m-%d')
                result['end_date'] = today.strftime('%Y-%m-%d')

        return result

    def _extract_entities(self, query: str) -> Dict:
        """
        Extract named entities from the query
        """
        entities = {
            'financial_metrics': [],
            'time_expressions': [],
            'actions': []
        }

        # Financial metrics
        financial_keywords = [
            'doanh thu', 'lợi nhuận', 'tài sản', 'nợ', 'vốn chủ sở hữu',
            'revenue', 'profit', 'asset', 'debt', 'equity', 'pe', 'pb',
            'roa', 'roe', 'eps'
        ]

        for keyword in financial_keywords:
            if keyword in query:
                entities['financial_metrics'].append(keyword)

        # Actions
        action_keywords = [
            'mua', 'bán', 'nắm giữ', 'buy', 'sell', 'hold',
            'đầu tư', 'invest', 'phân tích', 'analyze'
        ]

        for keyword in action_keywords:
            if keyword in query:
                entities['actions'].append(keyword)

        return entities