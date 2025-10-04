# from vnstock import Quote, Company, Finance
from vnstock_data import Quote, Company, Finance, Listing, Trading, TopStock, Market, Fund, CommodityPrice, Macro
from config import Config
import pandas as pd
from typing import Dict, Optional, List
import logging
from utils.json_utils import serialize_data
import warnings

class VNStockClient:
    def __init__(self):
        self.default_source = Config.VNSTOCK_DEFAULT_SOURCE
        self.logger = logging.getLogger(__name__)
        # Suppress pandas warnings về duplicate columns
        warnings.filterwarnings('ignore', message='DataFrame columns are not unique')
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean DataFrame by removing duplicate columns
        """
        if df is None or df.empty:
            return df
        
        # Check for duplicate columns and silently remove them
        if df.columns.duplicated().any():
            # Keep first occurrence of duplicate columns
            df = df.loc[:, ~df.columns.duplicated()]
        
        return df
    
    def _df_to_dict(self, df: pd.DataFrame) -> list:
        """
        Safe conversion of DataFrame to dict with duplicate column handling
        """
        if df is None or df.empty:
            return None
        
        df = self._clean_dataframe(df)
        return df.to_dict('records')

    def get_company_info(self, symbol: str) -> Dict:
        """
        Get comprehensive company information
        """
        try:
            # Company class only accepts 'VCI' source
            company = Company(symbol=symbol, source='VCI')

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
                overview = self._clean_dataframe(company.overview())
                result['overview'] = overview.to_dict('records') if overview is not None and not overview.empty else None
            except Exception as e:
                self.logger.warning(f"Could not get overview for {symbol}: {e}")

            # Get major shareholders
            try:
                shareholders = self._clean_dataframe(company.shareholders())
                result['shareholders'] = shareholders.to_dict('records') if shareholders is not None and not shareholders.empty else None
            except Exception as e:
                self.logger.warning(f"Could not get shareholders for {symbol}: {e}")

            # Get company officers
            try:
                officers = self._clean_dataframe(company.officers())
                result['officers'] = officers.to_dict('records') if officers is not None and not officers.empty else None
            except Exception as e:
                self.logger.warning(f"Could not get officers for {symbol}: {e}")

            # Get subsidiaries
            try:
                subsidiaries = self._clean_dataframe(company.subsidiaries())
                result['subsidiaries'] = subsidiaries.to_dict('records') if subsidiaries is not None and not subsidiaries.empty else None
            except Exception as e:
                self.logger.warning(f"Could not get subsidiaries for {symbol}: {e}")

            # Get recent events
            try:
                events = self._clean_dataframe(company.events())
                result['events'] = events.to_dict('records') if events is not None and not events.empty else None
            except Exception as e:
                self.logger.warning(f"Could not get events for {symbol}: {e}")

            # Note: News is now fetched via IQXNewsClient for better quality and real-time data
            # Removed company.news() to avoid redundant calls

            return result

        except Exception as e:
            self.logger.error(f"Error getting company info for {symbol}: {e}")
            return {'error': str(e)}

    def get_stock_news(self, symbol: str, limit: int = 10) -> Dict:
        """
        DEPRECATED: Use IQXNewsClient.get_latest_news() instead for better quality news data
        
        This method uses vnstock's company.news() which is less reliable.
        Kept for backward compatibility only.
        """
        self.logger.warning(f"get_stock_news is deprecated. Use IQXNewsClient instead.")
        try:
            # Company class only accepts 'VCI' source
            company = Company(symbol=symbol, source='VCI')

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

            # Clean and convert to dict
            df = self._clean_dataframe(df)
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
            # Finance class only accepts 'VCI' or 'MAS', use VCI as default
            finance = Finance(symbol=symbol, source='VCI')

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
                income = self._clean_dataframe(finance.income_statement(period=period, lang=lang))
                result['income_statement'] = income.to_dict('records') if income is not None and not income.empty else None
            except Exception as e:
                self.logger.warning(f"Could not get income statement for {symbol}: {e}")

            # Get balance sheet
            try:
                balance = self._clean_dataframe(finance.balance_sheet(period=period, lang=lang))
                result['balance_sheet'] = balance.to_dict('records') if balance is not None and not balance.empty else None
            except Exception as e:
                self.logger.warning(f"Could not get balance sheet for {symbol}: {e}")

            # Get cash flow
            try:
                cash_flow = self._clean_dataframe(finance.cash_flow(period=period, lang=lang))
                result['cash_flow'] = cash_flow.to_dict('records') if cash_flow is not None and not cash_flow.empty else None
            except Exception as e:
                self.logger.warning(f"Could not get cash flow for {symbol}: {e}")

            # Get financial ratios
            try:
                ratios = self._clean_dataframe(finance.ratio(period=period, lang=lang))
                result['financial_ratios'] = ratios.to_dict('records') if ratios is not None and not ratios.empty else None
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

    # LISTING DATA
    def get_all_symbols(self) -> Dict:
        """
        Lấy danh sách tất cả mã chứng khoán
        """
        try:
            listing = Listing(source='vnd')
            df = listing.all_symbols()
            return {
                'success': True,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting all symbols: {e}")
            return {'error': str(e)}

    # TRADING DATA
    def get_price_board(self, symbols: List[str]) -> Dict:
        """
        Lấy bảng giá giao dịch của nhiều mã
        """
        try:
            trading = Trading(symbol=symbols[0], source='vci')
            df = trading.price_board(symbols)
            return {
                'success': True,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting price board: {e}")
            return {'error': str(e)}

    def get_order_stats(self, symbol: str) -> Dict:
        """
        Lấy thống kê lệnh đặt mua/bán
        """
        try:
            trading = Trading(symbol=symbol, source='vci')
            df = trading.order_stats()
            return {
                'symbol': symbol,
                'success': True,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting order stats for {symbol}: {e}")
            return {'error': str(e)}

    def get_foreign_trade(self, symbol: str) -> Dict:
        """
        Lấy dữ liệu giao dịch khối ngoại
        """
        try:
            trading = Trading(symbol=symbol, source='vci')
            df = trading.foreign_trade()
            return {
                'symbol': symbol,
                'success': True,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting foreign trade for {symbol}: {e}")
            return {'error': str(e)}

    def get_prop_trade(self, symbol: str) -> Dict:
        """
        Lấy dữ liệu giao dịch tự doanh
        """
        try:
            trading = Trading(symbol=symbol, source='vci')
            df = trading.prop_trade()
            return {
                'symbol': symbol,
                'success': True,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting prop trade for {symbol}: {e}")
            return {'error': str(e)}

    def get_insider_deal(self, symbol: str) -> Dict:
        """
        Lấy dữ liệu giao dịch nội bộ
        """
        try:
            trading = Trading(symbol=symbol, source='vci')
            df = trading.insider_deal()
            return {
                'symbol': symbol,
                'success': True,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting insider deals for {symbol}: {e}")
            return {'error': str(e)}

    # TOP STOCK DATA
    def get_top_gainers(self, index: str = 'VNINDEX', limit: int = 10) -> Dict:
        """
        Lấy top mã tăng giá mạnh nhất
        """
        try:
            top = TopStock(source='VND')
            df = top.gainer(index=index, limit=limit)
            return {
                'success': True,
                'index': index,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting top gainers: {e}")
            return {'error': str(e)}

    def get_top_losers(self, index: str = 'VNINDEX', limit: int = 10) -> Dict:
        """
        Lấy top mã giảm giá mạnh nhất
        """
        try:
            top = TopStock(source='VND')
            df = top.loser(index=index, limit=limit)
            return {
                'success': True,
                'index': index,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting top losers: {e}")
            return {'error': str(e)}

    def get_top_by_value(self, index: str = 'VNINDEX', limit: int = 10) -> Dict:
        """
        Lấy top mã có giá trị giao dịch lớn nhất
        """
        try:
            top = TopStock(source='vci')
            df = top.value(index=index, limit=limit)
            return {
                'success': True,
                'index': index,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting top by value: {e}")
            return {'error': str(e)}

    def get_top_by_volume(self, index: str = 'VNINDEX', limit: int = 10) -> Dict:
        """
        Lấy top mã có khối lượng giao dịch lớn nhất
        """
        try:
            top = TopStock(source='VND')
            df = top.volume(index=index, limit=limit)
            return {
                'success': True,
                'index': index,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting top by volume: {e}")
            return {'error': str(e)}

    def get_top_foreign_buy(self, date: str = None) -> Dict:
        """
        Lấy top mã khối ngoại mua mạnh nhất
        """
        try:
            from datetime import datetime
            if not date:
                date = datetime.now().strftime('%Y-%m-%d')

            top = TopStock(source='VND')
            df = top.foreign_buy(date=date)
            return {
                'success': True,
                'date': date,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting top foreign buy: {e}")
            return {'error': str(e)}

    def get_top_foreign_sell(self, date: str = None) -> Dict:
        """
        Lấy top mã khối ngoại bán mạnh nhất
        """
        try:
            from datetime import datetime
            if not date:
                date = datetime.now().strftime('%Y-%m-%d')

            top = TopStock(source='VND')
            df = top.foreign_sell(date=date)
            return {
                'success': True,
                'date': date,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting top foreign sell: {e}")
            return {'error': str(e)}

    # MARKET VALUATION
    def get_market_pe(self, index: str = 'VNINDEX', duration: str = '5Y') -> Dict:
        """
        Lấy chỉ số P/E thị trường
        """
        try:
            market = Market(index=index, source='vnd')
            df = market.pe(duration=duration)
            return {
                'success': True,
                'index': index,
                'duration': duration,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting market P/E: {e}")
            return {'error': str(e)}

    def get_market_pb(self, index: str = 'VNINDEX', duration: str = '5Y') -> Dict:
        """
        Lấy chỉ số P/B thị trường
        """
        try:
            market = Market(index=index, source='vnd')
            df = market.pb(duration=duration)
            return {
                'success': True,
                'index': index,
                'duration': duration,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting market P/B: {e}")
            return {'error': str(e)}

    def get_market_evaluation(self, index: str = 'VNINDEX', duration: str = '5M') -> Dict:
        """
        Lấy chỉ số định giá tổng hợp
        """
        try:
            market = Market(index=index, source='vnd')
            df = market.evaluation(duration=duration)
            return {
                'success': True,
                'index': index,
                'duration': duration,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting market evaluation: {e}")
            return {'error': str(e)}

    # FUND DATA
    def get_fund_listing(self, fund_type: str = '') -> Dict:
        """
        Lấy danh sách quỹ mở
        fund_type: 'BALANCED', 'BOND', 'STOCK', hoặc '' cho tất cả
        """
        try:
            fund = Fund()
            df = fund.listing(fund_type=fund_type)
            return {
                'success': True,
                'fund_type': fund_type or 'all',
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting fund listing: {e}")
            return {'error': str(e)}

    def get_fund_nav(self, symbol: str) -> Dict:
        """
        Lấy lịch sử NAV của quỹ
        """
        try:
            fund = Fund()
            df = fund.details.nav_report(symbol)
            return {
                'symbol': symbol,
                'success': True,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting fund NAV for {symbol}: {e}")
            return {'error': str(e)}

    def get_fund_top_holding(self, symbol: str) -> Dict:
        """
        Lấy danh mục đầu tư top của quỹ
        """
        try:
            fund = Fund()
            df = fund.details.top_holding(symbol)
            return {
                'symbol': symbol,
                'success': True,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting fund top holding for {symbol}: {e}")
            return {'error': str(e)}

    def get_fund_industry_holding(self, symbol: str) -> Dict:
        """
        Lấy phân bổ ngành của quỹ
        """
        try:
            fund = Fund()
            df = fund.details.industry_holding(symbol)
            return {
                'symbol': symbol,
                'success': True,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting fund industry holding for {symbol}: {e}")
            return {'error': str(e)}

    def get_fund_asset_holding(self, symbol: str) -> Dict:
        """
        Lấy phân bổ tài sản của quỹ
        """
        try:
            fund = Fund()
            df = fund.details.asset_holding(symbol)
            return {
                'symbol': symbol,
                'success': True,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting fund asset holding for {symbol}: {e}")
            return {'error': str(e)}

    # COMMODITY PRICES
    def get_gold_vn(self, start: str = "2022-01-01", end: str = "2024-12-31") -> Dict:
        """
        Lấy giá vàng Việt Nam
        """
        try:
            commodity = CommodityPrice(start=start, end=end, source='spl')
            df = commodity.gold_vn()
            return {
                'success': True,
                'period': f'{start} to {end}',
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting gold VN prices: {e}")
            return {'error': str(e)}

    def get_gold_global(self, start: str = "2022-01-01", end: str = "2024-12-31") -> Dict:
        """
        Lấy giá vàng thế giới
        """
        try:
            commodity = CommodityPrice(start=start, end=end, source='spl')
            df = commodity.gold_global()
            return {
                'success': True,
                'period': f'{start} to {end}',
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting gold global prices: {e}")
            return {'error': str(e)}

    def get_oil_crude(self, start: str = "2022-01-01", end: str = "2024-12-31") -> Dict:
        """
        Lấy giá dầu thô
        """
        try:
            commodity = CommodityPrice(start=start, end=end, source='spl')
            df = commodity.oil_crude()
            return {
                'success': True,
                'period': f'{start} to {end}',
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting crude oil prices: {e}")
            return {'error': str(e)}

    def get_commodity_price(self, commodity_type: str, start: str = "2022-01-01", end: str = "2024-12-31") -> Dict:
        """
        Lấy giá hàng hóa theo loại
        commodity_type: gas_vn, gas_natural, coke, steel_d10, steel_hrc, iron_ore,
                       fertilizer_ure, soybean, corn, sugar, pork_north_vn, pork_china
        """
        try:
            commodity = CommodityPrice(start=start, end=end, source='spl')

            method_map = {
                'gas_vn': commodity.gas_vn,
                'gas_natural': commodity.gas_natural,
                'coke': commodity.coke,
                'steel_d10': commodity.steel_d10,
                'steel_hrc': commodity.steel_hrc,
                'iron_ore': commodity.iron_ore,
                'fertilizer_ure': commodity.fertilizer_ure,
                'soybean': commodity.soybean,
                'corn': commodity.corn,
                'sugar': commodity.sugar,
                'pork_north_vn': commodity.pork_north_vn,
                'pork_china': commodity.pork_china
            }

            if commodity_type not in method_map:
                return {'error': f'Invalid commodity type: {commodity_type}'}

            df = method_map[commodity_type]()
            return {
                'success': True,
                'commodity': commodity_type,
                'period': f'{start} to {end}',
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting commodity price for {commodity_type}: {e}")
            return {'error': str(e)}

    # MACRO DATA
    def get_gdp(self, start: str = "2015-01", end: str = "2025-04", period: str = "quarter") -> Dict:
        """
        Lấy dữ liệu GDP
        period: 'quarter' hoặc 'year'
        """
        try:
            macro = Macro(source='mbk')
            df = macro.gdp(start=start, end=end, period=period, keep_label=False)
            return {
                'success': True,
                'period': period,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting GDP data: {e}")
            return {'error': str(e)}

    def get_cpi(self, start: str = "2015-01", end: str = "2025-04", period: str = "month") -> Dict:
        """
        Lấy dữ liệu CPI
        period: 'month' hoặc 'year'
        """
        try:
            macro = Macro(source='mbk')
            df = macro.cpi(start=start, end=end, period=period)
            return {
                'success': True,
                'period': period,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting CPI data: {e}")
            return {'error': str(e)}

    def get_industry_production(self, start: str = "2015-01", end: str = "2025-04", period: str = "month") -> Dict:
        """
        Lấy dữ liệu sản xuất công nghiệp
        period: 'month' hoặc 'year'
        """
        try:
            macro = Macro(source='mbk')
            df = macro.industry_prod(start=start, end=end, period=period)
            return {
                'success': True,
                'period': period,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting industry production data: {e}")
            return {'error': str(e)}

    def get_retail(self, start: str = "2015-01", end: str = "2025-04", period: str = "month") -> Dict:
        """
        Lấy dữ liệu bán lẻ
        period: 'month' hoặc 'year'
        """
        try:
            macro = Macro(source='mbk')
            df = macro.retail(start=start, end=end, period=period)
            return {
                'success': True,
                'period': period,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting retail data: {e}")
            return {'error': str(e)}

    def get_import_export(self, start: str = "2015-01", end: str = "2025-04", period: str = "month") -> Dict:
        """
        Lấy dữ liệu xuất nhập khẩu
        period: 'month' hoặc 'year'
        """
        try:
            macro = Macro(source='mbk')
            df = macro.import_export(start=start, end=end, period=period)
            return {
                'success': True,
                'period': period,
                'data': serialize_data(df.to_dict('records'))
            }
        except Exception as e:
            self.logger.error(f"Error getting import/export data: {e}")
            return {'error': str(e)}