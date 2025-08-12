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
            from datetime import timedelta
            start_date = target_date.strftime('%Y-%m-%d')
            end_date = (target_date + timedelta(days=1)).strftime('%Y-%m-%d')
            
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
            try:
                info = ticker.info
                name = info.get('longName') or info.get('shortName') or code
            except:
                name = code
            
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
            from datetime import timedelta
            start_date = target_date.strftime('%Y-%m-%d')
            end_date = (target_date + timedelta(days=1)).strftime('%Y-%m-%d')
            
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
            try:
                info = ticker.info
                name = info.get('longName') or info.get('shortName') or code
            except:
                name = code
            
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
            # Try multiple sources for mutual fund data
            # First try: Investment Trusts Association of Japan (if 8-digit alphanumeric code)
            if re.match(r'^[0-9A-Z]{8}$', code):
                # Try ISIN-based search or investment trust association code
                urls_to_try = [
                    f"https://www.toushin.or.jp/search/fund/detail/{code}",
                    f"https://www.morningstar.co.jp/FundData/DetailSnapshot.do?isin={code}",
                    f"https://www.morningstar.co.jp/FundData/DetailSnapshot.do?fnc={code}"
                ]
            else:
                # Legacy numeric codes
                urls_to_try = [
                    f"https://www.morningstar.co.jp/FundData/DetailSnapshot.do?fnc={code}"
                ]
            
            for url in urls_to_try:
                try:
                    logger.info(f"Trying URL for mutual fund {code}: {url}")
                    response = requests.get(url, timeout=15, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    })
                    
                    if response.status_code != 200:
                        logger.warning(f"HTTP {response.status_code} for {url}")
                        continue
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Look for fund name
                    name_element = soup.find('h1') or soup.find('title')
                    fund_name = name_element.get_text().strip() if name_element else f'投資信託 {code}'
                    
                    # Look for NAV data - search for price patterns in text
                    import re
                    text_content = soup.get_text()
                    
                    # Look for patterns like "基準価額" followed by numbers
                    nav_patterns = re.findall(r'基準価額[：:\s]*([0-9,]+\.?[0-9]*)', text_content)
                    if not nav_patterns:
                        # Alternative patterns
                        nav_patterns = re.findall(r'([0-9,]+\.?[0-9]*)\s*円', text_content)
                    
                    if nav_patterns:
                        try:
                            # Extract price from the first matching pattern
                            price_text = nav_patterns[0].replace(',', '').strip()
                            if price_text and price_text.replace('.', '').isdigit():
                                price = float(price_text)
                                if price > 0:  # Ensure positive price
                                    return {
                                        'name': fund_name,
                                        'price': f"{price:.4f}",
                                        'currency': 'JPY'
                                    }
                        except (ValueError, IndexError, AttributeError):
                            continue
                    
                except Exception as e:
                    logger.warning(f"Failed to fetch from {url}: {str(e)}")
                    continue
            
            # Fallback: Try using trafilatura for text extraction on successful URLs
            for url in urls_to_try:
                try:
                    downloaded = trafilatura.fetch_url(url)
                    if downloaded:
                        text = trafilatura.extract(downloaded)
                        if text:
                            import re
                            # Look for NAV patterns in extracted text
                            nav_patterns = re.findall(r'基準価額[：:\s]*([0-9,]+\.?[0-9]*)', text)
                            if not nav_patterns:
                                nav_patterns = re.findall(r'([0-9,]+\.?[0-9]*)\s*円', text)
                            
                            if nav_patterns:
                                try:
                                    price_text = nav_patterns[0].replace(',', '').strip()
                                    if price_text and price_text.replace('.', '').isdigit():
                                        price = float(price_text)
                                        if price > 0:  # Ensure positive price
                                            return {
                                                'name': f'投資信託 {code}',
                                                'price': f"{price:.4f}",
                                                'currency': 'JPY'
                                            }
                                except (ValueError, IndexError, AttributeError):
                                    continue
                except Exception as e:
                    logger.warning(f"Trafilatura failed for {url}: {str(e)}")
                    continue
            
            # Return error if all methods fail
            return {
                'name': f'投資信託 {code}',
                'price': '—',
                'currency': '—',
                'error': '投資信託データの取得に失敗しました（スクレイピング制限の可能性があります）'
            }
        
        except Exception as e:
            logger.error(f"Error fetching Japanese mutual fund {code}: {str(e)}")
            raise
