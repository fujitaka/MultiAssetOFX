import logging
import re
from datetime import datetime
from flask import render_template, request, jsonify, send_file, flash, redirect, url_for
from app import app
from services.price_fetcher import PriceFetcher
from services.ofx_generator import OFXGenerator
import io
import os

logger = logging.getLogger(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    """Main page with input form and results display"""
    if request.method == 'GET':
        return render_template('index.html')
    
    # Handle POST request - fetch prices
    return fetch_prices()

def fetch_prices():
    """Fetch prices for given securities and date"""
    try:
        # Get form data
        date_str = request.form.get('date', '').strip()
        securities_str = request.form.get('securities', '').strip()
        
        # Validate inputs
        if not date_str or not securities_str:
            flash('日付と銘柄コードの両方を入力してください。', 'error')
            return render_template('index.html')
        
        # Validate date format
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            flash('日付の形式が正しくありません。YYYY-MM-DD形式で入力してください。', 'error')
            return render_template('index.html')
        
        # Parse securities list
        securities = [sec.strip().upper() for sec in securities_str.split(',') if sec.strip()]
        if not securities:
            flash('有効な銘柄コードを入力してください。', 'error')
            return render_template('index.html')
        
        # Classify and fetch prices
        fetcher = PriceFetcher()
        results = []
        
        for security in securities:
            security_type = classify_security(security)
            if security_type == 'INVALID':
                results.append({
                    'input_code': security,
                    'date': date_str,
                    'name': '—',
                    'price': '—',
                    'currency': '—',
                    'error': '無効な銘柄コード形式'
                })
                continue
            
            try:
                price_data = fetcher.fetch_price(security, security_type, target_date)
                results.append({
                    'input_code': security,
                    'date': date_str,
                    'name': price_data.get('name', '—'),
                    'price': price_data.get('price', '—'),
                    'currency': price_data.get('currency', '—'),
                    'error': price_data.get('error', None)
                })
            except Exception as e:
                logger.error(f"Error fetching price for {security}: {str(e)}")
                results.append({
                    'input_code': security,
                    'date': date_str,
                    'name': '—',
                    'price': '—',
                    'currency': '—',
                    'error': f'データ取得エラー: {str(e)}'
                })
        
        return render_template('index.html', results=results, date=date_str, securities=securities, show_results=True)
    
    except Exception as e:
        logger.error(f"Error in fetch_prices: {str(e)}")
        flash(f'エラーが発生しました: {str(e)}', 'error')
        return render_template('index.html')

@app.route('/download_ofx', methods=['POST'])
def download_ofx():
    """Generate and download OFX file"""
    try:
        # Get results data from form
        results_data = request.form.get('results_data')
        date_str = request.form.get('date')
        
        if not results_data or not date_str:
            flash('OFXファイルの生成に必要なデータがありません。', 'error')
            return render_template('index.html')
        
        # Parse results data (in practice, you might want to store this in session)
        # For simplicity, re-fetch the data based on the form inputs
        securities_str = request.form.get('securities', '').strip()
        securities = [sec.strip().upper() for sec in securities_str.split(',') if sec.strip()]
        
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
        
        # Re-fetch data for OFX generation
        fetcher = PriceFetcher()
        valid_results = []
        
        for security in securities:
            security_type = classify_security(security)
            if security_type == 'INVALID':
                continue
            
            try:
                price_data = fetcher.fetch_price(security, security_type, target_date)
                if price_data.get('price') != '—' and not price_data.get('error'):
                    valid_results.append({
                        'code': security,
                        'name': price_data.get('name'),
                        'price': price_data.get('price'),
                        'currency': price_data.get('currency'),
                        'type': security_type
                    })
            except Exception as e:
                logger.error(f"Error re-fetching price for {security}: {str(e)}")
                continue
        
        if not valid_results:
            flash('OFXファイルに含める有効なデータがありません。', 'error')
            return render_template('index.html')
        
        # Generate OFX file
        generator = OFXGenerator()
        ofx_content = generator.generate_ofx(valid_results, target_date)
        
        # Determine filename
        date_formatted = target_date.strftime('%Y%m%d')
        if len(valid_results) == 1:
            filename = f"SecuOFX_{date_formatted}_{valid_results[0]['code']}.ofx"
        else:
            filename = f"SecuOFX_{date_formatted}.ofx"
        
        # Create file-like object
        ofx_file = io.BytesIO(ofx_content.encode('utf-8'))
        ofx_file.seek(0)
        
        return send_file(
            ofx_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/x-ofx'
        )
    
    except Exception as e:
        logger.error(f"Error generating OFX file: {str(e)}")
        flash(f'OFXファイルの生成中にエラーが発生しました: {str(e)}', 'error')
        return render_template('index.html')

def classify_security(code):
    """Classify security type based on code format"""
    # Japanese stocks: ####.T/O/N/F/S
    if re.match(r'^\d{4}\.(T|O|N|F|S)$', code):
        return 'JP_STOCK'
    
    # Japanese mutual funds: 8-digit alphanumeric codes (investment trust association codes)
    if re.match(r'^[0-9A-Z]{8}$', code):
        return 'JP_MUTUALFUND'
    
    # Japanese mutual funds: legacy 6-8 digit numeric codes
    if re.match(r'^\d{6,8}$', code):
        return 'JP_MUTUALFUND'
    
    # US stocks/ETFs: Alphabetic tickers
    if re.match(r'^[A-Z][A-Z0-9\.-]{0,9}$', code):
        return 'US_STOCK'
    
    return 'INVALID'
