#!/usr/bin/env python3
"""
RISK Network Terminal - Backend Server
Scrapes TradingView Morocco, MASI Index, and RSS News
Auto-refreshes every 10 minutes
"""

from flask import Flask, jsonify, send_from_directory, make_response
from flask_cors import CORS
import requests
import xml.etree.ElementTree as ET
import json
import os
import threading
import time
import re
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

app = Flask(__name__)
# FIXED: More permissive CORS for Render deployment
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"]
    }
})

# Data storage
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# Complete Moroccan stocks database
ALL_STOCKS = {
    "TGC": {"name": "TRAVAUX GENERAUX DE CONSTRUCTIONS", "sector": "Construction"},
    "TMA": {"name": "TOTALENERGIES MARKETING", "sector": "Énergie"},
    "TQM": {"name": "TAQA MOROCCO", "sector": "Énergie"},
    "NKL": {"name": "ENNAKL SA", "sector": "Transport"},
    "LHM": {"name": "LAFARGEHOLCIM", "sector": "Construction"},
    "UMR": {"name": "UNIMER", "sector": "Agroalimentaire"},
    "WAA": {"name": "WAFA ASSURANCE", "sector": "Assurance"},
    "ZDJ": {"name": "ZELLIDJA S.A", "sector": "Mines"},
    "MSA": {"name": "SODEP MARSA", "sector": "Transport"},
    "RDS": {"name": "RESIDENCE DAR SAADA", "sector": "Immobilier"},
    "CSR": {"name": "COSUMAR", "sector": "Agroalimentaire"},
    "CFG": {"name": "CFG BANK", "sector": "Banque"},
    "CMG": {"name": "CMGP CAS", "sector": "Agriculture"},
    "HPS": {"name": "HPS", "sector": "Technologie"},
    "S2M": {"name": "S2M", "sector": "Technologie"},
    "RIS": {"name": "RISMA", "sector": "Hôtellerie"},
    "DHO": {"name": "DELTA HOLDING", "sector": "Industrie"},
    "DWY": {"name": "DISWAY", "sector": "Distribution"},
    "SNA": {"name": "STOKVIS NORD AFRIQUE", "sector": "Distribution"},
    "SNP": {"name": "SNEP", "sector": "Industrie"},
    "STR": {"name": "STROC INDUSTRIE", "sector": "Industrie"},
    "INV": {"name": "INVOLYS", "sector": "Technologie"},
    "MIC": {"name": "MICRODATA", "sector": "Technologie"},
    "DYT": {"name": "DISTY TECHNOLOGIES", "sector": "Distribution"},
    "ADH": {"name": "DOUJA PROM ADDOHA", "sector": "Immobilier"},
    "IMO": {"name": "IMMORENT INVEST", "sector": "Immobilier"},
    "ADI": {"name": "ALLIANCES", "sector": "Divers"},
    "AFI": {"name": "AFRIC INDUSTRIES", "sector": "Industrie"},
    "AFM": {"name": "AFMA", "sector": "Finance"},
    "AKT": {"name": "AKDITAL S.A", "sector": "Santé"},
    "ALM": {"name": "ALUMINIUM DU MAROC", "sector": "Matériaux"},
    "ARD": {"name": "ARADEI CAPITAL", "sector": "Immobilier"},
    "ATH": {"name": "AUTO HALL", "sector": "Automobile"},
    "ATL": {"name": "ATLANTASANAD", "sector": "Assurance"},
    "ATW": {"name": "ATTIJARIWAFA BANK", "sector": "Banque"},
    "BAL": {"name": "BALIMA", "sector": "Distribution"},
    "BCP": {"name": "BANQUE CENTRALE POPULAIRE", "sector": "Banque"},
    "CRS": {"name": "CARTIER SAADA", "sector": "Distribution"},
    "CIH": {"name": "CREDIT IMMOBILIER ET HOTELIER", "sector": "Banque"},
    "CMT": {"name": "CIMENTS DU MAROC", "sector": "Matériaux"},
    "COL": {"name": "COLORADO", "sector": "Distribution"},
    "CTM": {"name": "COMPAGNIE DE TRANSPORTS AU MAROC", "sector": "Transport"},
    "DIM": {"name": "DELATTRE LEVIVIER MAROC", "sector": "Industrie"},
    "DRI": {"name": "DARI COUSPATE", "sector": "Agroalimentaire"},
    "EQD": {"name": "EQDOM", "sector": "Immobilier"},
    "FBR": {"name": "FENIE BROSSETTE", "sector": "Distribution"},
    "IAM": {"name": "MAROC TELECOM", "sector": "Télécom"},
    "INM": {"name": "INDUSTRIE DU MAROC", "sector": "Industrie"},
    "JET": {"name": "JET CONTRACTORS", "sector": "Construction"},
    "LES": {"name": "LESIEUR CRISTAL", "sector": "Agroalimentaire"},
    "MOX": {"name": "MAGHREB OXYGENE", "sector": "Industrie"},
    "MNG": {"name": "MANAGEM", "sector": "Mines"},
    "MUT": {"name": "MUTANDIS", "sector": "Agroalimentaire"},
    "SID": {"name": "SONASID", "sector": "Sidérurgie"},
    "SOT": {"name": "SOTHEMA", "sector": "Pharmacie"},
    "SRM": {"name": "REALISATIONS MECANIQUES", "sector": "Industrie"},
    "MDP": {"name": "MED PAPER", "sector": "Industrie"},
    "VCN": {"name": "VICENNE", "sector": "Santé"},
    "SMI": {"name": "SMI", "sector": "Finance"},
    "CDM": {"name": "Crédit du Maroc", "sector": "Banque"},
    "GTM": {"name": "SGTM", "sector": "BTP"},
    "CAP": {"name": "Cash Plus", "sector": "Finance"}
}

# Cached data with defaults
stocks_cache = []
news_cache = []
masi_cache = {
    "symbol": "MASI", 
    "name": "Morocco All Shares Index", 
    "price": 18573.12, 
    "change": 0.0, 
    "change_percent": 0.0, 
    "currency": "MAD", 
    "last_update": datetime.now().isoformat()
}
last_update = None

def get_market_status():
    """Check if Moroccan stock market is open"""
    now = datetime.now(timezone(timedelta(hours=1)))  # Morocco time (UTC+1)
    weekday = now.weekday()
    hour = now.hour
    minute = now.minute
    current_time = hour * 60 + minute
    
    open_time = 9 * 60 + 30
    close_time = 15 * 60 + 40
    
    is_weekday = weekday < 5
    is_open_hours = open_time <= current_time <= close_time
    
    return {
        "is_open": is_weekday and is_open_hours,
        "open_time": "09:30",
        "close_time": "15:40",
        "current_time": now.strftime("%H:%M"),
        "day_of_week": weekday,
        "next_open": get_next_market_open(now)
    }

def get_next_market_open(current_time):
    """Calculate next market open time"""
    weekday = current_time.weekday()
    hour = current_time.hour
    minute = current_time.minute
    current_minutes = hour * 60 + minute
    
    if weekday >= 5:
        days_until_monday = 7 - weekday
        next_open = current_time + timedelta(days=days_until_monday)
        return next_open.replace(hour=9, minute=30, second=0).strftime("%Y-%m-%d %H:%M")
    elif current_minutes > 15 * 60 + 40:
        next_open = current_time + timedelta(days=1)
        if next_open.weekday() >= 5:
            days_until_monday = 7 - next_open.weekday()
            next_open = next_open + timedelta(days=days_until_monday)
        return next_open.replace(hour=9, minute=30, second=0).strftime("%Y-%m-%d %H:%M")
    else:
        return "Today 09:30"

def scrape_masi_index():
    """Scrape MASI index from TradingView using BeautifulSoup"""
    global masi_cache
    print(f"[{datetime.now()}] Scraping MASI index...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9'
        }
        
        url = "https://fr.tradingview.com/symbols/CSEMA-MASI/"
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"Failed to fetch MASI: {response.status_code}")
            return masi_cache
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the last price using the specific class
        price_elem = soup.find('span', class_='last-zoF9r75I') or \
                     soup.find('span', class_=lambda x: x and 'last-' in str(x)) or \
                     soup.find('span', {'data-qa-id': 'symbol-last-value'})
        
        price = None
        if price_elem:
            price_text = price_elem.get_text().strip()
            price_text = price_text.replace('\u202f', '').replace(' ', '').replace('\xa0', '').replace(',', '.')
            try:
                price = float(price_text)
                print(f"Found MASI price: {price}")
            except ValueError:
                print(f"Could not parse price: {price_text}")
        
        # Try alternative selectors if first one failed
        if price is None:
            all_spans = soup.find_all('span')
            for span in all_spans:
                text = span.get_text().strip()
                if re.match(r'^[\d\s\u202f,\.]+$', text):
                    clean_text = text.replace('\u202f', '').replace(' ', '').replace('\xa0', '').replace(',', '.')
                    try:
                        val = float(clean_text)
                        if 8000 < val < 50000:
                            price = val
                            print(f"Found MASI price (alt): {price}")
                            break
                    except:
                        continue
        
        # Look for change percentage
        change_percent = None
        change_elem = soup.find('span', class_=lambda x: x and 'change-' in str(x)) or \
                      soup.find('span', {'data-qa-id': 'symbol-change-percent-value'})
        
        if change_elem:
            change_text = change_elem.get_text().strip().replace('%', '').replace('+', '').replace(',', '.')
            try:
                change_percent = float(change_text)
                print(f"Found MASI change: {change_percent}%")
            except:
                pass
        
        masi_cache = {
            "symbol": "MASI",
            "name": "Morocco All Shares Index",
            "price": price if price else masi_cache["price"],
            "change": change_percent if change_percent else 0.0,
            "change_percent": change_percent if change_percent else 0.0,
            "currency": "MAD",
            "last_update": datetime.now().isoformat()
        }
        
        print(f"MASI updated: {masi_cache['price']} ({masi_cache['change_percent']}%)")
        return masi_cache
        
    except Exception as e:
        print(f"Error scraping MASI: {e}")
        import traceback
        traceback.print_exc()
        return masi_cache

def scrape_tradingview():
    """Scrape all stocks from TradingView Morocco"""
    global stocks_cache, last_update
    print(f"[{datetime.now()}] Scraping TradingView Morocco...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        url = "https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/"
        response = requests.get(url, headers=headers, timeout=45)
        
        if response.status_code != 200:
            print(f"Failed to fetch: {response.status_code}")
            return stocks_cache
        
        soup = BeautifulSoup(response.text, 'html.parser')
        tv_data = {}
        
        tables = soup.find_all('table')
        print(f"Found {len(tables)} tables")
        
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) < 5:
                continue
            
            for row in rows[1:]:
                try:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) < 5:
                        continue
                    
                    symbol = None
                    symbol_cell = cells[0].find('a') or cells[0]
                    symbol = symbol_cell.get_text().strip()
                    
                    if not symbol or symbol not in ALL_STOCKS:
                        continue
                    
                    data = {
                        'symbol': symbol,
                        'price': 0.0,
                        'change': 0.0,
                        'capital': '—',
                        'pe': None,
                        'sector': ALL_STOCKS[symbol]['sector'],
                        'rating': '—'
                    }
                    
                    for j, cell in enumerate(cells):
                        text = cell.get_text().strip()
                        
                        if j == 1:
                            try:
                                price_text = text.replace('MAD', '').replace(',', '').replace(' ', '').replace('\u202f', '').replace('\xa0', '')
                                price = float(price_text)
                                if 0 < price < 10000:
                                    data['price'] = price
                            except:
                                pass
                        
                        if '%' in text:
                            try:
                                change_text = text.replace('%', '').replace('(', '-').replace(')', '').replace('+', '').replace(',', '.')
                                change = float(change_text)
                                if -50 < change < 50:
                                    data['change'] = change
                            except:
                                pass
                        
                        if any(x in text for x in ['B', 'M', 'Md', 'MM', 'milliard', 'million']) and j > 2:
                            data['capital'] = text
                        
                        if j >= 5:
                            try:
                                pe_text = text.replace(',', '.')
                                pe = float(pe_text)
                                if 0 < pe < 200:
                                    data['pe'] = pe
                            except:
                                pass
                        
                        rating_keywords = ['buy', 'sell', 'hold', 'neutral', 'strong', 'achat', 'vente', 'conserver']
                        if any(kw in text.lower() for kw in rating_keywords) and len(text) < 20:
                            data['rating'] = text
                    
                    tv_data[symbol] = data
                    
                except Exception as e:
                    continue
        
        print(f"Scraped {len(tv_data)} stocks from TradingView")
        
        result = []
        for symbol, info in ALL_STOCKS.items():
            if symbol in tv_data:
                data = tv_data[symbol]
                result.append({
                    'symbol': symbol,
                    'name': info['name'],
                    'sector': data['sector'],
                    'capital': data['capital'],
                    'price': data['price'],
                    'change': data['change'],
                    'pe': data['pe'],
                    'rating': data['rating'],
                    'has_live_data': data['price'] > 0
                })
            else:
                result.append({
                    'symbol': symbol,
                    'name': info['name'],
                    'sector': info['sector'],
                    'capital': '—',
                    'price': 0.0,
                    'change': 0.0,
                    'pe': None,
                    'rating': '—',
                    'has_live_data': False
                })
        
        result.sort(key=lambda x: (not x['has_live_data'], x['symbol']))
        
        stocks_cache = result
        last_update = datetime.now().isoformat()
        
        live_count = sum(1 for r in result if r['has_live_data'])
        print(f"Saved {len(result)} stocks ({live_count} with live data)")
        
        return result
        
    except Exception as e:
        print(f"Error scraping TradingView: {e}")
        import traceback
        traceback.print_exc()
        return stocks_cache

def get_news():
    """Fetch news from Medias24 RSS feed"""
    global news_cache
    try:
        url = "https://medias24.com/categorie/leboursier/actus/feed/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            items = root.findall('.//item')
            
            news = []
            now = datetime.now(timezone.utc)
            
            for item in items[:10]:
                try:
                    title = item.find('title').text if item.find('title') else 'Sans titre'
                    link = item.find('link').text if item.find('link') else ''
                    pubDate = item.find('pubDate').text if item.find('pubDate') else ''
                    category = item.find('category').text if item.find('category') else 'INFO'
                    
                    time_mins = 0
                    if pubDate:
                        try:
                            pub_date = datetime.strptime(pubDate, '%a, %d %b %Y %H:%M:%S %z')
                            diff = now - pub_date
                            time_mins = int(diff.total_seconds() / 60)
                        except:
                            pass
                    
                    news.append({
                        'title': title,
                        'link': link,
                        'category': category.upper(),
                        'time': max(0, time_mins)
                    })
                except:
                    continue
            
            news_cache = news
            return news
    except Exception as e:
        print(f"Error fetching news: {e}")
    
    return news_cache if news_cache else []

def background_refresh():
    """Background thread to refresh data every 10 minutes"""
    while True:
        try:
            print(f"[{datetime.now()}] Auto-refresh starting...")
            scrape_tradingview()
            scrape_masi_index()
            get_news()
            print(f"[{datetime.now()}] Auto-refresh completed")
        except Exception as e:
            print(f"Auto-refresh error: {e}")
        
        time.sleep(600)

# FIXED: Add CORS headers to all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Accept')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Cache-Control', 'no-cache, no-store, must-revalidate')
    return response

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/stocks')
def api_stocks():
    return jsonify(stocks_cache if stocks_cache else [])

@app.route('/api/news')
def api_news():
    return jsonify(news_cache if news_cache else [])

@app.route('/api/masi')
def api_masi():
    return jsonify(masi_cache)

@app.route('/api/market-status')
def api_market_status():
    return jsonify(get_market_status())

@app.route('/api/all')
def api_all():
    return jsonify({
        'stocks': stocks_cache if stocks_cache else [],
        'news': news_cache if news_cache else [],
        'masi': masi_cache,
        'market_status': get_market_status(),
        'last_update': last_update
    })

@app.route('/api/refresh', methods=['POST', 'GET', 'OPTIONS'])
def api_refresh():
    """Manual refresh endpoint"""
    if request.method == 'OPTIONS':
        return make_response('', 200)
    
    scrape_tradingview()
    scrape_masi_index()
    get_news()
    return jsonify({
        'success': True,
        'stocks': stocks_cache,
        'masi': masi_cache,
        'news': news_cache,
        'market_status': get_market_status(),
        'last_update': last_update
    })

from flask import request

if __name__ == '__main__':
    print("=" * 60)
    print("RISK Network Terminal - Starting Server")
    print("=" * 60)
    print("Starting initial data scrape...")
    scrape_tradingview()
    scrape_masi_index()
    get_news()
    
    refresh_thread = threading.Thread(target=background_refresh, daemon=True)
    refresh_thread.start()
    print("Auto-refresh started (every 10 minutes)")
    
    port = int(os.environ.get('PORT', 5000))
    print(f"Server starting on port {port}...")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, threaded=True)
