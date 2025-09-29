from models.gemini_client import GeminiClient
from models.vnstock_client import VNStockClient
from models.iqx_news_client import IQXNewsClient
from services.query_parser import QueryParser
from typing import Dict, Optional
import logging

class ChatService:
    def __init__(self):
        self.gemini_client = GeminiClient()
        self.vnstock_client = VNStockClient()
        self.iqx_news_client = IQXNewsClient()
        self.query_parser = QueryParser()
        self.logger = logging.getLogger(__name__)

    def process_message(self, user_message: str, session_id: str = 'default') -> Dict:
        """
        Process user message and generate appropriate response with AI symbol validation
        """
        try:
            # Parse the user query to understand intent and entities
            parsed_query = self.query_parser.parse_query(user_message)
            self.logger.info(f"Parsed query: {parsed_query}")

            # Check if query has invalid symbols and provide suggestions
            invalid_symbols = parsed_query.get('invalid_symbols', [])
            if invalid_symbols:
                suggestions = self.query_parser.suggest_corrections(user_message)
                if suggestions['has_suggestions']:
                    # Generate helpful response with suggestions
                    suggestion_text = self._format_symbol_suggestions(invalid_symbols, suggestions['symbol_suggestions'])
                    return {
                        'success': True,
                        'response': suggestion_text,
                        'query_analysis': parsed_query,
                        'data_sources_used': [],
                        'session_id': session_id,
                        'has_symbol_suggestions': True,
                        'symbol_suggestions': suggestions['symbol_suggestions']
                    }

            # Get relevant data based on query analysis with AI validation
            context_data = self._fetch_relevant_data(parsed_query)

            # Handle case where query assessment determined it's not worth processing
            if context_data is None and not self.query_parser.is_stock_query_worth_processing(user_message)['worth_processing']:
                # Generate general response without stock data
                response = self.gemini_client.generate_response(user_message, None)
                return {
                    'success': True,
                    'response': response,
                    'query_analysis': parsed_query,
                    'data_sources_used': [],
                    'session_id': session_id
                }

            # Generate AI response with context
            response = self._generate_contextual_response(user_message, parsed_query, context_data)

            return {
                'success': True,
                'response': response,
                'query_analysis': parsed_query,
                'data_sources_used': list(context_data.keys()) if context_data else [],
                'context_data': context_data,
                'session_id': session_id
            }

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': 'Xin lỗi, đã có lỗi xảy ra khi xử lý yêu cầu của bạn. Vui lòng thử lại.',
                'session_id': session_id
            }

    def _fetch_relevant_data(self, parsed_query: Dict) -> Optional[Dict]:
        """
        Fetch relevant data based on parsed query with AI symbol validation
        """
        context_data = {}
        stock_symbols = parsed_query.get('stock_symbols', [])
        query_types = parsed_query.get('query_type', [])
        intent = parsed_query.get('intent', '')
        date_info = parsed_query.get('date_info', {})

        # Early check if query is worth processing
        query_assessment = self.query_parser.is_stock_query_worth_processing(parsed_query['original_query'])
        if not query_assessment['worth_processing']:
            self.logger.info(f"Query not worth processing: {query_assessment['reason']}")
            return None

        # Validate symbols before making API calls
        if stock_symbols:
            validation_result = self.query_parser.validate_symbols_before_query(stock_symbols)
            if not validation_result['should_proceed']:
                self.logger.info(f"Symbol validation failed: {validation_result['reason']}")
                # Try to get suggestions for invalid symbols
                suggestions = self.query_parser.suggest_corrections(parsed_query['original_query'])
                if suggestions['has_suggestions']:
                    context_data['symbol_suggestions'] = suggestions['symbol_suggestions']
                return context_data if context_data else None

            # Use only validated symbols
            stock_symbols = validation_result['valid_symbols']
            self.logger.info(f"Validated symbols: {stock_symbols}")

        # If no stock symbols found but query seems to be about stocks, try to help
        if not stock_symbols and any(qtype in ['stock_price', 'company_info', 'financial_reports'] for qtype in query_types):
            # Try to find stock mentions in different ways
            query_lower = parsed_query['original_query'].lower()
            search_results = self.vnstock_client.search_stocks(query_lower)
            if search_results:
                # Use the first match
                stock_symbols = [search_results[0]['symbol']]
                context_data['suggested_stocks'] = search_results

        # Fetch data for each validated stock symbol
        for symbol in stock_symbols:
            symbol_data = {}

            # Stock news (using IQX API)
            if 'news' in query_types or intent == 'get_stock_news':
                # Check for date range in query
                date_info = parsed_query.get('date_info', {})
                if date_info.get('start_date') and date_info.get('end_date'):
                    # Get news with date range
                    news_data = self.iqx_news_client.get_news_by_date_range(
                        symbol, date_info['start_date'], date_info['end_date']
                    )
                else:
                    # Get latest news
                    news_data = self.iqx_news_client.get_latest_news(symbol)

                if news_data.get('success'):
                    symbol_data['news'] = news_data
                else:
                    # Log error but continue with other data
                    self.logger.warning(f"Could not get news for {symbol}: {news_data.get('error', 'Unknown error')}")

            # Company information
            if 'company_info' in query_types or intent == 'get_company_info':
                company_info = self.vnstock_client.get_company_info(symbol)
                if 'error' not in company_info:
                    symbol_data['company_info'] = company_info

            # Stock price data
            if ('stock_price' in query_types or intent in ['get_current_price', 'get_price_history', 'get_stock_analysis']):
                if date_info.get('start_date') and date_info.get('end_date'):
                    # Historical data requested
                    price_data = self.vnstock_client.get_stock_price_history(
                        symbol,
                        date_info['start_date'],
                        date_info['end_date']
                    )
                else:
                    # Current price requested (default for most queries)
                    price_data = self.vnstock_client.get_current_price(symbol)

                if price_data and 'error' not in price_data:
                    symbol_data['price_data'] = price_data
                    self.logger.info(f"Price data fetched for {symbol}: close={price_data.get('close')}, change={price_data.get('price_change')}")

            # Financial reports
            if 'financial_reports' in query_types or intent == 'get_financial_report':
                financial_data = self.vnstock_client.get_financial_reports(symbol)
                if 'error' not in financial_data:
                    symbol_data['financial_reports'] = financial_data

            if symbol_data:
                context_data[symbol] = symbol_data

        return context_data if context_data else None

    def _generate_contextual_response(self, user_message: str, parsed_query: Dict, context_data: Optional[Dict]) -> str:
        """
        Generate response using Gemini with context data
        """
        intent = parsed_query.get('intent', '')

        # Special handling for specific intents
        if intent == 'get_stock_analysis' and context_data:
            # Use specialized stock analysis method
            for symbol, data in context_data.items():
                if 'price_data' in data:
                    return self.gemini_client.analyze_stock_data(symbol, data)

        # For general queries or when no specific analysis is needed
        return self.gemini_client.generate_response(user_message, context_data)

    def _format_symbol_suggestions(self, invalid_symbols: list, suggestions: dict) -> str:
        """
        Format symbol suggestions into a helpful response
        """
        suggestion_text = "Tôi không tìm thấy mã cổ phiếu hợp lệ trong câu hỏi của bạn.\n\n"

        for invalid_symbol in invalid_symbols:
            if invalid_symbol in suggestions:
                symbol_suggestions = suggestions[invalid_symbol]
                suggestion_text += f"**Thay vì `{invalid_symbol}`, bạn có thể muốn hỏi về:**\n"
                for suggestion in symbol_suggestions[:3]:  # Limit to 3 suggestions
                    suggestion_text += f"• `{suggestion}`\n"
                suggestion_text += "\n"

        suggestion_text += "💡 **Gợi ý**: Hãy sử dụng mã cổ phiếu chính xác (ví dụ: VCB, FPT, HPG) để nhận được thông tin chi tiết."

        return suggestion_text

    def get_conversation_history(self, session_id: str = 'default') -> list:
        """
        Get conversation history for a session
        """
        # For now, we'll use the default Gemini client history
        # In a production system, you might want to store per-session histories
        return self.gemini_client.conversation_history

    def clear_conversation_history(self, session_id: str = 'default') -> bool:
        """
        Clear conversation history for a session
        """
        try:
            self.gemini_client.clear_history()
            return True
        except Exception as e:
            self.logger.error(f"Error clearing history: {e}")
            return False

    def suggest_questions(self, context: Optional[str] = None) -> list:
        """
        Suggest relevant questions user might ask
        """
        general_suggestions = [
            "Giá cổ phiếu VCB hôm nay như thế nào?",
            "Thông tin về công ty Vingroup",
            "Phân tích báo cáo tài chính của HPG",
            "So sánh VCB và TCB",
            "Lịch sử giá VIC trong 3 tháng qua",
            "Doanh thu của FPT quý gần nhất",
            "Cổ phiếu nào đáng chú ý hiện tại?",
            "Xu hướng thị trường chứng khoán"
        ]

        return general_suggestions

    def handle_followup_question(self, question: str, previous_context: Dict) -> Dict:
        """
        Handle follow-up questions with context from previous conversation
        """
        # Enhance the question with previous context
        enhanced_query = f"Dựa trên thông tin trước đó: {previous_context.get('response', '')}. Câu hỏi tiếp theo: {question}"

        return self.process_message(enhanced_query)