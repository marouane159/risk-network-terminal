from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import requests
import xml.etree.ElementTree as ET
import json
import os
import threading
import time
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
import re

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

STOCKS_FILE = f"{DATA_DIR}/stocks.json"
NEWS_FILE = f"{DATA_DIR}/news.json"
MASI_FILE = f"{DATA_DIR}/masi.json"
LAST_UPDATE_FILE = f"{DATA_DIR}/last_update.json"

# Complete list of Moroccan stocks with sectors
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

def get_market_status():
    """Check if Moroccan stock market is open"""
    now = datetime.now(timezone(timedelta(hours=1)))  # Morocco time (UTC+1)
    weekday = now.weekday()
    hour = now.hour
    minute = now.minute
    current_time = hour * 60 + minute
    
    # Market hours: 09:30 - 15:40 (Monday to Friday)
    open_time = 9 * 60 + 30   # 09:30
    close_time = 15 * 60 + 40  # 15:40
    
    is_weekday = weekday < 5  # 0-4 = Monday-Friday
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
    
    if weekday >= 5:  # Weekend
        days_until_monday = 7 - weekday
        next_open = current_time + timedelta(days=days_until_monday)
        return next_open.replace(hour=9, minute=30, second=0).strftime("%Y-%m-%d %H:%M")
    elif current_minutes > 15 * 60 + 40:  # After market close
        next_open = current_time + timedelta(days=1)
        if next_open.weekday() >= 5:
            days_until_monday = 7 - next_open.weekday()
            next_open = next_open + timedelta(days=days_until_monday)
        return next_open.replace(hour=9, minute=30, second=0).strftime("%Y-%m-%d %H:%M")
    else:
        return "Today 09:30"

def scrape_masi_index():
    """Scrape MASI index data from TradingView"""
    print(f"[{datetime.now()}] Scraping MASI index...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        url = "https://fr.tradingview.com/symbols/CSEMA-MASI/"
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"Failed to fetch MASI: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract price
        price_elem = soup.find('span', {'class': re.compile('last-price')}) or \
                     soup.find('span', class_=lambda x: x and 'price' in x.lower())
        
        # Try multiple selectors for price
        price = None
        change = None
        change_percent = None
        
        # Look for price in script data
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'MASI' in script.string:
                # Try to extract from JSON data
                try:
                    match = re.search(r'"last":\s*([\d.]+)', script.string)
                    if match:
                        price = float(match.group(1))
                    match = re.search(r'"change":\s*([\d.-]+)', script.string)
                    if match:
                        change = float(match.group(1))
                    match = re.search(r'"change_percent":\s*([\d.-]+)', script.string)
                    if match:
                        change_percent = float(match.group(1))
                except:
                    pass
        
        # Fallback to HTML parsing
        if price is None:
            # Look for the main price display
            price_spans = soup.find_all('span', class_=lambda x: x and any(c in str(x).lower() for c in ['price', 'value', 'last']))
            for span in price_spans:
                text = span.get_text().strip().replace(',', '.')
                try:
                    val = float(text)
                    if 9000 < val < 15000:  # MASI range
                        price = val
                        break
                except:
                    continue
        
        # Get change from page
        if change is None:
            change_spans = soup.find_all('span', class_=lambda x: x and 'change' in str(x).lower())
            for span in change_spans:
                text = span.get_text().strip().replace(',', '.').replace('%', '').replace('+', '')
                try:
                    val = float(text)
                    if -10 < val < 10:
                        change_percent = val
                        break
                except:
                    continue
        
        masi_data = {
            "symbol": "MASI",
            "name": "Morocco All Shares Index",
            "price": price or 11000.0,
            "change": change or 0.0,
            "change_percent": change_percent or 0.0,
            "currency": "MAD",
            "last_update": datetime.now().isoformat()
        }
        
        with open(MASI_FILE, 'w') as f:
            json.dump(masi_data, f, ensure_ascii=False, indent=2)
        
        print(f"MASI data saved: {masi_data['price']} ({masi_data['change_percent']}%)")
        return masi_data
        
    except Exception as e:
        print(f"Error scraping MASI: {e}")
        import traceback
        traceback.print_exc()
        return None

def scrape_tradingview():
    """
    Scrape ALL stocks from TradingView Morocco with all required columns:
    Symbol, Market Cap, Sector, Price, Change %, P/E, Analyst Rating
    """
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
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the table - TradingView uses dynamic classes
        table = None
        
        # Try multiple selectors
        selectors = [
            'table.table-Ngq2xrcG',
            'table[data-field="change"]',
            'table[class*="table"]',
            'table',
        ]
        
        for selector in selectors:
            if selector == 'table':
                tables = soup.find_all('table')
                for t in tables:
                    if t.find('th') and 'symbol' in str(t).lower() or 'ticker' in str(t).lower():
                        table = t
                        break
            else:
                table = soup.select_one(selector)
            if table:
                break
        
        if not table:
            print("No table found on page")
            # Try to extract from script/json data
            return extract_from_scripts(soup)
        
        tv_data = {}
        rows = table.find_all('tr')
        print(f"Found {len(rows)} rows in table")
        
        for i, row in enumerate(rows[1:], 1):  # Skip header
            try:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 5:
                    continue
                
                # Extract symbol (usually first column)
                symbol = None
                symbol_cell = cells[0].find('a') or cells[0]
                symbol = symbol_cell.get_text().strip()
                
                if not symbol or symbol not in ALL_STOCKS:
                    continue
                
                # Extract all available data
                data = {
                    'symbol': symbol,
                    'price': 0.0,
                    'change': 0.0,
                    'capital': '—',
                    'pe': None,
                    'sector': ALL_STOCKS.get(symbol, {}).get('sector', 'N/A'),
                    'rating': '—'
                }
                
                # Try to extract from each cell
                for j, cell in enumerate(cells):
                    text = cell.get_text().strip()
                    
                    # Price (usually has MAD or is a number around 10-1000)
                    if j == 1 or ('MAD' in text and j < 3):
                        try:
                            price_text = text.replace('MAD', '').replace(',', '').replace(' ', '').replace('€', '').replace('$', '')
                            price = float(price_text)
                            if 0 < price < 10000:
                                data['price'] = price
                        except:
                            pass
                    
                    # Change % (has % sign)
                    if '%' in text:
                        try:
                            change_text = text.replace('%', '').replace('(', '-').replace(')', '').replace('+', '').replace(',', '.')
                            change = float(change_text)
                            if -50 < change < 50:
                                data['change'] = change
                        except:
                            pass
                    
                    # Market Cap (has B, M, K or is a large number)
                    if any(x in text for x in ['B', 'M', 'Md', 'MM']) and j > 2:
                        data['capital'] = text
                    
                    # P/E (usually a small number)
                    if j >= 5:
                        try:
                            pe_text = text.replace(',', '.')
                            pe = float(pe_text)
                            if 0 < pe < 200:
                                data['pe'] = pe
                        except:
                            pass
                    
                    # Rating (text like Buy, Sell, Hold, Strong Buy)
                    rating_keywords = ['buy', 'sell', 'hold', 'neutral', 'strong', 'achat', 'vente', 'conserver']
                    if any(kw in text.lower() for kw in rating_keywords) and len(text) < 20:
                        data['rating'] = text
                
                tv_data[symbol] = data
                
                if i <= 5:
                    print(f"  {symbol}: Price={data['price']}, Change={data['change']}%, Cap={data['capital']}, PE={data['pe']}, Rating={data['rating']}")
                
            except Exception as e:
                if i < 10:
                    print(f"  Error row {i}: {e}")
                continue
        
        print(f"\nTotal scraped: {len(tv_data)} stocks")
        
        # Build complete result
        result = []
        for symbol, info in ALL_STOCKS.items():
            if symbol in tv_data:
                data = tv_data[symbol]
                result.append({
                    'symbol': symbol,
                    'name': info['name'],
                    'sector': data['sector'] or info['sector'],
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
        
        # Sort: live data first, then by symbol
        result.sort(key=lambda x: (not x['has_live_data'], x['symbol']))
        
        # Save to file
        with open(STOCKS_FILE, 'w') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        live_count = sum(1 for r in result if r['has_live_data'])
        print(f"Saved {len(result)} stocks ({live_count} with live data)")
        
        # Save last update time
        with open(LAST_UPDATE_FILE, 'w') as f:
            json.dump({
                'last_update': datetime.now().isoformat(),
                'stocks_count': len(result),
                'live_count': live_count
            }, f)
        
        return result
        
    except Exception as e:
        print(f"Error scraping TradingView: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_from_scripts(soup):
    """Try to extract stock data from embedded scripts"""
    try:
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and ('stocks' in script.string.lower() or 'symbols' in script.string.lower()):
                # Look for JSON data
                try:
                    # Try to find JSON array of stocks
                    match = re.search(r'\[\s*{\s*"symbol"[^\]]+\]', script.string)
                    if match:
                        data = json.loads(match.group(0))
                        print(f"Found {len(data)} stocks in script data")
                        return process_script_data(data)
                except:
                    pass
        return None
    except:
        return None

def process_script_data(data):
    """Process data extracted from scripts"""
    result = []
    for item in data:
        symbol = item.get('symbol', '')
        if symbol in ALL_STOCKS:
            result.append({
                'symbol': symbol,
                'name': ALL_STOCKS[symbol]['name'],
                'sector': item.get('sector', ALL_STOCKS[symbol]['sector']),
                'capital': item.get('market_cap', '—'),
                'price': float(item.get('price', 0)),
                'change': float(item.get('change', 0)),
                'pe': float(item.get('pe', 0)) if item.get('pe') else None,
                'rating': item.get('rating', '—'),
                'has_live_data': float(item.get('price', 0)) > 0
            })
    return result

def get_news():
    """Fetch news from Medias24 RSS feed"""
    try:
        url = "https://medias24.com/categorie/leboursier/actus/feed/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            items = root.findall('.//item')
            
            news = []
            now = datetime.now(timezone.utc)
            
            for item in items[:10]:  # Get 10 latest
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
            
            # Save to file
            with open(NEWS_FILE, 'w') as f:
                json.dump(news, f, ensure_ascii=False, indent=2)
            
            return news
    except Exception as e:
        print(f"Error fetching news: {e}")
    
    # Try to load from file
    try:
        if os.path.exists(NEWS_FILE):
            with open(NEWS_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    
    return []

def get_stocks():
    """Get stocks data - try live first, then cached"""
    live = scrape_tradingview()
    if live:
        return live
    
    try:
        if os.path.exists(STOCKS_FILE):
            with open(STOCKS_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    
    # Fallback to static data
    return [{
        'symbol': s,
        'name': info['name'],
        'sector': info['sector'],
        'capital': '—',
        'price': 0.0,
        'change': 0.0,
        'pe': None,
        'rating': '—',
        'has_live_data': False
    } for s, info in ALL_STOCKS.items()]

def get_masi():
    """Get MASI index data"""
    live = scrape_masi_index()
    if live:
        return live
    
    try:
        if os.path.exists(MASI_FILE):
            with open(MASI_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    
    return {
        "symbol": "MASI",
        "name": "Morocco All Shares Index",
        "price": 11000.0,
        "change": 0.0,
        "change_percent": 0.0,
        "currency": "MAD",
        "last_update": datetime.now().isoformat()
    }

def background_refresh():
    """Background thread to refresh data every 10 minutes"""
    while True:
        try:
            print(f"[{datetime.now()}] Background refresh starting...")
            scrape_tradingview()
            scrape_masi_index()
            get_news()
            print(f"[{datetime.now()}] Background refresh completed")
        except Exception as e:
            print(f"Background refresh error: {e}")
        
        # Sleep for 10 minutes
        time.sleep(600)

# API Routes
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/stocks')
def api_stocks():
    return jsonify(get_stocks())

@app.route('/api/news')
def api_news():
    return jsonify(get_news())

@app.route('/api/masi')
def api_masi():
    return jsonify(get_masi())

@app.route('/api/market-status')
def api_market_status():
    return jsonify(get_market_status())

@app.route('/api/all')
def api_all():
    return jsonify({
        'stocks': get_stocks(),
        'news': get_news(),
        'masi': get_masi(),
        'market_status': get_market_status(),
        'last_update': datetime.now().isoformat()
    })

@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    """Manual refresh endpoint"""
    stocks = scrape_tradingview()
    masi = scrape_masi_index()
    news = get_news()
    return jsonify({
        'success': True,
        'stocks': stocks,
        'masi': masi,
        'news': news,
        'market_status': get_market_status(),
        'last_update': datetime.now().isoformat()
    })

if __name__ == '__main__':
    # Initial scrape
    print("Starting initial data scrape...")
    scrape_tradingview()
    scrape_masi_index()
    get_news()
    
    # Start background refresh thread
    refresh_thread = threading.Thread(target=background_refresh, daemon=True)
    refresh_thread.start()
    
    port = int(os.environ.get('PORT', 5000))
    print(f"Server starting on port {port}...")
    app.run(host='0.0.0.0', port=port, threaded=True)
