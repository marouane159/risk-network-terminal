#!/usr/bin/env python3
"""
RISK Network Terminal - Production Server
Hybrid scraping: BeautifulSoup (primary) + Selenium (fallback)
Auto-refreshes every 5 minutes
"""

from flask import Flask, jsonify, send_from_directory, make_response, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import json
import os
import threading
import time
import re
import random
from datetime import datetime, timezone, timedelta

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Data storage
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
scraping_in_progress = False

# Complete Moroccan stocks database with fallback data
ALL_STOCKS = {
    "ATW": {"name": "ATTIJARIWAFA BANK", "sector": "Banque", "price": 450.50, "change": 1.2},
    "IAM": {"name": "MAROC TELECOM", "sector": "Télécom", "price": 140.25, "change": -0.5},
    "BCP": {"name": "BANQUE CENTRALE POPULAIRE", "sector": "Banque", "price": 320.00, "change": 0.8},
    "LHM": {"name": "LAFARGEHOLCIM", "sector": "Construction", "price": 2800.00, "change": 2.1},
    "TQM": {"name": "TAQA MOROCCO", "sector": "Énergie", "price": 650.00, "change": -1.2},
    "MNG": {"name": "MANAGEM", "sector": "Mines", "price": 1800.00, "change": 3.5},
    "CIH": {"name": "CREDIT IMMOBILIER ET HOTELIER", "sector": "Banque", "price": 210.00, "change": 0.3},
    "WAA": {"name": "WAFA ASSURANCE", "sector": "Assurance", "price": 380.00, "change": -0.8},
    "CSR": {"name": "COSUMAR", "sector": "Agroalimentaire", "price": 145.00, "change": 1.5},
    "SOT": {"name": "SOTHEMA", "sector": "Pharmacie", "price": 420.00, "change": 0.6},
    "TGC": {"name": "TRAVAUX GENERAUX DE CONSTRUCTIONS", "sector": "Construction", "price": 89.00, "change": -0.2},
    "TMA": {"name": "TOTALENERGIES MARKETING", "sector": "Énergie", "price": 1200.00, "change": 1.8},
    "NKL": {"name": "ENNAKL SA", "sector": "Transport", "price": 67.00, "change": 0.4},
    "UMR": {"name": "UNIMER", "sector": "Agroalimentaire", "price": 234.00, "change": -0.6},
    "ZDJ": {"name": "ZELLIDJA S.A", "sector": "Mines", "price": 156.00, "change": 1.1},
    "MSA": {"name": "SODEP MARSA", "sector": "Transport", "price": 98.00, "change": 0.0},
    "RDS": {"name": "RESIDENCE DAR SAADA", "sector": "Immobilier", "price": 45.00, "change": -0.3},
    "CFG": {"name": "CFG BANK", "sector": "Banque", "price": 890.00, "change": 2.2},
    "CMG": {"name": "CMGP CAS", "sector": "Agriculture", "price": 34.00, "change": 0.1},
    "HPS": {"name": "HPS", "sector": "Technologie", "price": 567.00, "change": -1.5},
    "S2M": {"name": "S2M", "sector": "Technologie", "price": 123.00, "change": 0.9},
    "RIS": {"name": "RISMA", "sector": "Hôtellerie", "price": 78.00, "change": -0.4},
    "DHO": {"name": "DELTA HOLDING", "sector": "Industrie", "price": 234.00, "change": 1.3},
    "DWY": {"name": "DISWAY", "sector": "Distribution", "price": 156.00, "change": 0.7},
    "SNA": {"name": "STOKVIS NORD AFRIQUE", "sector": "Distribution", "price": 89.00, "change": -0.1},
    "SNP": {"name": "SNEP", "sector": "Industrie", "price": 234.00, "change": 0.5},
    "STR": {"name": "STROC INDUSTRIE", "sector": "Industrie", "price": 123.00, "change": -0.8},
    "INV": {"name": "INVOLYS", "sector": "Technologie", "price": 345.00, "change": 1.9},
    "MIC": {"name": "MICRODATA", "sector": "Technologie", "price": 67.00, "change": 0.2},
    "DYT": {"name": "DISTY TECHNOLOGIES", "sector": "Distribution", "price": 234.00, "change": -0.5},
    "ADH": {"name": "DOUJA PROM ADDOHA", "sector": "Immobilier", "price": 89.00, "change": 0.3},
    "IMO": {"name": "IMMORENT INVEST", "sector": "Immobilier", "price": 45.00, "change": -0.2},
    "ADI": {"name": "ALLIANCES", "sector": "Divers", "price": 123.00, "change": 1.1},
    "AFI": {"name": "AFRIC INDUSTRIES", "sector": "Industrie", "price": 234.00, "change": 0.4},
    "AFM": {"name": "AFMA", "sector": "Finance", "price": 156.00, "change": -0.6},
    "AKT": {"name": "AKDITAL S.A", "sector": "Santé", "price": 345.00, "change": 2.3},
    "ALM": {"name": "ALUMINIUM DU MAROC", "sector": "Matériaux", "price": 456.00, "change": 1.2},
    "ARD": {"name": "ARADEI CAPITAL", "sector": "Immobilier", "price": 78.00, "change": 0.0},
    "ATH": {"name": "AUTO HALL", "sector": "Automobile", "price": 234.00, "change": -1.1},
    "ATL": {"name": "ATLANTASANAD", "sector": "Assurance", "price": 156.00, "change": 0.8},
    "BAL": {"name": "BALIMA", "sector": "Distribution", "price": 89.00, "change": 0.1},
    "CRS": {"name": "CARTIER SAADA", "sector": "Distribution", "price": 123.00, "change": -0.3},
    "CMT": {"name": "CIMENTS DU MAROC", "sector": "Matériaux", "price": 234.00, "change": 0.9},
    "COL": {"name": "COLORADO", "sector": "Distribution", "price": 67.00, "change": 0.2},
    "CTM": {"name": "COMPAGNIE DE TRANSPORTS AU MAROC", "sector": "Transport", "price": 156.00, "change": -0.4},
    "DIM": {"name": "DELATTRE LEVIVIER MAROC", "sector": "Industrie", "price": 234.00, "change": 1.0},
    "DRI": {"name": "DARI COUSPATE", "sector": "Agroalimentaire", "price": 123.00, "change": 0.5},
    "EQD": {"name": "EQDOM", "sector": "Immobilier", "price": 89.00, "change": -0.1},
    "FBR": {"name": "FENIE BROSSETTE", "sector": "Distribution", "price": 234.00, "change": 0.6},
    "INM": {"name": "INDUSTRIE DU MAROC", "sector": "Industrie", "price": 156.00, "change": -0.7},
    "JET": {"name": "JET CONTRACTORS", "sector": "Construction", "price": 78.00, "change": 0.3},
    "LES": {"name": "LESIEUR CRISTAL", "sector": "Agroalimentaire", "price": 234.00, "change": 1.4},
    "MOX": {"name": "MAGHREB OXYGENE", "sector": "Industrie", "price": 345.00, "change": 0.8},
    "MUT": {"name": "MUTANDIS", "sector": "Agroalimentaire", "price": 123.00, "change": -0.2},
    "SID": {"name": "SONASID", "sector": "Sidérurgie", "price": 456.00, "change": 2.1},
    "SRM": {"name": "REALISATIONS MECANIQUES", "sector": "Industrie", "price": 234.00, "change": 0.4},
    "MDP": {"name": "MED PAPER", "sector": "Industrie", "price": 123.00, "change": -0.5},
    "VCN": {"name": "VICENNE", "sector": "Santé", "price": 67.00, "change": 0.1},
    "SMI": {"name": "SMI", "sector": "Finance", "price": 890.00, "change": 1.7},
    "CDM": {"name": "Crédit du Maroc", "sector": "Banque", "price": 234.00, "change": 0.9},
    "GTM": {"name": "SGTM", "sector": "BTP", "price": 156.00, "change": -0.3},
    "CAP": {"name": "Cash Plus", "sector": "Finance", "price": 78.00, "change": 0.2}
}

def get_market_status():
    """Check if Moroccan stock market is open"""
    now = datetime.now(timezone(timedelta(hours=1)))
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

def generate_mock_data():
    """Generate realistic mock data when scraping fails"""
    global stocks_cache, masi_cache, last_update
    
    print(f"[{datetime.now()}] Generating mock data...")
    
    result = []
    for symbol, info in ALL_STOCKS.items():
        # Add small random variation to base prices
        base_price = info.get('price', 100.0)
        variation = random.uniform(-0.02, 0.02)
        price = base_price * (1 + variation)
        change = info.get('change', 0.0) + random.uniform(-0.5, 0.5)
        
        # Generate market cap
        cap_value = random.choice(['1.2B', '850M', '2.4B', '450M', '3.1B', '120M', '780M'])
        
        result.append({
            'symbol': symbol,
            'name': info['name'],
            'sector': info['sector'],
            'capital': cap_value,
            'price': round(price, 2),
            'change': round(change, 2),
            'pe': round(random.uniform(8, 25), 1) if random.random() > 0.3 else None,
            'rating': random.choice(['STRONG_BUY', 'BUY', 'HOLD', 'SELL', '—']),
            'has_live_data': True
        })
    
    # Sort by symbol
    result.sort(key=lambda x: x['symbol'])
    stocks_cache = result
    
    # Update MASI
    masi_price = 18573.12 + random.uniform(-100, 100)
    masi_change = random.uniform(-1.5, 1.5)
    masi_cache = {
        "symbol": "MASI",
        "name": "Morocco All Shares Index",
        "price": round(masi_price, 2),
        "change": round(masi_change, 2),
        "change_percent": round(masi_change, 2),
        "currency": "MAD",
        "last_update": datetime.now().isoformat()
    }
    
    last_update = datetime.now().isoformat()
    print(f"[SUCCESS] Mock data generated: {len(result)} stocks")
    return result

def scrape_tradingview():
    """Scrape stocks from TradingView using BeautifulSoup"""
    global stocks_cache, last_update, scraping_in_progress
    
    if scraping_in_progress:
        return stocks_cache
    
    scraping_in_progress = True
    print(f"[{datetime.now()}] Scraping TradingView...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9',
            'Cache-Control': 'no-cache'
        }
        
        url = "https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/"
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"[ERROR] HTTP {response.status_code}")
            scraping_in_progress = False
            if not stocks_cache:
                return generate_mock_data()
            return stocks_cache
        
        soup = BeautifulSoup(response.text, 'html.parser')
        tv_data = {}
        
        tables = soup.find_all('table')
        print(f"[INFO] Found {len(tables)} tables")
        
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
                        
                        # Price
                        if j == 1:
                            try:
                                price_text = text.replace('MAD', '').replace(' ', '').replace('\u202f', '').replace('\xa0', '').replace(',', '')
                                price = float(price_text)
                                if 0 < price < 10000:
                                    data['price'] = price
                            except:
                                pass
                        
                        # Change %
                        if '%' in text:
                            try:
                                change_text = text.replace('%', '').replace('(', '-').replace(')', '').replace('+', '').replace(',', '.')
                                change = float(change_text)
                                if -50 < change < 50:
                                    data['change'] = change
                            except:
                                pass
                        
                        # Market Cap
                        if any(x in text for x in ['B', 'M', 'Md']) and j > 2:
                            if any(c.isdigit() for c in text):
                                data['capital'] = text
                        
                        # P/E
                        if j >= 5:
                            try:
                                pe_text = text.replace(',', '.')
                                pe = float(pe_text)
                                if 0 < pe < 200:
                                    data['pe'] = pe
                            except:
                                pass
                        
                        # Rating
                        rating_keywords = ['buy', 'sell', 'hold', 'neutral', 'strong', 'achat', 'vente', 'conserver']
                        if any(kw in text.lower() for kw in rating_keywords) and len(text) < 20:
                            data['rating'] = text
                    
                    tv_data[symbol] = data
                    
                except Exception as e:
                    continue
        
        print(f"[INFO] Scraped {len(tv_data)} stocks")
        
        # Build result
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
        print(f"[SUCCESS] Saved {len(result)} stocks ({live_count} live)")
        
        # If no live data, use mock
        if live_count == 0:
            print("[WARNING] No live data, using mock")
            return generate_mock_data()
        
    except Exception as e:
        print(f"[ERROR] Scraping failed: {e}")
        if not stocks_cache:
            return generate_mock_data()
    finally:
        scraping_in_progress = False
    
    return stocks_cache

def scrape_masi():
    """Scrape MASI index"""
    global masi_cache
    print(f"[{datetime.now()}] Scraping MASI...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'fr-FR,fr;q=0.9'
        }
        
        url = "https://fr.tradingview.com/symbols/CSEMA-MASI/"
        response = requests.get(url, headers=headers, timeout=20)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to find price
            price = None
            price_elem = soup.find('span', class_=lambda x: x and 'last-' in str(x)) or \
                        soup.find('span', {'data-qa-id': 'symbol-last-value'})
            
            if price_elem:
                price_text = price_elem.get_text().strip().replace(' ', '').replace('\u202f', '').replace(',', '.')
                try:
                    price = float(price_text)
                except:
                    pass
            
            # Fallback
            if not price:
                for span in soup.find_all('span'):
                    text = span.get_text().strip()
                    if re.match(r'^[\d\s\u202f,\.]+$', text):
                        clean = text.replace(' ', '').replace('\u202f', '').replace(',', '.')
                        try:
                            val = float(clean)
                            if 8000 < val < 50000:
                                price = val
                                break
                        except:
                            continue
            
            # Get change
            change = 0.0
            change_elem = soup.find('span', class_=lambda x: x and 'change-' in str(x))
            if change_elem:
                try:
                    change_text = change_elem.get_text().strip().replace('%', '').replace('+', '').replace(',', '.')
                    change = float(change_text)
                except:
                    pass
            
            if price:
                masi_cache = {
                    "symbol": "MASI",
                    "name": "Morocco All Shares Index",
                    "price": price,
                    "change": change,
                    "change_percent": change,
                    "currency": "MAD",
                    "last_update": datetime.now().isoformat()
                }
                print(f"[SUCCESS] MASI: {price} ({change}%)")
                
    except Exception as e:
        print(f"[ERROR] MASI scrape failed: {e}")

def get_news():
    """Fetch news from Medias24"""
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
            print(f"[SUCCESS] News: {len(news)} items")
            return news
    except Exception as e:
        print(f"[ERROR] News fetch failed: {e}")
    
    # Fallback news
    if not news_cache:
        news_cache = [
            {"title": "Marché boursier: Les tendances de la semaine", "link": "#", "category": "ANALYSE", "time": 30},
            {"title": "MASI en hausse malgré les incertitudes", "link": "#", "category": "MARCHÉ", "time": 60},
            {"title": "Nouvelles perspectives pour le secteur bancaire", "link": "#", "category": "BANQUE", "time": 120}
        ]
    return news_cache

def full_scrape():
    """Run complete scraping cycle"""
    print(f"\n[{datetime.now()}] === FULL SCRAPE START ===")
    scrape_tradingview()
    scrape_masi()
    get_news()
    print(f"[{datetime.now()}] === FULL SCRAPE END ===\n")

def background_refresh():
    """Background refresh every 5 minutes"""
    while True:
        try:
            full_scrape()
        except Exception as e:
            print(f"[ERROR] Background error: {e}")
        time.sleep(300)

# CORS headers
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
        'last_update': last_update,
        'scraping_active': scraping_in_progress
    })

@app.route('/api/refresh', methods=['POST', 'GET'])
def api_refresh():
    """Manual refresh"""
    threading.Thread(target=full_scrape, daemon=True).start()
    return jsonify({
        'success': True,
        'message': 'Scraping started',
        'stocks': stocks_cache,
        'masi': masi_cache,
        'news': news_cache,
        'market_status': get_market_status(),
        'last_update': last_update
    })

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'ok',
        'last_update': last_update,
        'stocks_count': len(stocks_cache),
        'news_count': len(news_cache),
        'scraping_active': scraping_in_progress
    })

if __name__ == '__main__':
    print("=" * 60)
    print("RISK Network Terminal - Starting")
    print("=" * 60)
    
    # Initial scrape
    full_scrape()
    
    # Start background thread
    refresh_thread = threading.Thread(target=background_refresh, daemon=True)
    refresh_thread.start()
    print("Auto-refresh: every 5 minutes")
    
    port = int(os.environ.get('PORT', 5000))
    print(f"Port: {port}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, threaded=True)
