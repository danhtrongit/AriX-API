# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
from flask_cors import CORS
from config import Config
from services.chat_service import ChatService
from services.data_service import DataService
from models.iqx_news_client import IQXNewsClient
from utils.logger import setup_logger
from utils.validators import InputValidator, ResponseValidator
from utils.json_utils import CustomJSONEncoder, serialize_data
import traceback
import json

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
app.json_encoder = CustomJSONEncoder
CORS(app)

# Setup logging
logger = setup_logger(__name__, Config.LOG_LEVEL)

# Initialize services
chat_service = ChatService()
data_service = DataService()
iqx_news_client = IQXNewsClient()

@app.route('/', methods=['GET'])
def health_check():
    """
    Health check endpoint
    """
    return jsonify({
        'status': 'healthy',
        'message': 'VNStock AI Chatbot API is running',
        'version': '1.0.0'
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint
    """
    try:
        data = request.get_json()

        if not data or 'message' not in data:
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400

        user_message = data['message']
        session_id = data.get('session_id', 'default')

        # Validate and sanitize input
        user_message = InputValidator.sanitize_user_input(user_message)

        if not user_message:
            return jsonify({
                'success': False,
                'error': 'Invalid message format'
            }), 400

        # Process message
        result = chat_service.process_message(user_message, session_id)

        # Serialize the result to handle NaN values
        result = serialize_data(result)

        # Validate response
        if result['success'] and not ResponseValidator.validate_ai_response(result['response']):
            logger.warning("AI response failed validation")
            result['response'] = "Xin loi, toi khong the tao ra cau tra loi phu hop. Vui long thu lai."

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'Da co loi xay ra. Vui long thu lai sau.'
        }), 500

@app.route('/api/stock/<symbol>', methods=['GET'])
def get_stock_info(symbol):
    """
    Get detailed stock information
    """
    try:
        # Validate stock symbol
        if not InputValidator.validate_stock_symbol(symbol):
            return jsonify({
                'success': False,
                'error': 'Invalid stock symbol format'
            }), 400

        symbol = symbol.upper()

        # Get query parameters
        include_company = request.args.get('include_company', 'true').lower() == 'true'
        include_financial = request.args.get('include_financial', 'false').lower() == 'true'
        include_price = request.args.get('include_price', 'true').lower() == 'true'

        result = {'symbol': symbol, 'data': {}}

        # Get company info
        if include_company:
            company_info = chat_service.vnstock_client.get_company_info(symbol)
            if 'error' not in company_info:
                result['data']['company'] = company_info

        # Get price info
        if include_price:
            price_info = chat_service.vnstock_client.get_current_price(symbol)
            if 'error' not in price_info:
                result['data']['price'] = price_info

        # Get financial reports
        if include_financial:
            financial_info = chat_service.vnstock_client.get_financial_reports(symbol)
            if 'error' not in financial_info:
                result['data']['financial'] = financial_info

        return jsonify({
            'success': True,
            'result': result
        })

    except Exception as e:
        logger.error(f"Error in stock info endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/stock/<symbol>/price', methods=['GET'])
def get_stock_price(symbol):
    """
    Get stock price information
    """
    try:
        if not InputValidator.validate_stock_symbol(symbol):
            return jsonify({
                'success': False,
                'error': 'Invalid stock symbol format'
            }), 400

        symbol = symbol.upper()

        # Get query parameters for date range
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if start_date and end_date:
            # Validate dates
            if not (InputValidator.validate_date_format(start_date) and
                    InputValidator.validate_date_format(end_date)):
                return jsonify({
                    'success': False,
                    'error': 'Invalid date format. Use YYYY-MM-DD'
                }), 400

            # Get historical price data
            price_data = chat_service.vnstock_client.get_stock_price_history(
                symbol, start_date, end_date
            )
        else:
            # Get current price
            price_data = chat_service.vnstock_client.get_current_price(symbol)

        if 'error' in price_data:
            return jsonify({
                'success': False,
                'error': price_data['error']
            }), 404

        return jsonify({
            'success': True,
            'data': price_data
        })

    except Exception as e:
        logger.error(f"Error in stock price endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/market/summary', methods=['GET'])
def get_market_summary():
    """
    Get market summary
    """
    try:
        summary = data_service.get_market_summary()
        return jsonify(summary)

    except Exception as e:
        logger.error(f"Error in market summary endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/portfolio/analyze', methods=['POST'])
def analyze_portfolio():
    """
    Analyze portfolio holdings
    """
    try:
        data = request.get_json()

        if not data or 'holdings' not in data:
            return jsonify({
                'success': False,
                'error': 'Holdings data is required'
            }), 400

        holdings = data['holdings']

        # Validate holdings format
        if not InputValidator.validate_portfolio_holdings(holdings):
            return jsonify({
                'success': False,
                'error': 'Invalid holdings format'
            }), 400

        # Calculate portfolio metrics
        result = data_service.calculate_portfolio_metrics(holdings)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in portfolio analysis endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/stocks/compare', methods=['POST'])
def compare_stocks():
    """
    Compare multiple stocks
    """
    try:
        data = request.get_json()

        if not data or 'symbols' not in data:
            return jsonify({
                'success': False,
                'error': 'Stock symbols are required'
            }), 400

        symbols = data['symbols']
        metrics = data.get('metrics', ['current_price', 'company_overview'])

        # Validate symbols
        for symbol in symbols:
            if not InputValidator.validate_stock_symbol(symbol):
                return jsonify({
                    'success': False,
                    'error': f'Invalid stock symbol: {symbol}'
                }), 400

        # Convert to uppercase
        symbols = [s.upper() for s in symbols]

        result = data_service.compare_stocks(symbols, metrics)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in stock comparison endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/chat/history', methods=['GET'])
def get_chat_history():
    """
    Get chat history for a session
    """
    try:
        session_id = request.args.get('session_id', 'default')
        history = chat_service.get_conversation_history(session_id)

        return jsonify({
            'success': True,
            'history': history,
            'session_id': session_id
        })

    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/chat/clear', methods=['POST'])
def clear_chat_history():
    """
    Clear chat history for a session
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id', 'default') if data else 'default'

        success = chat_service.clear_conversation_history(session_id)

        return jsonify({
            'success': success,
            'message': 'Chat history cleared' if success else 'Failed to clear history'
        })

    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/stocks/validate/<symbol>', methods=['GET'])
def validate_stock_symbol(symbol):
    """
    Validate if a stock symbol is valid
    """
    try:
        is_valid = InputValidator.validate_stock_symbol(symbol)

        result = {
            'symbol': symbol.upper(),
            'is_valid': is_valid
        }

        if is_valid:
            # Try to get basic data to confirm symbol exists
            price_data = chat_service.vnstock_client.get_current_price(symbol.upper())
            result['exists'] = 'error' not in price_data
            if 'error' in price_data:
                result['error'] = price_data['error']
        else:
            result['exists'] = False
            result['error'] = 'Invalid symbol format'

        return jsonify({
            'success': True,
            'result': result
        })

    except Exception as e:
        logger.error(f"Error validating symbol {symbol}: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/suggestions', methods=['GET'])
def get_suggestions():
    """
    Get conversation starter suggestions
    """
    try:
        suggestions = chat_service.suggest_questions()
        return jsonify({
            'success': True,
            'suggestions': suggestions
        })

    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        'success': False,
        'error': 'Method not allowed'
    }), 405

@app.route('/api/news/<symbol>', methods=['GET'])
def get_stock_news(symbol):
    """
    Get news for a specific stock symbol using IQX News API

    Query parameters:
    - page: Page number (default: 1)
    - page_size: Articles per page (default: 12)
    - sentiment: Filter by sentiment (positive, negative, neutral)
    - update_from: Start date (YYYY-MM-DD)
    - update_to: End date (YYYY-MM-DD)
    - newsfrom: News source filter
    """
    try:
        # Validate symbol
        if not symbol or len(symbol) < 2:
            return jsonify({
                'success': False,
                'error': 'Invalid stock symbol'
            }), 400

        # Get query parameters
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 12, type=int)
        sentiment = request.args.get('sentiment', '')
        update_from = request.args.get('update_from', '')
        update_to = request.args.get('update_to', '')
        newsfrom = request.args.get('newsfrom', '')

        # Validate parameters
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 50:
            page_size = 12

        # Get news using IQX API
        if update_from and update_to:
            # Date range query
            result = iqx_news_client.get_news_by_date_range(symbol, update_from, update_to, page_size)
        elif sentiment:
            # Sentiment filter query
            result = iqx_news_client.get_news_by_sentiment(symbol, sentiment, page_size)
        else:
            # Standard query with all parameters
            result = iqx_news_client.get_stock_news(
                ticker=symbol,
                page=page,
                page_size=page_size,
                sentiment=sentiment,
                update_from=update_from,
                update_to=update_to,
                newsfrom=newsfrom
            )

        return jsonify(serialize_data(result))

    except Exception as e:
        logger.error(f"Error in news endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

if __name__ == '__main__':
    logger.info("Starting VNStock AI Chatbot API...")
    app.run(
        debug=Config.DEBUG,
        host='0.0.0.0',
        port=5005
    )