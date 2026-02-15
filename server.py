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

# ALL 54 Moroccan stocks - guaranteed complete list
ALL_STOCKS = [
    "TGC", "TMA", "TQM", "NKL", "LHM", "UMR", "WAA", "ZDJ", "MSA", "RDS",
    "CSR", "CFG", "CMG", "HPS", "S2M", "RIS", "DHO", "DWY", "SNA", "SNP",
    "STR", "INV", "MIC", "DYT", "ADH", "IMO", "ADI", "AFI", "AFM", "AKT",
    "ALM", "ARD", "ATH", "ATL", "ATW", "BAL", "BCP", "CRS", "CIH", "CMT",
    "COL", "CTM", "DIM", "DRI", "EQD", "FBR", "IAM", "INM", "JET", "LES",
    "MOX", "MNG", "MUT", "SID", "SOT", "SRM", "MDP", "VCN", "SMI", "CDM"
]

# Base info for names
STOCK_INFO = {
    "TGC": "TRAVAUX GENERAUX DE CONSTRUCTIONS",
    "TMA": "TOTALENERGIES MARKETING",
    "TQM": "TAQA MOROCCO",
    "NKL": "ENNAKL SA",
    "LHM": "LAFARGEHOLCIM",
    "UMR": "UNIMER",
    "WAA": "WAFA ASSURANCE",
    "ZDJ": "ZELLIDJA S.A",
    "MSA": "SODEP MARSA",
    "RDS": "RESIDENCE DAR SAADA",
    "CSR": "COSUMAR",
    "CFG": "CFG BANK",
    "CMG": "CMGP CAS",
    "HPS": "HPS",
    "S2M": "S2M",
    "RIS": "RISMA",
    "DHO": "DELTA HOLDING",
    "DWY": "DISWAY",
    "SNA": "STOKVIS NORD AFRIQUE",
    "SNP": "SNEP",
    "STR": "STROC INDUSTRIE",
    "INV": "INVOLYS",
    "MIC": "MICRODATA",
    "DYT": "DISTY TECHNOLOGIES",
    "ADH": "DOUJA PROM ADDOHA",
    "IMO": "IMMORENT INVEST",
    "ADI": "ALLIANCES",
    "AFI": "AFRIC INDUSTRIES",
    "AFM": "AFMA",
    "AKT": "AKDITAL S.A",
    "ALM": "ALUMINIUM DU MAROC",
    "ARD": "ARADEI CAPITAL",
    "ATH": "AUTO HALL",
    "ATL": "ATLANTASANAD",
    "ATW": "ATTIJARIWAFA BANK",
    "BAL": "BALIMA",
    "BCP": "BANQUE CENTRALE POPULAIRE",
    "CRS": "CARTIER SAADA",
    "CIH": "CREDIT IMMOBILIER ET HOTELIER",
    "CMT": "CIMENTS DU MAROC",
    "COL": "COLORADO",
    "CTM": "COMPAGNIE DE TRANSPORTS AU MAROC",
    "DIM": "DELATTRE LEVIVIER MAROC",
    "DRI": "DARI COUSPATE",
    "EQD": "EQDOM",
    "FBR": "FENIE BROSSETTE",
    "IAM": "MAROC TELECOM",
    "INM": "INDUSTRIE DU MAROC",
    "JET": "JET CONTRACTORS",
    "LES": "LESIEUR CRISTAL",
    "MOX": "MAGHREB OXYGENE",
    "MNG": "MANAGEM",
    "MUT": "MUTANDIS",
    "SID": "SONASID",
    "SOT": "SOTHEMA",
    "SRM": "REALISATIONS MECANIQUES",
    "MDP": "MED PAPER",
    "VCN": "VICENNE",
    "SMI": "Société métallurgique d'imiter",
    "CDM": "Crédit du Maroc"
}

def scrape_tradingview():
    """
    Scrape ALL columns in correct order:
    Col 0: Symbol, Col 11: Sector, Col 4: Capital, 
    Col 1: Price, Col 2: Change%, Col 6: P/E, Col 10: Analyst Rating
    """
    print(f"[{datetime.now()}] Scraping TradingView...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8'
        }
        
        url = "https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/"
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"Failed: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the main table
        table = soup.find('table', {'class': 'table-Ngq2xrcG'})
        if not table:
            table = soup.find('table')
        
        if not table:
            print("No table found")
            return None
        
        tv_data = {}
        rows = table.find_all('tr')
        print(f"Processing {len(rows)} rows...")
        
        for i, row in enumerate(rows[1:], 1):  # Skip header, enumerate for logging
            try:
                cells = row.find_all('td')
                
                # Need at least 12 columns for all data
                if len(cells) < 12:
                    continue
                
                # Extract data by column index
                # Col 0: Symbol
                symbol_cell = cells[0].find('a') or cells[0]
                symbol = symbol_cell.text.strip()
                
                # Col 1: Price (Cours)
                price_text = cells[1].text.strip().replace('MAD', '').replace(',', '').replace(' ', '')
                
                # Col 2: Change % (Var %)
                change_text = cells[2].text.strip().replace('%', '').replace('(', '-').replace(')', '').replace('+', '')
                
                # Col 4: Capital (5th column, index 4)
                capital_text = cells[4].text.strip() if len(cells) > 4 else ''
                
                # Col 6: P/E (7th column, index 6)
                pe_text = cells[6].text.strip().replace(',', '') if len(cells) > 6 else ''
                
                # Col 10: Analyst Rating (11th column, index 10) - "Sentiment de marché"
                rating = cells[10].text.strip() if len(cells) > 10 else ''
                
                # Col 11: Sector (12th column, index 11) - "Secteur"
                sector = cells[11].text.strip() if len(cells) > 11 else ''
                
                # Parse numeric values
                try:
                    price = float(price_text) if price_text else 0.0
                    change = float(change_text) if change_text else 0.0
                    pe = float(pe_text) if pe_text and pe_text not in ['—', '-', ''] else None
                except ValueError:
                    price = 0.0
                    change = 0.0
                    pe = None
                
                if symbol:
                    tv_data[symbol] = {
                        'symbol': symbol,
                        'price': price,
                        'change': change,
                        'capital': capital_text,
                        'pe': pe,
                        'sector': sector,
                        'rating': rating if rating else '—',
                        'has_data': price > 0
                    }
                    if i <= 5 or price > 0:  # Log first 5 and any with price
                        print(f"  Row {i}: {symbol} | Price:{price} | Sector:{sector} | Rating:{rating}")
                    
            except Exception as e:
                if i < 10:  # Only log errors for first few rows
                    print(f"  Error row {i}: {e}")
                continue
        
        print(f"\nTotal scraped from TV: {len(tv_data)} stocks")
        
        # Build complete list of ALL 54 stocks
        result = []
        for symbol in ALL_STOCKS:
            if symbol in tv_data:
                data = tv_data[symbol]
                result.append({
                    'symbol': symbol,
                    'name': STOCK_INFO.get(symbol, symbol),
                    'sector': data['sector'] or 'N/A',
                    'capital': data['capital'] or '—',
                    'price': data['price'],
                    'change': data['change'],
                    'pe': data['pe'],
                    'rating': data['rating'],
                    'has_live_data': data['has_data']
                })
            else:
                # Not in TV table - include with zeros
                result.append({
                    'symbol': symbol,
                    'name': STOCK_INFO.get(symbol, symbol),
                    'sector': 'N/A',
                    'capital': '—',
                    'price': 0.0,
                    'change': 0.0,
                    'pe': None,
                    'rating': '—',
                    'has_live_data': False
                })
        
        # Sort: live data first, then alphabetically
        result.sort(key=lambda x: (not x['has_live_data'], x['symbol']))
        
        # Save
        with open(STOCKS_FILE, 'w') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        live_count = sum(1 for r in result if r['has_live_data'])
        print(f"Saved {len(result)} stocks total ({live_count} with live data)")
        
        return result
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_stocks():
    """Get stocks - scrape live or from file"""
    live = scrape_tradingview()
    if live:
        return live
    
    try:
        if os.path.exists(STOCKS_FILE):
            with open(STOCKS_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    
    # Fallback
    return [{
        'symbol': s,
        'name': STOCK_INFO.get(s, s),
        'sector': 'N/A',
        'capital': '—',
        'price': 0.0,
        'change': 0.0,
        'pe': None,
        'rating': '—',
        'has_live_data': False
    } for s in ALL_STOCKS]

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
            
            return news
    except:
        pass
    return []

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/stocks')
def api_stocks():
    return jsonify(get_stocks())

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
    scrape_tradingview()
    thread = threading.Thread(target=lambda: [time.sleep(300) or scrape_tradingview() for _ in iter(int, 1)], daemon=True)
    thread.start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
