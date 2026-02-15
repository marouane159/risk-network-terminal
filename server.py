from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import requests
import xml.etree.ElementTree as ET
import json
import os
import re
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

# Complete list of all 54 stocks for reference
ALL_SYMBOLS = [
    "TGC", "TMA", "TQM", "NKL", "LHM", "UMR", "WAA", "ZDJ", "MSA", "RDS",
    "CSR", "CFG", "CMG", "HPS", "S2M", "RIS", "DHO", "DWY", "SNA", "SNP",
    "STR", "INV", "MIC", "DYT", "ADH", "IMO", "ADI", "AFI", "AFM", "AKT",
    "ALM", "ARD", "ATH", "ATL", "ATW", "BAL", "BCP", "CRS", "CIH", "CMT",
    "COL", "CTM", "DIM", "DRI", "EQD", "FBR", "IAM", "INM", "JET", "LES",
    "MOX", "MNG", "MUT", "SID", "SOT", "SRM", "MDP", "VCN", "SMI", "CDM"
]

def scrape_tradingview_advanced():
    """
    Advanced scraper that extracts ALL stocks from TradingView
    Tries multiple methods: JSON in page, multiple tables, API simulation
    """
    print(f"[{datetime.now()}] Scraping TradingView (Advanced)...")
    
    all_stocks = {}
    
    try:
        url = "https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.37 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.37',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Pragma': 'no-cache'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        html = response.text
        
        # Method 1: Look for JSON data embedded in the page (TradingView stores data in <script> tags)
        # Pattern 1: Look for "symbol":"XXX","price":YYY
        json_pattern = r'"symbol":"(\w+)","name":"([^"]+)","price":([\d.]+),"change":([-\d.]+)'
        matches = re.findall(json_pattern, html)
        
        if matches:
            print(f"Found {len(matches)} stocks via JSON pattern 1")
            for symbol, name, price, change in matches:
                try:
                    all_stocks[symbol] = {
                        'symbol': symbol,
                        'name': name,
                        'price': float(price),
                        'change': float(change)
                    }
                except:
                    continue
        
        # Method 2: Look for alternative JSON patterns (newer TradingView format)
        # Pattern: {"s":"TGC","c":[price,change],"v":[volume]}
        alt_pattern = r'"s":"(\w+)","c":\[([-\d.]+),([-\d.]+)\]'
        alt_matches = re.findall(alt_pattern, html)
        
        if alt_matches:
            print(f"Found {len(alt_matches)} stocks via JSON pattern 2")
            for symbol, price, change in alt_matches:
                if symbol not in all_stocks:
                    try:
                        all_stocks[symbol] = {
                            'symbol': symbol,
                            'price': float(price),
                            'change': float(change)
                        }
                    except:
                        continue
        
        # Method 3: Parse all tables (there might be multiple: Top Gainers, Top Losers, Most Active)
        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all('table')
        
        print(f"Found {len(tables)} tables on page")
        
        for table_idx, table in enumerate(tables):
            rows = table.find_all('tr')
            print(f"Table {table_idx}: {len(rows)} rows")
            
            for row in rows[1:]:  # Skip header
                try:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        # Try to find symbol
                        symbol_elem = cells[0].find('a') or cells[0]
                        symbol = symbol_elem.text.strip()
                        
                        # Price
                        price_text = cells[1].text.strip().replace('MAD', '').replace(',', '').replace(' ', '')
                        price = float(price_text) if price_text else 0
                        
                        # Change
                        change_text = cells[2].text.strip().replace('%', '').replace('(', '-').replace(')', '').replace('+', '')
                        change = float(change_text) if change_text else 0
                        
                        if symbol and price > 0:
                            all_stocks[symbol] = {
                                'symbol': symbol,
                                'price': price,
                                'change': change
                            }
                except:
                    continue
        
        # Method 4: Look for data in script tags (JSON with ticker info)
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'symbol' in script.string:
                # Try to extract JSON objects
                try:
                    # Look for patterns like: {"symbol":"TGC","price":820.0,...}
                    data_matches = re.findall(r'\{"symbol":"(\w+)","price":([\d.]+),"change":([-\d.]+)\}', script.string)
                    for symbol, price, change in data_matches:
                        if symbol not in all_stocks:
                            all_stocks[symbol] = {
                                'symbol': symbol,
                                'price': float(price),
                                'change': float(change)
                            }
                except:
                    pass
        
        print(f"Total unique stocks collected: {len(all_stocks)}")
        
        # Save to file
        if all_stocks:
            stock_list = list(all_stocks.values())
            with open(STOCKS_FILE, 'w') as f:
                json.dump(stock_list, f)
            print(f"Saved {len(stock_list)} stocks to file")
            return all_stocks
            
    except Exception as e:
        print(f"Scrape error: {e}")
        import traceback
        traceback.print_exc()
    
    return None

def get_complete_stocks():
    """Merge scraped data with complete list, ensuring all 54 are present"""
    # Try to load scraped data
    scraped_data = {}
    try:
        if os.path.exists(STOCKS_FILE):
            with open(STOCKS_FILE, 'r') as f:
                file_data = json.load(f)
                for item in file_data:
                    if isinstance(item, dict) and 'symbol' in item:
                        scraped_data[item['symbol']] = item
    except:
        pass
    
    # If no file data, try scraping immediately
    if not scraped_data:
        scraped_data = scrape_tradingview_advanced() or {}
    
    # Base info for all stocks
    base_info = {
        "TGC": {"name": "TRAVAUX GENERAUX DE CONSTRUCTIONS", "sector": "Construction"},
        "TMA": {"name": "TOTALENERGIES MARKETING", "sector": "Énergie"},
        "TQM": {"name": "TAQA MOROCCO", "sector": "Énergie"},
        "NKL": {"name": "ENNAKL SA", "sector": "Transport"},
        "LHM": {"name": "LAFARGEHOLCIM", "sector": "Construction"},
        "UMR": {"name": "UNIMER", "sector": "Agroalimentaire"},
        "WAA": {"name": "WAFA ASSURANCE", "sector": "Assurance"},
        "ZDJ": {"name": "ZELLIDJA S.A", "sector": "Mines"},
        "MSA": {"name": "SODEP MARSA", "sector": "Transport"},
        "RDS": {"name": "RESIDENCE DAR SAADA", "sector": "Construction"},
        "CSR": {"name": "COSUMAR", "sector": "Industrie"},
        "CFG": {"name": "CFG BANK", "sector": "Banque"},
        "CMG": {"name": "CMGP CAS", "sector": "Agriculture"},
        "HPS": {"name": "HPS", "sector": "Paiment"},
        "S2M": {"name": "S2M", "sector": "Paiment"},
        "RIS": {"name": "RISMA", "sector": "Hotel Management"},
        "DHO": {"name": "DELTA HOLDING", "sector": "Industrie"},
        "DWY": {"name": "DISWAY", "sector": "Distribution éléctro"},
        "SNA": {"name": "STOKVIS NORD AFRIQUE", "sector": "Distribution service"},
        "SNP": {"name": "SNEP", "sector": "Process Industries"},
        "STR": {"name": "STROC INDUSTRIE", "sector": "Service Industriel"},
        "INV": {"name": "INVOLYS", "sector": "Service de Technologie"},
        "MIC": {"name": "MICRODATA", "sector": "Service de Technologie"},
        "DYT": {"name": "DISTY TECHNOLOGIES", "sector": "Service de destribution"},
        "ADH": {"name": "DOUJA PROM ADDOHA", "sector": "Immobilier"},
        "IMO": {"name": "IMMORENT INVEST", "sector": "Immobilier"},
        "ADI": {"name": "ALLIANCES", "sector": "Divers"},
        "AFI": {"name": "AFRIC INDUSTRIES", "sector": "Industrie"},
        "AFM": {"name": "AFMA", "sector": "Finance"},
        "AKT": {"name": "AKDITAL S.A", "sector": "Santé"},
        "ALM": {"name": "ALUMINIUM DU MAROC", "sector": "Matériaux"},
        "ARD": {"name": "ARADEI CAPITAL", "sector": "Immobilier"},
        "ATH": {"name": "AUTO HALL", "sector": "Automobile"},
        "ATL": {"name": "ATLANTASANAD", "sector": "Distribution"},
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
        "SID": {"name": "SONASID", "sector": "Agroalimentaire"},
        "SOT": {"name": "SOTHEMA", "sector": "Pharma"},
        "SRM": {"name": "REALISATIONS MECANIQUES", "sector": "Industrie"},
        "MDP": {"name": "MED PAPER", "sector": "Industrie"},
        "VCN": {"name": "VICENNE", "sector": "Santé"},
        "SMI": {"name": "Société métallurgique d'imiter", "sector": "Finance"},
        "CDM": {"name": "Crédit du Maroc", "sector": "Banque"}
    }
    
    # Build complete list
    result = []
    for symbol in ALL_SYMBOLS:
        info = base_info.get(symbol, {"name": symbol, "sector": "Unknown"})
        
        if symbol in scraped_data:
            data = scraped_data[symbol]
            result.append({
                'symbol': symbol,
                'name': info['name'],
                'sector': info['sector'],
                'price': float(data.get('price', 0)),
                'change': float(data.get('change', 0)),
                'has_live_data': True
            })
        else:
            # No data available - show 0 but include in list
            result.append({
                'symbol': symbol,
                'name': info['name'],
                'sector': info['sector'],
                'price': 0.0,
                'change': 0.0,
                'has_live_data': False
            })
    
    # Sort: live data first, then alphabetically
    result.sort(key=lambda x: (not x['has_live_data'], x['symbol']))
    return result

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

def background_scraper():
    while True:
        time.sleep(300)  # 5 minutes
        print("Background scrape triggered")
        scrape_tradingview_advanced()

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/stocks')
def api_stocks():
    stocks = get_complete_stocks()
    return jsonify(stocks)

@app.route('/api/news')
def api_news():
    return jsonify(get_news())

@app.route('/api/all')
def api_all():
    return jsonify({
        'stocks': get_complete_stocks(),
        'news': get_news(),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/scrape', methods=['POST'])
def manual_scrape():
    data = scrape_tradingview_advanced()
    return jsonify({
        'success': data is not None,
        'count': len(data) if data else 0,
        'message': f"Scraped {len(data) if data else 0} stocks"
    })

if __name__ == '__main__':
    # Initial scrape
    print("Starting server...")
    scrape_tradingview_advanced()
    
    # Background thread
    thread = threading.Thread(target=background_scraper, daemon=True)
    thread.start()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
