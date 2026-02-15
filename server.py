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

# BASE STOCKS with names and sectors
BASE_STOCKS = [
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
    Scrape stocks using your working method + change percentage
    """
    print(f"[{datetime.now()}] Scraping TradingView...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        url = "https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/"
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"Failed to fetch: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')
        
        if not table:
            print("No table found")
            return None
        
        # Extract from table rows
        tv_data = {}  # symbol -> {price, change}
        
        for row in table.find_all('tr')[1:]:  # Skip header
            try:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    # Symbol (first column, usually in <a> tag)
                    symbol_cell = cells[0].find('a')
                    symbol = symbol_cell.text.strip() if symbol_cell else cells[0].text.strip()
                    
                    # Price (second column)
                    price_text = cells[1].text.strip().replace('MAD', '').replace(',', '').replace(' ', '')
                    
                    # Change % (third column) - remove % and parentheses
                    change_text = cells[2].text.strip().replace('%', '').replace('(', '-').replace(')', '').replace('+', '').replace(' ', '')
                    
                    try:
                        price = float(price_text)
                        change = float(change_text)
                        
                        if price > 0 and symbol:
                            tv_data[symbol] = {
                                'price': price,
                                'change': change
                            }
                            print(f"  ✓ {symbol}: {price} MAD ({change}%)")
                    except ValueError:
                        continue
                        
            except Exception as e:
                continue
        
        print(f"Found {len(tv_data)} stocks in table")
        
        # Build complete list of 54 stocks
        result = []
        for base in BASE_STOCKS:
            symbol = base['symbol']
            
            if symbol in tv_data:
                # Has live data
                result.append({
                    'symbol': symbol,
                    'name': base['name'],
                    'sector': base['sector'],
                    'price': tv_data[symbol]['price'],
                    'change': tv_data[symbol]['change'],
                    'has_live_data': True
                })
            else:
                # No data from TV - still include with 0.0
                result.append({
                    'symbol': symbol,
                    'name': base['name'],
                    'sector': base['sector'],
                    'price': 0.0,
                    'change': 0.0,
                    'has_live_data': False
                })
        
        # Save to file
        with open(STOCKS_FILE, 'w') as f:
            json.dump(result, f)
        
        live_count = sum(1 for s in result if s['price'] > 0)
        print(f"Saved {len(result)} stocks ({live_count} with live data)")
        
        return result
        
    except Exception as e:
        print(f"Scrape error: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_stocks():
    """Get stocks - try live scrape first, fallback to file"""
    # Try live scrape
    live_data = scrape_tradingview()
    if live_data:
        return live_data
    
    # Fallback to file
    try:
        if os.path.exists(STOCKS_FILE):
            with open(STOCKS_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    
    # Fallback to base list with zeros
    return [{
        'symbol': s['symbol'],
        'name': s['name'],
        'sector': s['sector'],
        'price': 0.0,
        'change': 0.0,
        'has_live_data': False
    } for s in BASE_STOCKS]

def get_news():
    try:
        url = "https://medias24.com/categorie/leboursier/actus/feed/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
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
            
            return news
    except:
        pass
    return []

# Auto-scraper thread
def background_scraper():
    while True:
        time.sleep(300)  # 5 minutes
        print("Background scrape...")
        scrape_tradingview()

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/stocks')
def api_stocks():
    stocks = get_stocks()
    return jsonify(stocks)

@app.route('/api/news')
def api_news():
    return jsonify(get_news())

@app.route('/api/all')
def api_all():
    return jsonify({
        'stocks': get_stocks(),
        'news': get_news()
    })

if __name__ == '__main__':
    # Initial scrape
    scrape_tradingview()
    
    # Start background thread
    thread = threading.Thread(target=background_scraper, daemon=True)
    thread.start()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
