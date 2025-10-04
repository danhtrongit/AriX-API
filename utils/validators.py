import re
from typing import List, Optional

class InputValidator:
    @staticmethod
    def validate_stock_symbol(symbol: str) -> bool:
        """
        Validate Vietnamese stock symbol format
        """
        if not symbol:
            return False

        # Vietnamese stock symbols are typically 3-4 uppercase letters
        # Common patterns: VCB, HPG, TCBS, etc.
        symbol = symbol.upper().strip()
        pattern = r'^[A-Z]{3,4}$'

        if not re.match(pattern, symbol):
            return False

        # Additional check for known invalid patterns
        invalid_patterns = ['NAY', 'XXX', 'TEST']
        if symbol in invalid_patterns:
            return False

        return True

    @staticmethod
    def validate_date_format(date_str: str) -> bool:
        """
        Validate date format (YYYY-MM-DD)
        """
        if not date_str:
            return False

        pattern = r'^\d{4}-\d{2}-\d{2}$'
        return bool(re.match(pattern, date_str))

    @staticmethod
    def sanitize_user_input(user_input: str) -> str:
        """
        Sanitize user input to prevent injection attacks
        """
        if not user_input:
            return ""

        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\';]', '', user_input)

        # Limit length
        max_length = 1000
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized.strip()

    @staticmethod
    def validate_portfolio_holdings(holdings: List[dict]) -> bool:
        """
        Validate portfolio holdings format
        """
        if not isinstance(holdings, list):
            return False

        required_fields = ['symbol', 'shares', 'avg_price']

        for holding in holdings:
            if not isinstance(holding, dict):
                return False

            # Check required fields
            for field in required_fields:
                if field not in holding:
                    return False

            # Validate symbol
            if not InputValidator.validate_stock_symbol(holding['symbol']):
                return False

            # Validate numeric fields
            try:
                shares = float(holding['shares'])
                avg_price = float(holding['avg_price'])

                if shares <= 0 or avg_price <= 0:
                    return False

            except (ValueError, TypeError):
                return False

        return True

    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """
        Basic API key validation
        """
        if not api_key:
            return False

        # Basic length check (OpenAI API keys are typically long)
        if len(api_key) < 20:
            return False

        # Should contain alphanumeric characters and dashes
        if not re.match(r'^[a-zA-Z0-9_-]+$', api_key):
            return False

        return True

class ResponseValidator:
    @staticmethod
    def validate_stock_data(data: dict) -> bool:
        """
        Validate stock data response format
        """
        if not isinstance(data, dict):
            return False

        # Check for error field
        if 'error' in data:
            return False

        # For price data, check essential fields
        if 'close' in data or 'price' in data:
            return True

        # For company data, check if overview exists
        if 'overview' in data:
            return True

        return False

    @staticmethod
    def validate_ai_response(response: str) -> bool:
        """
        Validate AI response
        """
        if not response or not isinstance(response, str):
            return False

        # Check minimum length
        if len(response.strip()) < 5:
            return False

        # Check for obvious error patterns
        error_patterns = [
            'error occurred',
            'internal server error',
            'failed to generate',
            'api key',
            'authentication'
        ]

        response_lower = response.lower()
        for pattern in error_patterns:
            if pattern in response_lower:
                return False

        return True