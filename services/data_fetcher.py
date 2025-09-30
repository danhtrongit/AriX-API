from models.vnstock_client import VNStockClient
from models.iqx_news_client import IQXNewsClient
from typing import Dict, List, Optional
import logging

class DataFetcher:
    """
    Thực hiện các API calls dựa trên kết quả phân tích từ QueryAnalyzer
    """
    def __init__(self):
        self.vnstock_client = VNStockClient()
        self.iqx_news_client = IQXNewsClient()
        self.logger = logging.getLogger(__name__)

    def fetch_data(self, api_calls: List[Dict]) -> Dict:
        """
        Thực hiện tất cả API calls và tổng hợp dữ liệu

        Args:
            api_calls: List of API call specs from QueryAnalyzer
                [
                    {
                        'service': 'get_current_price',
                        'params': {'symbol': 'VCB'}
                    }
                ]

        Returns:
            {
                'VCB': {
                    'current_price': {...},
                    'company_info': {...}
                },
                'market_data': {...},
                'errors': [...]
            }
        """
        results = {}
        errors = []

        for api_call in api_calls:
            try:
                service = api_call.get('service')
                params = api_call.get('params', {})

                # Execute the service
                data = self._execute_service(service, params)

                # Organize results by symbol or category
                self._organize_result(results, service, params, data)

            except Exception as e:
                error_msg = f"Error calling {api_call.get('service')}: {str(e)}"
                self.logger.error(error_msg)
                errors.append(error_msg)

        if errors:
            results['errors'] = errors

        return results

    def _execute_service(self, service: str, params: Dict) -> Optional[Dict]:
        """
        Execute specific service call
        """
        # VNStock services
        if hasattr(self.vnstock_client, service):
            method = getattr(self.vnstock_client, service)
            return method(**params)

        # IQX News services
        elif service == 'get_stock_news':
            symbol = params.get('symbol')
            limit = params.get('limit', 10)
            return self.iqx_news_client.get_latest_news(symbol, limit=limit)

        else:
            self.logger.warning(f"Unknown service: {service}")
            return None

    def _organize_result(self, results: Dict, service: str, params: Dict, data: Optional[Dict]):
        """
        Organize results by symbol or category
        """
        if data is None:
            return

        # Symbol-specific services
        symbol = params.get('symbol')
        if symbol:
            if symbol not in results:
                results[symbol] = {}

            # Map service name to data key
            service_key_map = {
                'get_current_price': 'current_price',
                'get_stock_price_history': 'price_history',
                'get_company_info': 'company_info',
                'get_financial_reports': 'financial_reports',
                'get_stock_news': 'news',
                'get_order_stats': 'order_stats',
                'get_foreign_trade': 'foreign_trade',
                'get_prop_trade': 'prop_trade',
                'get_insider_deal': 'insider_deals',
                'get_fund_nav': 'fund_nav',
                'get_fund_top_holding': 'fund_holdings',
                'get_fund_industry_holding': 'fund_industry',
                'get_fund_asset_holding': 'fund_assets'
            }

            key = service_key_map.get(service, service)
            results[symbol][key] = data

        # Market-level services (no specific symbol)
        else:
            market_services = [
                'get_all_symbols', 'get_top_gainers', 'get_top_losers',
                'get_top_by_value', 'get_top_by_volume', 'get_top_foreign_buy',
                'get_top_foreign_sell', 'get_market_pe', 'get_market_pb',
                'get_market_evaluation', 'get_fund_listing'
            ]

            commodity_services = [
                'get_gold_vn', 'get_gold_global', 'get_oil_crude', 'get_commodity_price'
            ]

            macro_services = [
                'get_gdp', 'get_cpi', 'get_industry_production',
                'get_retail', 'get_import_export'
            ]

            # Categorize results
            if service in market_services:
                if 'market_data' not in results:
                    results['market_data'] = {}
                results['market_data'][service] = data

            elif service in commodity_services:
                if 'commodity_data' not in results:
                    results['commodity_data'] = {}
                results['commodity_data'][service] = data

            elif service in macro_services:
                if 'macro_data' not in results:
                    results['macro_data'] = {}
                results['macro_data'][service] = data

            elif service == 'get_price_board':
                # Price board returns data for multiple symbols
                if 'price_board' not in results:
                    results['price_board'] = data

            else:
                # Store in misc category
                if 'misc_data' not in results:
                    results['misc_data'] = {}
                results['misc_data'][service] = data