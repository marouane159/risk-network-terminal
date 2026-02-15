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

# Complete base info for all 54 stocks (fallback if sector not in TV)
BASE_STOCKS = {
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

def scrape_tradingview():
    """
    Scrape all columns from TradingView:
    Col 0: Symbol, Col 1: Price, Col 2: Change%, 
    Col 6: P/E, Col 10: Sector, Col 11: Analyst Rating
    """
    print(f"[{datetime.now()}] Scraping TradingView...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        url = "https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/"
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"Failed: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')
        
        if not table:
            print("No table found")
            return None
        
        tv_data = {}
        
        for row in table.find_all('tr')[1:]:  # Skip header
            try:
                cells = row.find_all('td')
                if len(cells) >= 12:  # Need at least 12 columns
                    
                    # Column 0: Symbol
                    symbol_cell = cells[0].find('a')
                    symbol = symbol_cell.text.strip() if symbol_cell else cells[0].text.strip()
                    
                    # Column 1: Price
                    price_text = cells[1].text.strip().replace('MAD', '').replace(',', '').replace(' ', '')
                    
                    # Column 2: Change %
                    change_text = cells[2].text.strip().replace('%', '').replace('(', '-').replace(')', '').replace('+', '')
                    
                    # Column 6: P/E (7th column, index 6)
                    pe_text = cells[6].text.strip().replace(',', '') if len(cells) > 6 else ''
                    
                    # Column 10: Sector (11th column, index 10)  
                    sector = cells[10].text.strip() if len(cells) > 10 else ''
                    
                    # Column 11: Analyst Rating (12th column, index 11)
                    rating = cells[11].text.strip() if len(cells) > 11 else ''
                    
                    try:
                        price = float(price_text) if price_text else 0.0
                        change = float(change_text) if change_text else 0.0
                        pe = float(pe_text) if pe_text and pe_text != '—' else None
                        
                        if symbol and price > 0:
                            tv_data[symbol] = {
                                'symbol': symbol,
                                'price': price,
                                'change': change,
                                'pe': pe,
                                'sector_tv': sector,
                                'rating': rating
                            }
                            print(f"  ✓ {symbol}: {price} MAD | P/E:{pe} | {rating}")
                    except ValueError:
                        continue
                        
            except Exception as e:
                continue
        
        print(f"Scraped {len(tv_data)} stocks")
        
        # Build complete 54-stock list with all fields
        result = []
        for symbol, base_info in BASE_STOCKS.items():
            if symbol in tv_data:
                data = tv_data[symbol]
                result.append({
                    'symbol': symbol,
                    'name': base_info['name'],
                    'price': data['price'],
                    'change': data['change'],
                    'pe': data['pe'],
                    'sector': data['sector_tv'] or base_info['sector'],  # Use TV sector if available
                    'rating': data['rating'],
                    'has_live_data': True
                })
            else:
                result.append({
                    'symbol': symbol,
                    'name': base_info['name'],
                    'price': 0.0,
                    'change': 0.0,
                    'pe': None,
                    'sector': base_info['sector'],
                    'rating': '—',
                    'has_live_data': False
                })
        
        # Save
        with open(STOCKS_FILE, 'w') as f:
            json.dump(result, f)
        
        return result
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_stocks():
    """Get stocks with live scrape or fallback"""
    live = scrape_tradingview()
    if live:
        return live
    
    try:
        if os.path.exists(STOCKS_FILE):
            with open(STOCKS_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    
    return [{'symbol': k, 'name': v['name'], 'price': 0.0, 'change': 0.0, 'pe': None, 'sector': v['sector'], 'rating': '—', 'has_live_data': False} 
            for k, v in BASE_STOCKS.items()]

def get_news():
    try:
        url = "https://medias24.com/categorie/leboursier/actus/feed/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
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
    scrape_tradingview()  # Initial scrape
    thread = threading.Thread(target=lambda: [time.sleep(300) or scrape_tradingview() for _ in iter(int, 1)], daemon=True)
    thread.start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
