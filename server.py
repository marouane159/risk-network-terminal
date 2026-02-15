from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import requests
import xml.etree.ElementTree as ET
import json
import os
import threading
import time
from datetime import datetime, timezone
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

STOCKS_FILE = f"{DATA_DIR}/stocks.json"
NEWS_FILE = f"{DATA_DIR}/news.json"

# Cache for live data
live_stock_data = {}
last_scrape_time = None

# ALL 54 STOCKS - Base structure
ALL_STOCKS = [
    {"symbol": "TGC", "name": "TRAVAUX GENERAUX DE CONSTRUCTIONS", "sector": "Construction"},
    {"symbol": "TMA", "name": "TOTALENERGIES MARKETING", "sector": "Énergie"},
    {"symbol": "TQM", "name": "TAQA MOROCCO", "sector": "Énergie"},
    {"symbol": "NKL", "name": "ENNAKL SA", "sector": "Transport"},
    {"symbol": "LHM", "name": "LAFARGEHOLCIM", "sector": "Construction"},
    {"symbol": "UMR", "name": "UNIMER", "sector": "Agroalimentaire"},
    {"symbol": "WAA", "name": "WAFA ASSURANCE", "sector": "Assurance"},
    {"symbol": "ZDJ", "name": "ZELLIDJA S.A", "sector": "Mines"},
    {"symbol": "MSA", "name": "SODEP MARSA", "sector": "Transport"},
    {"symbol": "RDS", "name": "RESIDENCE DAR SAADA", "sector": "Construction"},
    {"symbol": "CSR", "name": "COSUMAR", "sector": "Industrie"},
    {"symbol": "CFG", "name": "CFG BANK", "sector": "Banque"},
    {"symbol": "CMG", "name": "CMGP CAS", "sector": "Agriculture"},
    {"symbol": "HPS", "name": "HPS", "sector": "Paiment"},
    {"symbol": "S2M", "name": "S2M", "sector": "Paiment"},
    {"symbol": "RIS", "name": "RISMA", "sector": "Hotel Management"},
    {"symbol": "DHO", "name": "DELTA HOLDING", "sector": "Industrie"},
    {"symbol": "DWY", "name": "DISWAY", "sector": "Distribution éléctro"},
    {"symbol": "SNA", "name": "STOKVIS NORD AFRIQUE", "sector": "Distribution service"},
    {"symbol": "SNP", "name": "SNEP", "sector": "Process Industries"},
    {"symbol": "STR", "name": "STROC INDUSTRIE", "sector": "Service Industriel"},
    {"symbol": "INV", "name": "INVOLYS", "sector": "Service de Technologie"},
    {"symbol": "MIC", "name": "MICRODATA", "sector": "Service de Technologie"},
    {"symbol": "DYT", "name": "DISTY TECHNOLOGIES", "sector": "Service de destribution"},
    {"symbol": "ADH", "name": "DOUJA PROM ADDOHA", "sector": "Immobilier"},
    {"symbol": "IMO", "name": "IMMORENT INVEST", "sector": "Immobilier"},
    {"symbol": "ADI", "name": "ALLIANCES", "sector": "Divers"},
    {"symbol": "AFI", "name": "AFRIC INDUSTRIES", "sector": "Industrie"},
    {"symbol": "AFM", "name": "AFMA", "sector": "Finance"},
    {"symbol": "AKT", "name": "AKDITAL S.A", "sector": "Santé"},
    {"symbol": "ALM", "name": "ALUMINIUM DU MAROC", "sector": "Matériaux"},
    {"symbol": "ARD", "name": "ARADEI CAPITAL", "sector": "Immobilier"},
    {"symbol": "ATH", "name": "AUTO HALL", "sector": "Automobile"},
    {"symbol": "ATL", "name": "ATLANTASANAD", "sector": "Distribution"},
    {"symbol": "ATW", "name": "ATTIJARIWAFA BANK", "sector": "Banque"},
    {"symbol": "BAL", "name": "BALIMA", "sector": "Distribution"},
    {"symbol": "BCP", "name": "BANQUE CENTRALE POPULAIRE", "sector": "Banque"},
    {"symbol": "CRS", "name": "CARTIER SAADA", "sector": "Distribution"},
    {"symbol": "CIH", "name": "CREDIT IMMOBILIER ET HOTELIER", "sector": "Banque"},
    {"symbol": "CMT", "name": "CIMENTS DU MAROC", "sector": "Matériaux"},
    {"symbol": "COL", "name": "COLORADO", "sector": "Distribution"},
    {"symbol": "CTM", "name": "COMPAGNIE DE TRANSPORTS AU MAROC", "sector": "Transport"},
    {"symbol": "DIM", "name": "DELATTRE LEVIVIER MAROC", "sector": "Industrie"},
    {"symbol": "DRI", "name": "DARI COUSPATE", "sector": "Agroalimentaire"},
    {"symbol": "EQD", "name": "EQDOM", "sector": "Immobilier"},
    {"symbol": "FBR", "name": "FENIE BROSSETTE", "sector": "Distribution"},
    {"symbol": "IAM", "name": "MAROC TELECOM", "sector": "Télécom"},
    {"symbol": "INM", "name": "INDUSTRIE DU MAROC", "sector": "Industrie"},
    {"symbol": "JET", "name": "JET CONTRACTORS", "sector": "Construction"},
    {"symbol": "LES", "name": "LESIEUR CRISTAL", "sector": "Agroalimentaire"},
    {"symbol": "MOX", "name": "MAGHREB OXYGENE", "sector": "Industrie"},
    {"symbol": "MNG", "name": "MANAGEM", "sector": "Mines"},
    {"symbol": "MUT", "name": "MUTANDIS", "sector": "Agroalimentaire"},
    {"symbol": "SID", "name": "SONASID", "sector": "Agroalimentaire"},
    {"symbol": "SOT", "name": "SOTHEMA", "sector": "Pharma"},
    {"symbol": "SRM", "name": "REALISATIONS MECANIQUES", "sector": "Industrie"},
    {"symbol": "MDP", "name": "MED PAPER", "sector": "Industrie"},
    {"symbol": "VCN", "name": "VICENNE", "sector": "Santé"},
    {"symbol": "SMI", "name": "Société métallurgique d'imiter", "sector": "Finance"},
    {"symbol": "CDM", "name": "Crédit du Maroc", "sector": "Banque"}
]

def scrape_tradingview():
    """
    Scrape TradingView Morocco directly
    Returns dict: {symbol: {price, change}}
    """
    global live_stock_data, last_scrape_time
    
    print(f"[{datetime.now()}] Scraping TradingView...")
    
    try:
        url = "https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        tv_data = {}
        table = soup.find('table')
        
        if table:
            rows = table.find_all('tr')
            print(f"Found {len(rows)} rows in table")
            
            for row in rows[1:]:  # Skip header
                try:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        symbol_elem = cells[0].find('a')
                        symbol = symbol_elem.text.strip() if symbol_elem else cells[0].text.strip()
                        
                        price_text = cells[1].text.strip().replace('MAD', '').replace(',', '').replace(' ', '')
                        change_text = cells[2].text.strip().replace('%', '').replace('(', '-').replace(')', '').replace('+', '')
                        
                        try:
                            price = float(price_text)
                            change = float(change_text)
                            if price > 0:
                                tv_data[symbol] = {'price': price, 'change': change}
                                print(f"  ✓ {symbol}: {price} MAD ({change}%)")
                        except:
                            continue
                except:
                    continue
        
        if tv_data:
            live_stock_data = tv_data
            last_scrape_time = datetime.now()
            print(f"Scraped {len(tv_data)} stocks successfully")
            
            # Also save to file for persistence
            with open(STOCKS_FILE, 'w') as f:
                json.dump(tv_data, f)
            
            return True
        else:
            print("No data scraped")
            return False
            
    except Exception as e:
        print(f"Scrape error: {e}")
        return False

def get_stocks_with_scrape():
    """Return all 54 stocks, scraping if needed"""
    global live_stock_data
    
    # If we have fresh data, use it
    if live_stock_data:
        stocks = []
        for base in ALL_STOCKS:
            symbol = base['symbol']
            if symbol in live_stock_data:
                stocks.append({
                    'symbol': symbol,
                    'name': base['name'],
                    'sector': base['sector'],
                    'price': live_stock_data[symbol]['price'],
                    'change': live_stock_data[symbol]['change'],
                    'has_live_data': True
                })
            else:
                stocks.append({
                    'symbol': symbol,
                    'name': base['name'],
                    'sector': base['sector'],
                    'price': 0.0,
                    'change': 0.0,
                    'has_live_data': False
                })
        
        # Sort: live data first
        stocks.sort(key=lambda x: (not x['has_live_data'], x['symbol']))
        return stocks
    
    # Try to load from file as fallback
    try:
        if os.path.exists(STOCKS_FILE):
            with open(STOCKS_FILE, 'r') as f:
                file_data = json.load(f)
                if file_data:
                    live_stock_data = file_data
                    return get_stocks_with_scrape()
    except:
        pass
    
    # Return base list with zeros if nothing available
    return [{
        'symbol': s['symbol'],
        'name': s['name'],
        'sector': s['sector'],
        'price': 0.0,
        'change': 0.0,
        'has_live_data': False
    } for s in ALL_STOCKS]

def scrape_news():
    """Scrape Medias24 RSS"""
    try:
        url = "https://medias24.com/categorie/leboursier/actus/feed/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return []
        
        root = ET.fromstring(response.content)
        items = root.findall('.//item')
        
        news = []
        now = datetime.now(timezone.utc)
        
        for item in items[:15]:
            try:
                title = item.find('title').text if item.find('title') is not None else 'Sans titre'
                link = item.find('link').text if item.find('link') is not None else ''
                pubDate = item.find('pubDate').text if item.find('pubDate') is not None else ''
                category = item.find('category').text if item.find('category') is not None else 'INFO'
                
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
            json.dump(news, f)
        
        return news
    except:
        return []

def background_scraper():
    """Run scraper in background every 5 minutes"""
    while True:
        time.sleep(300)  # 5 minutes
        print("Background scrape triggered")
        scrape_tradingview()
        scrape_news()

# Routes
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/stocks')
def api_stocks():
    # Trigger scrape if no data yet
    if not live_stock_data:
        scrape_tradingview()
    
    stocks = get_stocks_with_scrape()
    return jsonify(stocks)

@app.route('/api/news')
def api_news():
    news = scrape_news()
    return jsonify(news)

@app.route('/api/all')
def api_all():
    if not live_stock_data:
        scrape_tradingview()
    
    return jsonify({
        'stocks': get_stocks_with_scrape(),
        'news': scrape_news(),
        'last_update': last_scrape_time.isoformat() if last_scrape_time else None
    })

@app.route('/api/scrape', methods=['POST'])
def manual_scrape():
    """Manual trigger for scraping"""
    success = scrape_tradingview()
    return jsonify({
        'success': success,
        'stocks_count': len(live_stock_data) if live_stock_data else 0
    })

if __name__ == '__main__':
    # Initial scrape on startup
    print("=" * 50)
    print("RISK NETWORK GROUP - Starting server")
    print("=" * 50)
    
    # Try to load existing data first
    try:
        if os.path.exists(STOCKS_FILE):
            with open(STOCKS_FILE, 'r') as f:
                live_stock_data = json.load(f)
            print(f"Loaded {len(live_stock_data)} stocks from file")
    except:
        pass
    
    # Start background scraper
    scraper_thread = threading.Thread(target=background_scraper, daemon=True)
    scraper_thread.start()
    
    # Run server
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
