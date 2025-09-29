from models.vnstock_client import VNStockClient
from typing import Dict, List, Optional
import pandas as pd
import logging

class DataService:
    def __init__(self):
        self.vnstock_client = VNStockClient()
        self.logger = logging.getLogger(__name__)

    def get_market_summary(self) -> Dict:
        """
        Get overall market summary with key indices and top stocks
        """
        try:
            # Get data for major stocks
            major_stocks = ['VN30', 'VCB', 'VIC', 'HPG', 'FPT', 'TCB']
            market_data = {}

            for symbol in major_stocks:
                try:
                    current_price = self.vnstock_client.get_current_price(symbol)
                    if 'error' not in current_price:
                        market_data[symbol] = current_price
                except Exception as e:
                    self.logger.warning(f"Could not get data for {symbol}: {e}")

            return {
                'success': True,
                'data': market_data,
                'timestamp': pd.Timestamp.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error getting market summary: {e}")
            return {'success': False, 'error': str(e)}

    def compare_stocks(self, symbols: List[str], metrics: List[str] = None) -> Dict:
        """
        Compare multiple stocks across various metrics
        """
        if not metrics:
            metrics = ['current_price', 'company_overview']

        try:
            comparison_data = {}

            for symbol in symbols:
                stock_data = {}

                # Get current price if requested
                if 'current_price' in metrics:
                    price_data = self.vnstock_client.get_current_price(symbol)
                    if 'error' not in price_data:
                        stock_data['current_price'] = price_data

                # Get company overview if requested
                if 'company_overview' in metrics:
                    company_data = self.vnstock_client.get_company_info(symbol)
                    if 'error' not in company_data and company_data.get('overview'):
                        stock_data['company_overview'] = company_data['overview']

                # Get financial metrics if requested
                if 'financial_metrics' in metrics:
                    financial_data = self.vnstock_client.get_financial_reports(symbol)
                    if 'error' not in financial_data:
                        stock_data['financial_reports'] = financial_data

                comparison_data[symbol] = stock_data

            return {
                'success': True,
                'comparison': comparison_data,
                'metrics_compared': metrics
            }

        except Exception as e:
            self.logger.error(f"Error comparing stocks: {e}")
            return {'success': False, 'error': str(e)}

    def get_sector_analysis(self, sector: str) -> Dict:
        """
        Get analysis for a specific sector (simplified implementation)
        """
        # Define some sector mappings
        sector_stocks = {
            'banking': ['VCB', 'TCB', 'ACB', 'MBB', 'STB'],
            'real_estate': ['VIC', 'VHM', 'VRE', 'NVL', 'KDH'],
            'technology': ['FPT', 'CMG', 'ELC', 'ITD'],
            'steel': ['HPG', 'HSG', 'NKG', 'TLH'],
            'oil_gas': ['PLX', 'PVS', 'GAS', 'PVD']
        }

        stocks = sector_stocks.get(sector.lower(), [])
        if not stocks:
            return {'success': False, 'error': f'Sector {sector} not found'}

        return self.compare_stocks(stocks, ['current_price', 'company_overview'])

    def get_trending_stocks(self, limit: int = 10) -> Dict:
        """
        Get trending stocks (simplified implementation)
        """
        # For now, return data for most commonly traded stocks
        popular_stocks = ['VCB', 'VIC', 'VHM', 'HPG', 'FPT', 'TCB', 'VRE', 'ACB', 'MBB', 'PLX']

        trending_data = {}
        for symbol in popular_stocks[:limit]:
            try:
                price_data = self.vnstock_client.get_current_price(symbol)
                if 'error' not in price_data:
                    trending_data[symbol] = price_data
            except Exception as e:
                self.logger.warning(f"Could not get trending data for {symbol}: {e}")

        return {
            'success': True,
            'trending_stocks': trending_data,
            'note': 'Based on commonly traded stocks'
        }

    def calculate_portfolio_metrics(self, holdings: List[Dict]) -> Dict:
        """
        Calculate portfolio metrics given holdings
        Holdings format: [{'symbol': 'VCB', 'shares': 100, 'avg_price': 95000}, ...]
        """
        try:
            portfolio_data = {}
            total_current_value = 0
            total_invested_value = 0

            for holding in holdings:
                symbol = holding['symbol']
                shares = holding['shares']
                avg_price = holding['avg_price']

                # Get current price
                current_price_data = self.vnstock_client.get_current_price(symbol)
                if 'error' in current_price_data:
                    continue

                current_price = current_price_data.get('close', 0)
                if not current_price:
                    continue

                # Calculate metrics
                invested_value = shares * avg_price
                current_value = shares * current_price
                gain_loss = current_value - invested_value
                gain_loss_percent = (gain_loss / invested_value) * 100 if invested_value > 0 else 0

                portfolio_data[symbol] = {
                    'shares': shares,
                    'avg_price': avg_price,
                    'current_price': current_price,
                    'invested_value': invested_value,
                    'current_value': current_value,
                    'gain_loss': gain_loss,
                    'gain_loss_percent': gain_loss_percent
                }

                total_current_value += current_value
                total_invested_value += invested_value

            # Calculate overall portfolio metrics
            total_gain_loss = total_current_value - total_invested_value
            total_gain_loss_percent = (total_gain_loss / total_invested_value) * 100 if total_invested_value > 0 else 0

            return {
                'success': True,
                'holdings': portfolio_data,
                'portfolio_summary': {
                    'total_invested': total_invested_value,
                    'total_current_value': total_current_value,
                    'total_gain_loss': total_gain_loss,
                    'total_gain_loss_percent': total_gain_loss_percent
                }
            }

        except Exception as e:
            self.logger.error(f"Error calculating portfolio metrics: {e}")
            return {'success': False, 'error': str(e)}

    def get_stock_recommendations(self, criteria: Dict = None) -> Dict:
        """
        Get stock recommendations based on criteria
        """
        # Simplified recommendation based on popular stocks
        recommendations = [
            {
                'symbol': 'VCB',
                'reason': 'Ngân hàng lớn nhất Việt Nam với kết quả kinh doanh ổn định',
                'risk_level': 'Thấp'
            },
            {
                'symbol': 'FPT',
                'reason': 'Công ty công nghệ hàng đầu với triển vọng tăng trưởng tốt',
                'risk_level': 'Trung bình'
            },
            {
                'symbol': 'HPG',
                'reason': 'Doanh nghiệp thép lớn với lợi thế cạnh tranh',
                'risk_level': 'Trung bình'
            }
        ]

        return {
            'success': True,
            'recommendations': recommendations,
            'note': 'Đây là gợi ý chung, không phải lời khuyên đầu tư'
        }