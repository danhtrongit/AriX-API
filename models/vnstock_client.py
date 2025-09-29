from vnstock import Quote, Company, Finance
from config import Config
import pandas as pd
from typing import Dict, Optional, List
import logging
from utils.json_utils import serialize_data

class VNStockClient:
    def __init__(self):
        self.default_source = Config.VNSTOCK_DEFAULT_SOURCE
        self.logger = logging.getLogger(__name__)

    def get_company_info(self, symbol: str) -> Dict:
        """
        Get comprehensive company information
        """
        try:
            company = Company(symbol=symbol, source=self.default_source)

            result = {
                'symbol': symbol,
                'overview': None,
                'shareholders': None,
                'officers': None,
                'subsidiaries': None,
                'events': None,
                'news': None,
                'reports': None,
                'ratio_summary': None,
                'trading_stats': None
            }

            # Get company overview
            try:
                overview = company.overview()
                result['overview'] = overview.to_dict('records') if not overview.empty else None
            except Exception as e:
                self.logger.warning(f"Could not get overview for {symbol}: {e}")

            # Get major shareholders
            try:
                shareholders = company.shareholders()
                result['shareholders'] = shareholders.to_dict('records') if not shareholders.empty else None
            except Exception as e:
                self.logger.warning(f"Could not get shareholders for {symbol}: {e}")

            # Get company officers
            try:
                officers = company.officers()
                result['officers'] = officers.to_dict('records') if not officers.empty else None
            except Exception as e:
                self.logger.warning(f"Could not get officers for {symbol}: {e}")

            # Get subsidiaries
            try:
                subsidiaries = company.subsidiaries()
                result['subsidiaries'] = subsidiaries.to_dict('records') if not subsidiaries.empty else None
            except Exception as e:
                self.logger.warning(f"Could not get subsidiaries for {symbol}: {e}")

            # Get recent events
            try:
                events = company.events()
                result['events'] = events.to_dict('records') if not events.empty else None
            except Exception as e:
                self.logger.warning(f"Could not get events for {symbol}: {e}")

            # Get recent news
            try:
                news = company.news()
                result['news'] = news.to_dict('records') if not news.empty else None
            except Exception as e:
                self.logger.warning(f"Could not get news for {symbol}: {e}")

            return result

        except Exception as e:
            self.logger.error(f"Error getting company info for {symbol}: {e}")
            return {'error': str(e)}

    def get_stock_news(self, symbol: str, limit: int = 10) -> Dict:
        """
        Get recent news for a specific stock symbol
        """
        try:
            company = Company(symbol=symbol, source=self.default_source)

            # Get recent news
            news_df = company.news()

            if news_df.empty:
                return {
                    'symbol': symbol,
                    'news': [],
                    'message': f'Không tìm thấy tin tức mới nhất cho mã {symbol}'
                }

            # Limit results and serialize
            limited_news = news_df.head(limit) if len(news_df) > limit else news_df
            news_data = serialize_data(limited_news.to_dict('records'))

            return {
                'symbol': symbol,
                'news': news_data,
                'total_articles': len(news_df),
                'showing': len(limited_news)
            }

        except Exception as e:
            self.logger.error(f"Error getting news for {symbol}: {e}")
            return {'error': f'Không thể lấy tin tức cho mã {symbol}: {str(e)}'}

    def get_stock_price_history(self, symbol: str, start_date: str, end_date: str, interval: str = '1D') -> Dict:
        """
        Get historical stock price data
        """
        try:
            # Validate symbol first
            if not symbol or len(symbol) < 3:
                return {'error': f'Invalid symbol: {symbol}'}

            quote = Quote(symbol=symbol, source='VCI')

            # Add timeout and retry logic
            import time
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    df = quote.history(start=start_date, end=end_date, interval=interval)
                    break
                except Exception as retry_error:
                    self.logger.warning(f"Attempt {attempt + 1} failed for {symbol}: {retry_error}")
                    if attempt == max_retries - 1:
                        raise retry_error
                    time.sleep(1)  # Wait 1 second before retry

            if df is None or df.empty:
                return {'error': f'No data found for symbol {symbol}. Symbol may not exist or data unavailable for the specified period.'}

            # Convert to dict and add summary statistics
            data_records = df.to_dict('records')
            result = {
                'symbol': symbol,
                'period': f'{start_date} to {end_date}',
                'data': serialize_data(data_records),
                'summary': serialize_data({
                    'total_records': len(df),
                    'avg_price': df['close'].mean() if 'close' in df.columns else None,
                    'max_price': df['high'].max() if 'high' in df.columns else None,
                    'min_price': df['low'].min() if 'low' in df.columns else None,
                    'avg_volume': df['volume'].mean() if 'volume' in df.columns else None,
                    'total_volume': df['volume'].sum() if 'volume' in df.columns else None,
                    'price_change': None,
                    'price_change_percent': None
                })
            }

            # Calculate price change if data available
            if len(df) > 1 and 'close' in df.columns:
                first_price = df['close'].iloc[0]
                last_price = df['close'].iloc[-1]
                result['summary']['price_change'] = serialize_data(last_price - first_price)
                result['summary']['price_change_percent'] = serialize_data(((last_price - first_price) / first_price) * 100)

            return result

        except Exception as e:
            error_msg = str(e)
            if 'RetryError' in error_msg:
                error_msg = f'Unable to fetch data for {symbol}. This may be due to network issues or the symbol may not exist.'
            elif 'ValueError' in error_msg:
                error_msg = f'Invalid symbol or date format for {symbol}.'

            self.logger.error(f"Error getting price history for {symbol}: {e}")
            return {'error': error_msg}

    def get_financial_reports(self, symbol: str, period: str = 'year', lang: str = 'vi') -> Dict:
        """
        Get financial reports (income statement, balance sheet, cash flow)
        """
        try:
            finance = Finance(symbol=symbol, source=self.default_source)

            result = {
                'symbol': symbol,
                'period': period,
                'language': lang,
                'income_statement': None,
                'balance_sheet': None,
                'cash_flow': None,
                'financial_ratios': None
            }

            # Get income statement
            try:
                income = finance.income_statement(period=period, lang=lang)
                result['income_statement'] = income.to_dict('records') if not income.empty else None
            except Exception as e:
                self.logger.warning(f"Could not get income statement for {symbol}: {e}")

            # Get balance sheet
            try:
                balance = finance.balance_sheet(period=period, lang=lang)
                result['balance_sheet'] = balance.to_dict('records') if not balance.empty else None
            except Exception as e:
                self.logger.warning(f"Could not get balance sheet for {symbol}: {e}")

            # Get cash flow
            try:
                cash_flow = finance.cash_flow(period=period, lang=lang)
                result['cash_flow'] = cash_flow.to_dict('records') if not cash_flow.empty else None
            except Exception as e:
                self.logger.warning(f"Could not get cash flow for {symbol}: {e}")

            # Get financial ratios
            try:
                ratios = finance.ratio(period=period, lang=lang)
                result['financial_ratios'] = ratios.to_dict('records') if not ratios.empty else None
            except Exception as e:
                self.logger.warning(f"Could not get financial ratios for {symbol}: {e}")

            return result

        except Exception as e:
            self.logger.error(f"Error getting financial reports for {symbol}: {e}")
            return {'error': str(e)}

    def get_current_price(self, symbol: str) -> Dict:
        """
        Get current/latest price information
        """
        try:
            # Validate symbol first
            if not symbol or len(symbol) < 3:
                return {'error': f'Invalid symbol: {symbol}'}

            quote = Quote(symbol=symbol, source='VCI')

            # Add timeout and retry logic
            import time
            from datetime import datetime, timedelta

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Get latest 3 days data to ensure we get current price
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=3)

                    df = quote.history(
                        start=start_date.strftime('%Y-%m-%d'),
                        end=end_date.strftime('%Y-%m-%d'),
                        interval='1D'
                    )
                    break
                except Exception as retry_error:
                    self.logger.warning(f"Attempt {attempt + 1} failed for {symbol}: {retry_error}")
                    if attempt == max_retries - 1:
                        raise retry_error
                    time.sleep(1)  # Wait 1 second before retry

            if df is None or df.empty:
                return {'error': f'Không có dữ liệu giá cho mã {symbol}. Mã có thể không tồn tại hoặc thị trường đang đóng cửa.'}

            # Get the latest row (most recent data)
            latest = df.iloc[-1]

            result = {
                'symbol': symbol,
                'timestamp': serialize_data(latest.name),
                'open': serialize_data(latest.get('open')),
                'high': serialize_data(latest.get('high')),
                'low': serialize_data(latest.get('low')),
                'close': serialize_data(latest.get('close')),
                'volume': serialize_data(latest.get('volume')),
                'source': self.default_source
            }

            # Calculate price change if we have multiple days
            if len(df) > 1:
                previous = df.iloc[-2]
                current_price = latest.get('close', 0)
                previous_price = previous.get('close', 0)

                if previous_price and current_price:
                    change = current_price - previous_price
                    change_percent = (change / previous_price) * 100
                    result['price_change'] = serialize_data(change)
                    result['price_change_percent'] = serialize_data(change_percent)
                else:
                    result['price_change'] = serialize_data(0)
                    result['price_change_percent'] = serialize_data(0)
            else:
                result['price_change'] = serialize_data(0)
                result['price_change_percent'] = serialize_data(0)

            return result

        except Exception as e:
            error_msg = str(e)
            if 'RetryError' in error_msg:
                error_msg = f'Unable to fetch current price for {symbol}. This may be due to network issues or the symbol may not exist.'
            elif 'ValueError' in error_msg:
                error_msg = f'Invalid symbol: {symbol}.'

            self.logger.error(f"Error getting current price for {symbol}: {e}")
            return {'error': error_msg}

    def search_stocks(self, query: str) -> List[Dict]:
        """
        Search for stocks by name or symbol (basic implementation)
        """
        # This is a basic implementation - in practice, you might want to maintain
        # a list of all available stocks or use a more sophisticated search
        common_stocks = [
            {'symbol': 'VCB', 'name': 'Vietcombank'},
            {'symbol': 'VIC', 'name': 'Vingroup'},
            {'symbol': 'VHM', 'name': 'Vinhomes'},
            {'symbol': 'VRE', 'name': 'Vincom Retail'},
            {'symbol': 'HPG', 'name': 'Hoa Phat Group'},
            {'symbol': 'TCB', 'name': 'Techcombank'},
            {'symbol': 'ACB', 'name': 'Asia Commercial Bank'},
            {'symbol': 'MBB', 'name': 'Military Bank'},
            {'symbol': 'STB', 'name': 'Sacombank'},
            {'symbol': 'FPT', 'name': 'FPT Corporation'}
        ]

        query_lower = query.lower()
        results = []

        for stock in common_stocks:
            if (query_lower in stock['symbol'].lower() or
                query_lower in stock['name'].lower()):
                results.append(stock)

        return results