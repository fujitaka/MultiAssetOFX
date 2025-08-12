import logging
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import trafilatura

logger = logging.getLogger(__name__)

class PriceFetcher:
    """Service class to fetch prices for different security types"""
    
    def __init__(self):
        self.max_retries = 3
        self.retry_delay = 1  # seconds
    
    def fetch_price(self, code, security_type, target_date):
        """Main method to fetch price data based on security type"""
        for attempt in range(self.max_retries):
            try:
                if security_type == 'JP_STOCK':
                    return self._fetch_japanese_stock(code, target_date)
                elif security_type == 'US_STOCK':
                    return self._fetch_us_stock(code, target_date)
                elif security_type == 'JP_MUTUALFUND':
                    return self._fetch_japanese_mutual_fund(code, target_date)
                else:
                    return {
                        'name': '—',
                        'price': '—',
                        'currency': '—',
                        'error': '不明な銘柄タイプ'
                    }
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {code}: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    return {
                        'name': '—',
                        'price': '—',
                        'currency': '—',
                        'error': f'データ取得失敗（{self.max_retries}回試行）'
                    }
    
    def _fetch_japanese_stock(self, code, target_date):
        """Fetch Japanese stock price using yfinance"""
        try:
            ticker = yf.Ticker(code)
            
            # Get historical data for the specific date
            start_date = target_date.strftime('%Y-%m-%d')
            end_date = (target_date.replace(day=target_date.day + 1)).strftime('%Y-%m-%d')
            
            hist = ticker.history(start=start_date, end=end_date)
            
            if hist.empty:
                return {
                    'name': '—',
                    'price': '—',
                    'currency': '—',
                    'error': '指定日のデータが見つかりません（休業日の可能性）'
                }
            
            close_price = hist['Close'].iloc[0]
            
            # Get company name
            info = ticker.info
            name = info.get('longName') or info.get('shortName') or code
            
            return {
                'name': name,
                'price': f"{close_price:.2f}",
                'currency': 'JPY'
            }
        
        except Exception as e:
            logger.error(f"Error fetching Japanese stock {code}: {str(e)}")
            raise
    
    def _fetch_us_stock(self, code, target_date):
        """Fetch US stock price using yfinance"""
        try:
            ticker = yf.Ticker(code)
            
            # Get historical data for the specific date
            start_date = target_date.strftime('%Y-%m-%d')
            end_date = (target_date.replace(day=target_date.day + 1)).strftime('%Y-%m-%d')
            
            hist = ticker.history(start=start_date, end=end_date)
            
            if hist.empty:
                return {
                    'name': '—',
                    'price': '—',
                    'currency': '—',
                    'error': '指定日のデータが見つかりません（休業日の可能性）'
                }
            
            close_price = hist['Close'].iloc[0]
            
            # Get company name
            info = ticker.info
            name = info.get('longName') or info.get('shortName') or code
            
            return {
                'name': name,
                'price': f"{close_price:.2f}",
                'currency': 'USD'
            }
        
        except Exception as e:
            logger.error(f"Error fetching US stock {code}: {str(e)}")
            raise
    
    def _fetch_japanese_mutual_fund(self, code, target_date):
        """Fetch Japanese mutual fund NAV using web scraping"""
        try:
            # Try Morningstar Japan first
            url = f"https://www.morningstar.co.jp/FundData/DetailSnapshot.do?fnc={code}"
            
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for fund name
                name_element = soup.find('h1') or soup.find('title')
                fund_name = name_element.get_text().strip() if name_element else code
                
                # Look for NAV data (this is a simplified approach)
                # In a real implementation, you'd need to parse the specific HTML structure
                nav_elements = soup.find_all(text=lambda text: text and '円' in text and any(c.isdigit() for c in text))
                
                if nav_elements:
                    # Extract price from the first matching element
                    price_text = nav_elements[0].strip()
                    import re
                    price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                    
                    if price_match:
                        price = float(price_match.group().replace(',', ''))
                        return {
                            'name': fund_name,
                            'price': f"{price:.4f}",
                            'currency': 'JPY'
                        }
                
            except Exception as e:
                logger.warning(f"Morningstar failed for {code}: {str(e)}")
            
            # Fallback: Try using trafilatura for text extraction
            try:
                downloaded = trafilatura.fetch_url(url)
                if downloaded:
                    text = trafilatura.extract(downloaded)
                    if text and '円' in text:
                        # Simple pattern matching for NAV
                        import re
                        price_patterns = re.findall(r'[\d,]+\.?\d*\s*円', text)
                        if price_patterns:
                            price_text = price_patterns[0].replace('円', '').replace(',', '').strip()
                            try:
                                price = float(price_text)
                                return {
                                    'name': f'投資信託 {code}',
                                    'price': f"{price:.4f}",
                                    'currency': 'JPY'
                                }
                            except ValueError:
                                pass
            except Exception as e:
                logger.warning(f"Trafilatura failed for {code}: {str(e)}")
            
            # If all methods fail, return mock data structure
            return {
                'name': '—',
                'price': '—',
                'currency': '—',
                'error': '投資信託データの取得に失敗しました'
            }
        
        except Exception as e:
            logger.error(f"Error fetching Japanese mutual fund {code}: {str(e)}")
            raise
