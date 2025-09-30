from models.gemini_client import GeminiClient
from models.vnstock_client import VNStockClient
from models.iqx_news_client import IQXNewsClient
from services.query_parser import QueryParser
from services.query_analyzer import QueryAnalyzer
from services.data_fetcher import DataFetcher
from typing import Dict, Optional
import logging

class ChatService:
    def __init__(self):
        self.gemini_client = GeminiClient()
        self.vnstock_client = VNStockClient()
        self.iqx_news_client = IQXNewsClient()
        self.query_parser = QueryParser()
        self.query_analyzer = QueryAnalyzer()
        self.data_fetcher = DataFetcher()
        self.logger = logging.getLogger(__name__)

    def process_message(self, user_message: str, session_id: str = 'default') -> Dict:
        """
        Process user message - 2 bước tối ưu:
        Bước 1: AI phân tích câu hỏi -> xác định symbols + API calls
        Bước 2: Fetch data -> AI phân tích toàn bộ dữ liệu -> trả lời
        """
        try:
            # BƯỚC 1: AI phân tích câu hỏi
            self.logger.info(f"[Step 1] Analyzing query: {user_message}")
            analysis = self.query_analyzer.analyze_query(user_message)

            # Kiểm tra nếu không liên quan chứng khoán
            if analysis['query_intent'] == 'general' and not analysis['symbols']:
                response = self.gemini_client.generate_response(user_message, None)
                return {
                    'success': True,
                    'response': response,
                    'query_analysis': analysis,
                    'data_sources_used': [],
                    'session_id': session_id
                }

            # Fetch dữ liệu dựa trên analysis
            self.logger.info(f"[Step 1] Analysis result: symbols={analysis['symbols']}, api_calls={len(analysis['api_calls'])}")

            # BƯỚC 2: Fetch data và AI phân tích
            if analysis['api_calls']:
                self.logger.info(f"[Step 2] Fetching data from {len(analysis['api_calls'])} API calls")
                fetched_data = self.data_fetcher.fetch_data(analysis['api_calls'])

                # AI phân tích toàn bộ dữ liệu và trả lời
                self.logger.info(f"[Step 2] AI analyzing fetched data")
                response = self._generate_ai_response(user_message, analysis, fetched_data)

                return {
                    'success': True,
                    'response': response,
                    'query_analysis': analysis,
                    'fetched_data': fetched_data,
                    'data_sources_used': list(fetched_data.keys()),
                    'session_id': session_id
                }
            else:
                # Không có API calls cần thực hiện
                response = self.gemini_client.generate_response(user_message, None)
                return {
                    'success': True,
                    'response': response,
                    'query_analysis': analysis,
                    'data_sources_used': [],
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

    def _generate_ai_response(self, user_query: str, analysis: Dict, fetched_data: Dict) -> str:
        """
        AI phân tích toàn bộ dữ liệu và trả lời ngắn gọn, đúng trọng tâm
        """
        try:
            # Build context for AI
            context_prompt = self._build_context_prompt(user_query, analysis, fetched_data)

            # Generate response
            response = self.gemini_client.model.generate_content(context_prompt)

            return response.text.strip()

        except Exception as e:
            self.logger.error(f"Error generating AI response: {e}")
            return "Xin lỗi, không thể phân tích dữ liệu. Vui lòng thử lại."

    def _build_context_prompt(self, user_query: str, analysis: Dict, fetched_data: Dict) -> str:
        """
        Tạo prompt cho AI với toàn bộ dữ liệu
        """
        import json

        prompt = f"""Bạn là trợ lý phân tích chứng khoán chuyên nghiệp.

Câu hỏi của người dùng: "{user_query}"

Phân tích câu hỏi:
- Mã cổ phiếu: {', '.join(analysis.get('symbols', []))}
- Ý định: {analysis.get('query_intent')}

Dữ liệu đã thu thập:
{json.dumps(fetched_data, ensure_ascii=False, indent=2)}

Yêu cầu:
1. Phân tích dữ liệu trên
2. Trả lời NGẮN GỌN, ĐÚNG TRỌNG TÂM câu hỏi
3. KHÔNG đưa ra khuyến nghị mua/bán
4. KHÔNG dài dòng, chỉ trả lời đúng câu hỏi
5. Sử dụng số liệu cụ thể từ dữ liệu

Trả lời:"""

        return prompt

    def _fetch_relevant_data(self, parsed_query: Dict) -> Optional[Dict]:
        """
        Fetch relevant data based on parsed query with AI symbol validation
        """
        context_data = {}
        stock_symbols = parsed_query.get('stock_symbols', [])
        query_types = parsed_query.get('query_type', [])
        intent = parsed_query.get('intent', '')
        date_info = parsed_query.get('date_info', {})
        user_message = parsed_query.get('original_query', '').lower()  # Get original query

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
            if ('stock_price' in query_types or intent in ['get_current_price', 'get_price_history', 'get_price_chart', 'get_stock_analysis']):
                self.logger.info(f"Processing price data for {symbol}, intent: {intent}, user_message: {user_message}")
                if intent == 'get_price_chart' or 'biểu đồ' in user_message or 'chart' in user_message:
                    self.logger.info(f"Chart request detected for {symbol}")
                    # Chart request - get 30 days historical data by default
                    from datetime import datetime, timedelta
                    end_date = datetime.now().strftime('%Y-%m-%d')
                    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

                    price_data = self.vnstock_client.get_stock_price_history(
                        symbol, start_date, end_date
                    )
                    if price_data and 'error' not in price_data:
                        # Format data for chart rendering
                        price_data['chart_type'] = 'candlestick'
                        price_data['chart_ready'] = True
                        symbol_data['price_data'] = price_data

                elif date_info.get('start_date') and date_info.get('end_date'):
                    # Historical data requested
                    price_data = self.vnstock_client.get_stock_price_history(
                        symbol,
                        date_info['start_date'],
                        date_info['end_date']
                    )
                else:
                    # Current price requested (default for most queries)
                    price_data = self.vnstock_client.get_current_price(symbol)

                if price_data and 'error' not in price_data and 'chart_ready' not in price_data:
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
        self.logger.info(f"Detected intent: {intent}")

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