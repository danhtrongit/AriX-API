import pytest
import sys
import os

# Add the parent directory to sys.path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from services.query_parser import QueryParser
from utils.validators import InputValidator, ResponseValidator

@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def query_parser():
    """Create a QueryParser instance for testing"""
    return QueryParser()

class TestAPI:
    """Test API endpoints"""

    def test_health_check(self, client):
        """Test the health check endpoint"""
        response = client.get('/')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert 'message' in data

    def test_chat_endpoint_missing_message(self, client):
        """Test chat endpoint with missing message"""
        response = client.post('/api/chat', json={})
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'Message is required' in data['error']

    def test_chat_endpoint_empty_message(self, client):
        """Test chat endpoint with empty message"""
        response = client.post('/api/chat', json={'message': ''})
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    def test_stock_info_invalid_symbol(self, client):
        """Test stock info endpoint with invalid symbol"""
        response = client.get('/api/stock/INVALID123')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'Invalid stock symbol format' in data['error']

    def test_stock_price_invalid_symbol(self, client):
        """Test stock price endpoint with invalid symbol"""
        response = client.get('/api/stock/INVALID123/price')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    def test_stock_price_invalid_date_format(self, client):
        """Test stock price endpoint with invalid date format"""
        response = client.get('/api/stock/VCB/price?start_date=invalid&end_date=invalid')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'Invalid date format' in data['error']

    def test_compare_stocks_missing_symbols(self, client):
        """Test compare stocks endpoint with missing symbols"""
        response = client.post('/api/stocks/compare', json={})
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'Stock symbols are required' in data['error']

    def test_compare_stocks_invalid_symbol(self, client):
        """Test compare stocks endpoint with invalid symbol"""
        response = client.post('/api/stocks/compare', json={'symbols': ['INVALID123']})
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'Invalid stock symbol' in data['error']

    def test_portfolio_analyze_missing_holdings(self, client):
        """Test portfolio analyze endpoint with missing holdings"""
        response = client.post('/api/portfolio/analyze', json={})
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'Holdings data is required' in data['error']

    def test_suggestions_endpoint(self, client):
        """Test suggestions endpoint"""
        response = client.get('/api/suggestions')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'suggestions' in data
        assert isinstance(data['suggestions'], list)

class TestQueryParser:
    """Test QueryParser functionality"""

    def test_extract_stock_symbols(self, query_parser):
        """Test stock symbol extraction"""
        query = "Thông tin về cổ phiếu VCB và HPG"
        parsed = query_parser.parse_query(query)
        assert 'VCB' in parsed['stock_symbols']
        assert 'HPG' in parsed['stock_symbols']

    def test_identify_query_type_company_info(self, query_parser):
        """Test query type identification for company info"""
        query = "Thông tin công ty VCB"
        parsed = query_parser.parse_query(query)
        assert 'company_info' in parsed['query_type']

    def test_identify_query_type_stock_price(self, query_parser):
        """Test query type identification for stock price"""
        query = "Giá cổ phiếu VCB hôm nay"
        parsed = query_parser.parse_query(query)
        assert 'stock_price' in parsed['query_type']

    def test_extract_date_info_today(self, query_parser):
        """Test date extraction for 'hôm nay'"""
        query = "Giá VCB hôm nay"
        parsed = query_parser.parse_query(query)
        date_info = parsed['date_info']
        assert date_info['period_type'] == 'named_period'
        assert date_info['relative_period'] == 'hôm nay'

    def test_extract_date_range(self, query_parser):
        """Test date range extraction"""
        query = "Giá VCB từ 01/01/2024 đến 31/01/2024"
        parsed = query_parser.parse_query(query)
        date_info = parsed['date_info']
        assert date_info['period_type'] == 'custom_range'
        assert date_info['start_date'] is not None
        assert date_info['end_date'] is not None

    def test_determine_intent_current_price(self, query_parser):
        """Test intent determination for current price"""
        query = "Giá hiện tại của VCB"
        parsed = query_parser.parse_query(query)
        assert parsed['intent'] == 'get_current_price'

    def test_determine_intent_analysis(self, query_parser):
        """Test intent determination for analysis"""
        query = "Phân tích cổ phiếu VCB"
        parsed = query_parser.parse_query(query)
        assert parsed['intent'] == 'get_stock_analysis'

class TestValidators:
    """Test validation functions"""

    def test_validate_stock_symbol_valid(self):
        """Test valid stock symbol validation"""
        assert InputValidator.validate_stock_symbol('VCB') is True
        assert InputValidator.validate_stock_symbol('HPG') is True
        assert InputValidator.validate_stock_symbol('TCBS') is True

    def test_validate_stock_symbol_invalid(self):
        """Test invalid stock symbol validation"""
        assert InputValidator.validate_stock_symbol('') is False
        assert InputValidator.validate_stock_symbol('INVALID123') is False
        assert InputValidator.validate_stock_symbol('A') is False
        assert InputValidator.validate_stock_symbol('TOOLONG') is False

    def test_validate_date_format_valid(self):
        """Test valid date format validation"""
        assert InputValidator.validate_date_format('2024-01-01') is True
        assert InputValidator.validate_date_format('2023-12-31') is True

    def test_validate_date_format_invalid(self):
        """Test invalid date format validation"""
        assert InputValidator.validate_date_format('') is False
        assert InputValidator.validate_date_format('2024/01/01') is False
        assert InputValidator.validate_date_format('01-01-2024') is False
        assert InputValidator.validate_date_format('invalid') is False

    def test_sanitize_user_input(self):
        """Test user input sanitization"""
        clean_input = InputValidator.sanitize_user_input("Giá VCB hôm nay")
        assert clean_input == "Giá VCB hôm nay"

        malicious_input = InputValidator.sanitize_user_input("<script>alert('xss')</script>")
        assert '<script>' not in malicious_input
        assert 'alert(' not in malicious_input

    def test_validate_portfolio_holdings_valid(self):
        """Test valid portfolio holdings validation"""
        holdings = [
            {'symbol': 'VCB', 'shares': 100, 'avg_price': 95000},
            {'symbol': 'HPG', 'shares': 200, 'avg_price': 25000}
        ]
        assert InputValidator.validate_portfolio_holdings(holdings) is True

    def test_validate_portfolio_holdings_invalid(self):
        """Test invalid portfolio holdings validation"""
        # Missing required fields
        holdings = [{'symbol': 'VCB'}]
        assert InputValidator.validate_portfolio_holdings(holdings) is False

        # Invalid symbol
        holdings = [{'symbol': 'INVALID123', 'shares': 100, 'avg_price': 95000}]
        assert InputValidator.validate_portfolio_holdings(holdings) is False

        # Negative values
        holdings = [{'symbol': 'VCB', 'shares': -100, 'avg_price': 95000}]
        assert InputValidator.validate_portfolio_holdings(holdings) is False

    def test_validate_ai_response_valid(self):
        """Test valid AI response validation"""
        assert ResponseValidator.validate_ai_response("Đây là một phản hồi hợp lệ từ AI") is True

    def test_validate_ai_response_invalid(self):
        """Test invalid AI response validation"""
        assert ResponseValidator.validate_ai_response("") is False
        assert ResponseValidator.validate_ai_response(None) is False
        assert ResponseValidator.validate_ai_response("abc") is False  # Too short
        assert ResponseValidator.validate_ai_response("API key error occurred") is False  # Error pattern