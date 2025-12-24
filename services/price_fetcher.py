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
        """Fetch Japanese mutual fund NAV using Investment Trusts Association of Japan website"""
        import re
        import io
        import csv
        
        try:
            # Validate ISIN code format (JP followed by 10 alphanumeric characters)
            if not re.match(r'^JP[0-9A-Z]{10}$', code):
                return {
                    'name': f'投資信託 {code}',
                    'price': '—',
                    'currency': '—',
                    'error': 'ISINコード形式が正しくありません（JP + 10桁の英数字）'
                }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
            }
            
            # Step 1: Get fund detail page to extract associFundCd and fund name
            page_url = f"https://toushin-lib.fwg.ne.jp/FdsWeb/FDST030000?isinCd={code}"
            logger.info(f"Fetching mutual fund page for {code} from toushin-lib.fwg.ne.jp")
            
            page_response = requests.get(page_url, timeout=15, headers=headers)
            
            if page_response.status_code != 200:
                logger.warning(f"HTTP {page_response.status_code} for {page_url}")
                return {
                    'name': f'投資信託 {code}',
                    'price': '—',
                    'currency': '—',
                    'error': f'投信協会サイトへのアクセスに失敗しました（HTTP {page_response.status_code}）'
                }
            
            soup = BeautifulSoup(page_response.content, 'html.parser')
            
            # Extract fund name from title
            fund_name = f'投資信託 {code}'
            title_elem = soup.find('title')
            if title_elem:
                title_text = title_elem.get_text().strip()
                if '｜' in title_text:
                    fund_name = title_text.split('｜')[0].strip()
                elif '|' in title_text:
                    fund_name = title_text.split('|')[0].strip()
                elif title_text and title_text != '投信総合検索ライブラリー':
                    fund_name = title_text
            
            if not fund_name or fund_name == '投信総合検索ライブラリー':
                fund_name = f'投資信託 {code}'
            
            logger.info(f"Fund name for {code}: {fund_name}")
            
            # Extract associFundCd from CSV download link
            assoc_fund_cd = None
            csv_link = soup.find('a', href=re.compile(r'csv-file-download'))
            if csv_link:
                href = csv_link.get('href', '')
                # Handle HTML-escaped ampersands
                href = href.replace('&amp;', '&')
                match = re.search(r'associFundCd=([^&]+)', href)
                if match:
                    assoc_fund_cd = match.group(1)
            
            # Try to find associFundCd in page content if not found in link
            if not assoc_fund_cd:
                page_text = str(page_response.content)
                match = re.search(r'associFundCd[=:]([A-Z0-9]{8,})', page_text, re.I)
                if match:
                    assoc_fund_cd = match.group(1)
            
            if not assoc_fund_cd:
                logger.warning(f"Could not find associFundCd for {code}")
                # Fallback: try to get latest NAV from the page
                return self._fetch_latest_nav_from_page(soup, code, fund_name, target_date)
            
            # Step 2: Download CSV with historical data
            csv_url = f"https://toushin-lib.fwg.ne.jp/FdsWeb/FDST030000/csv-file-download?isinCd={code}&associFundCd={assoc_fund_cd}"
            logger.info(f"Downloading CSV for {code} with associFundCd={assoc_fund_cd}")
            
            csv_response = requests.get(csv_url, timeout=30, headers=headers)
            
            if csv_response.status_code != 200:
                logger.warning(f"CSV download failed with HTTP {csv_response.status_code}")
                return self._fetch_latest_nav_from_page(soup, code, fund_name, target_date)
            
            # Step 3: Parse CSV to find NAV for target date
            try:
                # CSV is typically in Shift-JIS encoding
                csv_content = csv_response.content.decode('shift_jis', errors='replace')
                all_rows = list(csv.reader(io.StringIO(csv_content)))
                
                if not all_rows:
                    logger.warning(f"Empty CSV for {code}")
                    return self._fetch_latest_nav_from_page(soup, code, fund_name, target_date)
                
                # Find header row and determine column indices
                header_idx = -1
                date_col = 0
                nav_col = 1
                
                for i, row in enumerate(all_rows):
                    if len(row) >= 2:
                        # Look for header row containing date-related text
                        row_text = ''.join(row)
                        if '年月日' in row_text or '日付' in row_text or '基準価額' in row_text:
                            header_idx = i
                            # Map column indices by header names
                            for j, cell in enumerate(row):
                                if '年月日' in cell or '日付' in cell:
                                    date_col = j
                                elif '基準価額' in cell:
                                    nav_col = j
                            break
                
                # Search all rows for target date (starting after header if found)
                # Support multiple date formats: YYYY/MM/DD, YYYY年MM月DD日
                target_date_str1 = target_date.strftime('%Y/%m/%d')
                target_date_str2 = target_date.strftime('%Y年%m月%d日')
                start_idx = header_idx + 1 if header_idx >= 0 else 0
                
                for row in all_rows[start_idx:]:
                    if len(row) > max(date_col, nav_col):
                        date_cell = row[date_col].strip()
                        # Check if this row has a matching date (support both formats)
                        if date_cell == target_date_str1 or date_cell == target_date_str2:
                            price_text = row[nav_col].replace(',', '').strip()
                            if price_text.isdigit():
                                price = int(price_text)
                                logger.info(f"Found NAV for {code} on {date_cell}: {price}")
                                return {
                                    'name': fund_name,
                                    'price': str(price),
                                    'currency': 'JPY'
                                }
                
                # Date not found in CSV - it might be a non-trading day
                return {
                    'name': fund_name,
                    'price': '—',
                    'currency': '—',
                    'error': f'指定日（{target_date.strftime("%Y/%m/%d")}）のデータが見つかりません（休業日の可能性）'
                }
                
            except Exception as e:
                logger.warning(f"CSV parsing failed: {e}")
                return self._fetch_latest_nav_from_page(soup, code, fund_name, target_date)
        
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching mutual fund {code}")
            return {
                'name': f'投資信託 {code}',
                'price': '—',
                'currency': '—',
                'error': '接続がタイムアウトしました'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching mutual fund {code}: {str(e)}")
            return {
                'name': f'投資信託 {code}',
                'price': '—',
                'currency': '—',
                'error': f'ネットワークエラー: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Error fetching Japanese mutual fund {code}: {str(e)}")
            raise
    
    def _fetch_latest_nav_from_page(self, soup, code, fund_name, target_date):
        """Fallback method to fetch latest NAV from the page (without date filtering)"""
        import re
        
        text_content = soup.get_text()
        
        # Pattern 1: Look for 基準価額 followed by numbers
        nav_patterns = re.findall(r'基準価額[：:\s]*([0-9,]+)', text_content)
        
        # Pattern 2: Look for numeric values in yen format near 基準価額
        if not nav_patterns:
            nav_patterns = re.findall(r'基準価額.*?([0-9,]+)\s*円', text_content, re.DOTALL)
        
        if nav_patterns:
            try:
                price_text = nav_patterns[0].replace(',', '').strip()
                if price_text and price_text.isdigit():
                    price = int(price_text)
                    if 100 < price < 1000000:
                        logger.info(f"Fetched latest NAV for {code}: {price} (date may not match)")
                        return {
                            'name': fund_name,
                            'price': str(price),
                            'currency': 'JPY',
                            'error': '最新の基準価額です（指定日のデータではない可能性があります）'
                        }
            except (ValueError, IndexError, AttributeError) as e:
                logger.warning(f"Failed to parse NAV value: {e}")
        
        return {
            'name': fund_name,
            'price': '—',
            'currency': '—',
            'error': '基準価額の取得に失敗しました'
        }
