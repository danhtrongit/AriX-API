import requests
import logging
from typing import Dict, Optional, List
from datetime import datetime

class IQXNewsClient:
    def __init__(self):
        self.base_url = "https://proxy.iqx.vn/proxy/ai/api/v2"
        self.logger = logging.getLogger(__name__)

    def get_stock_news(self, ticker: str, page: int = 1, page_size: int = 12,
                      industry: str = "", update_from: str = "", update_to: str = "",
                      sentiment: str = "", newsfrom: str = "", language: str = "vi") -> Dict:
        """
        Get news for a specific stock ticker using IQX API

        Args:
            ticker: Stock symbol (e.g., VIC, VCB, FPT)
            page: Page number (default: 1)
            page_size: Number of articles per page (default: 12)
            industry: Filter by industry
            update_from: Start date filter (YYYY-MM-DD)
            update_to: End date filter (YYYY-MM-DD)
            sentiment: Filter by sentiment (positive, negative, neutral)
            newsfrom: Filter by news source
            language: Language (default: vi for Vietnamese)
        """
        try:
            # Build API URL
            url = f"{self.base_url}/news_info"

            # Build parameters
            params = {
                'page': page,
                'ticker': ticker.upper(),
                'industry': industry,
                'update_from': update_from,
                'update_to': update_to,
                'sentiment': sentiment,
                'newsfrom': newsfrom,
                'language': language,
                'page_size': page_size
            }

            # Remove empty parameters
            params = {k: v for k, v in params.items() if v}

            self.logger.info(f"Fetching news for {ticker} from IQX API: {url}")

            # Make API request with timeout
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()

                # Extract news data - IQX API returns news_info array
                news_data = data.get('news_info', [])
                total_records = data.get('total_records', 0)

                # Process the response
                return {
                    'success': True,
                    'symbol': ticker.upper(),
                    'news': news_data,
                    'total_pages': (total_records + page_size - 1) // page_size,  # Calculate total pages
                    'total_articles': total_records,
                    'current_page': page,
                    'page_size': page_size,
                    'showing': len(news_data),
                    'api_source': 'IQX News API',
                    'company_name': data.get('name', ticker.upper())
                }
            else:
                error_msg = f"API returned status {response.status_code}"
                self.logger.error(f"IQX News API error for {ticker}: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'symbol': ticker.upper()
                }

        except requests.exceptions.Timeout:
            error_msg = "Request timeout - IQX API không phản hồi"
            self.logger.error(f"Timeout fetching news for {ticker}")
            return {
                'success': False,
                'error': error_msg,
                'symbol': ticker.upper()
            }

        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {str(e)}"
            self.logger.error(f"Network error fetching news for {ticker}: {e}")
            return {
                'success': False,
                'error': error_msg,
                'symbol': ticker.upper()
            }

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.error(f"Unexpected error fetching news for {ticker}: {e}")
            return {
                'success': False,
                'error': error_msg,
                'symbol': ticker.upper()
            }

    def get_latest_news(self, ticker: str, limit: int = 10) -> Dict:
        """
        Get latest news for a ticker (convenience method)
        """
        return self.get_stock_news(ticker, page=1, page_size=limit)

    def get_news_by_sentiment(self, ticker: str, sentiment: str, limit: int = 10) -> Dict:
        """
        Get news filtered by sentiment

        Args:
            ticker: Stock symbol
            sentiment: 'positive', 'negative', or 'neutral'
            limit: Number of articles
        """
        return self.get_stock_news(ticker, page=1, page_size=limit, sentiment=sentiment)

    def get_news_by_date_range(self, ticker: str, start_date: str, end_date: str, limit: int = 10) -> Dict:
        """
        Get news within a date range

        Args:
            ticker: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            limit: Number of articles
        """
        return self.get_stock_news(ticker, page=1, page_size=limit,
                                 update_from=start_date, update_to=end_date)

    def search_news(self, ticker: str, filters: Dict) -> Dict:
        """
        Search news with custom filters

        Args:
            ticker: Stock symbol
            filters: Dictionary with search filters
        """
        return self.get_stock_news(
            ticker=ticker,
            page=filters.get('page', 1),
            page_size=filters.get('page_size', 12),
            industry=filters.get('industry', ''),
            update_from=filters.get('update_from', ''),
            update_to=filters.get('update_to', ''),
            sentiment=filters.get('sentiment', ''),
            newsfrom=filters.get('newsfrom', ''),
            language=filters.get('language', 'vi')
        )