from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import requests
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

# ALL 76 Moroccan stocks - complete list
ALL_STOCKS = [
    "TGC", "TMA", "TQM", "NKL", "LHM", "UMR", "WAA", "ZDJ", "MSA", "RDS",
    "CSR", "CFG", "CMG", "HPS", "S2M", "RIS", "DHO", "DWY", "SNA", "SNP",
    "STR", "INV", "MIC", "DYT", "ADH", "IMO", "ADI", "AFI", "AFM", "AKT",
    "ALM", "ARD", "ATH", "ATL", "ATW", "BAL", "BCP", "CRS", "CIH", "CMT",
    "COL", "CTM", "DIM", "DRI", "EQD", "FBR", "IAM", "INM", "JET", "LES",
    "MOX", "MNG", "MUT", "SID", "SOT", "SRM", "MDP", "VCN", "SMI", "CDM",
    # Additional stocks to reach 76
    "BOA", "BMCI", "AFG", "AGM", "CASH", "CMC", "DLM", "LBM", "MAG", "MED",
    "M2M", "OUK", "PRO", "SAL", "SAM", "SLM", "BND", "SNV", "STK", "TIS",
    "REB", "IBC", "DLT", "MGL"
]

# Stock names mapping
STOCK_INFO = {
    "TGC": "TGCC",
    "TMA": "TotalEnergies Marketing",
    "TQM": "TAQA Morocco",
    "NKL": "Ennakl",
    "LHM": "LafargeHolcim Maroc",
    "UMR": "Unimer",
    "WAA": "Wafa Assurance",
    "ZDJ": "Zellidja",
    "MSA": "Marsa Maroc",
    "RDS": "Residences Dar Saada",
    "CSR": "Cosumar",
    "CFG": "CFG Bank",
    "CMG": "CMGP",
    "HPS": "HPS",
    "S2M": "S2M",
    "RIS": "Risma",
    "DHO": "Delta Holding",
    "DWY": "Disway",
    "SNA": "Stokvis Nord Afrique",
    "SNP": "SNEP",
    "STR": "Stroc Industrie",
    "INV": "Involys",
    "MIC": "Microdata",
    "DYT": "Disty Technologies",
    "ADH": "Douja Prom Addoha",
    "IMO": "Immorente Invest",
    "ADI": "Alliances",
    "AFI": "Afric Industries",
    "AFM": "AFMA",
    "AKT": "Akdital",
    "ALM": "Aluminium du Maroc",
    "ARD": "Aradei Capital",
    "ATH": "Auto Hall",
    "ATL": "AtlantaSanad",
    "ATW": "Attijariwafa Bank",
    "BAL": "Balima",
    "BCP": "Banque Centrale Populaire",
    "CRS": "Cartier Saada",
    "CIH": "CIH Bank",
    "CMT": "Ciments du Maroc",
    "COL": "Colorado",
    "CTM": "CTM",
    "DIM": "Delattre Levivier",
    "DRI": "Dari Couspate",
    "EQD": "EQDOM",
    "FBR": "Fenie Brossette",
    "IAM": "Maroc Telecom",
    "INM": "Industries du Maroc",
    "JET": "Jet Contractors",
    "LES": "Lesieur Cristal",
    "MOX": "Maghreb Oxygene",
    "MNG": "Managem",
    "MUT": "Mutandis",
    "SID": "Sonasid",
    "SOT": "Sothema",
    "SRM": "SRM",
    "MDP": "Med Paper",
    "VCN": "Vicenne",
    "SMI": "SMI",
    "CDM": "Credit du Maroc",
    "BOA": "Bank of Africa",
    "BMCI": "BMCI",
    "AFG": "Afriquia Gaz",
    "AGM": "AGMA",
    "CASH": "Cash Plus",
    "CMC": "CMC",
    "DLM": "Delattre Levivier Maroc",
    "LBM": "Label Vie",
    "MAG": "Maghrebail",
    "MED": "Med Paper",
    "M2M": "M2M Group",
    "OUK": "Oulmes",
    "PRO": "Promopharm",
    "SAL": "Salafin",
    "SAM": "Samir",
    "SLM": "Sanlam Maroc",
    "BND": "Societe des Boissons du Maroc",
    "SNV": "SNEP",
    "STK": "Stokvis Nord Afrique",
    "TIS": "Miniere Touissit",
    "REB": "Rebab Company",
    "IBC": "IB Maroc.com",
    "DLT": "Diac Salaf",
    "MGL": "Maroc Leasing"
}

# TradingView column indices mapping based on actual TV table structure
# Columns: 0=Symbol, 1=Price, 2=Change%, 3=Change, 4=Rating, 5=Vol, 6=MarketCap, 
# 7=P/E, 8=EPS, 9=Employees, 10=Sector
TV_COLUMNS = {
    'symbol': 0,
    'price': 1,
    'change_percent': 2,
    'change': 3,
    'rating': 4,
    'volume': 5,
    'market_cap': 6,
    'pe_ratio': 7,
    'eps': 8,
    'employees': 9,
    'sector': 10
}

def scrape_tradingview():
    """
    Scrape TradingView Morocco All Stocks with exact column mapping:
    Symbol, Price, Change %, Change, Rating, Volume, Market Cap, 
    P/E Ratio, EPS, Employees, Sector
    """
    print(f"[{datetime.now()}] Scraping TradingView Morocco...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
            'Referer': 'https://www.tradingview.com/'
        }
        
        url = "https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/"
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"Failed to fetch: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find table with data
        table = soup.find('table', {'class': 'table-Ngq2xrcG'})
        if not table:
            table = soup.find('table')
        
        if not table:
            print("No table found in response")
            return None
        
        tv_data = {}
        rows = table.find_all('tr')
        print(f"Found {len(rows)} rows")
        
        for i, row in enumerate(rows[1:], 1):  # Skip header
            try:
                cells = row.find_all('td')
                if len(cells) < 11:
                    continue
                
                # Extract by column index matching TradingView layout
                symbol = cells[TV_COLUMNS['symbol']].text.strip()
                price_text = cells[TV_COLUMNS['price']].text.strip().replace('MAD', '').replace(',', '').replace(' ', '')
                change_pct_text = cells[TV_COLUMNS['change_percent']].text.strip().replace('%', '').replace('(', '-').replace(')', '').replace('+', '')
                change_text = cells[TV_COLUMNS['change']].text.strip().replace('MAD', '').replace(',', '').replace(' ', '')
                rating = cells[TV_COLUMNS['rating']].text.strip()
                volume = cells[TV_COLUMNS['volume']].text.strip()
                market_cap = cells[TV_COLUMNS['market_cap']].text.strip()
                pe_text = cells[TV_COLUMNS['pe_ratio']].text.strip().replace(',', '')
                eps_text = cells[TV_COLUMNS['eps']].text.strip().replace(',', '')
                employees = cells[TV_COLUMNS['employees']].text.strip()
                sector = cells[TV_COLUMNS['sector']].text.strip()
                
                # Parse numeric values
                try:
                    price = float(price_text) if price_text else 0.0
                except ValueError:
                    price = 0.0
                
                try:
                    change_pct = float(change_pct_text) if change_pct_text else 0.0
                except ValueError:
                    change_pct = 0.0
                
                try:
                    change = float(change_text) if change_text else 0.0
                except ValueError:
                    change = 0.0
                
                try:
                    pe = float(pe_text) if pe_text and pe_text not in ['—', '-', '', 'N/A'] else None
                except ValueError:
                    pe = None
                
                try:
                    eps = float(eps_text) if eps_text and eps_text not in ['—', '-', '', 'N/A'] else None
                except ValueError:
                    eps = None
                
                if symbol:
                    tv_data[symbol] = {
                        'symbol': symbol,
                        'price': price,
                        'change_percent': change_pct,
                        'change': change,
                        'rating': rating if rating else '—',
                        'volume': volume if volume else '—',
                        'market_cap': market_cap if market_cap else '—',
                        'pe_ratio': pe,
                        'eps': eps,
                        'employees': employees if employees else '—',
                        'sector': sector if sector else 'N/A',
                        'has_data': price > 0
                    }
                    
                    if i <= 5 or price > 0:
                        print(f"  {symbol}: Price={price}, Change={change_pct}%, Sector={sector}, Rating={rating}")
                    
            except Exception as e:
                if i < 10:
                    print(f"  Error processing row {i}: {e}")
                continue
        
        print(f"\nTotal scraped: {len(tv_data)} stocks")
        
        # Build complete list with all symbols
        result = []
        for symbol in ALL_STOCKS:
            if symbol in tv_data:
                data = tv_data[symbol]
                result.append({
                    'symbol': symbol,
                    'name': STOCK_INFO.get(symbol, symbol),
                    'price': data['price'],
                    'change_percent': data['change_percent'],
                    'change': data['change'],
                    'rating': data['rating'],
                    'volume': data['volume'],
                    'market_cap': data['market_cap'],
                    'pe_ratio': data['pe_ratio'],
                    'eps': data['eps'],
                    'employees': data['employees'],
                    'sector': data['sector'],
                    'has_live_data': data['has_data']
                })
            else:
                # Not found in TV - add with empty values
                result.append({
                    'symbol': symbol,
                    'name': STOCK_INFO.get(symbol, symbol),
                    'price': 0.0,
                    'change_percent': 0.0,
                    'change': 0.0,
                    'rating': '—',
                    'volume': '—',
                    'market_cap': '—',
                    'pe_ratio': None,
                    'eps': None,
                    'employees': '—',
                    'sector': 'N/A',
                    'has_live_data': False
                })
        
        # Sort: live data first, then alphabetically
        result.sort(key=lambda x: (not x['has_live_data'], x['symbol']))
        
        # Save to file
        with open(STOCKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        live_count = sum(1 for r in result if r['has_live_data'])
        print(f"Saved {len(result)} stocks ({live_count} with live data)")
        
        return result
        
    except Exception as e:
        print(f"Scraping error: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_stocks():
    """Get stocks - try live scrape first, fallback to file"""
    live = scrape_tradingview()
    if live:
        return live
    
    # Fallback to cached file
    try:
        if os.path.exists(STOCKS_FILE):
            with open(STOCKS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error reading cache: {e}")
    
    # Ultimate fallback - empty structure
    return [{
        'symbol': s,
        'name': STOCK_INFO.get(s, s),
        'price': 0.0,
        'change_percent': 0.0,
        'change': 0.0,
        'rating': '—',
        'volume': '—',
        'market_cap': '—',
        'pe_ratio': None,
        'eps': None,
        'employees': '—',
        'sector': 'N/A',
        'has_live_data': False
    } for s in ALL_STOCKS]

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/stocks')
def api_stocks():
    return jsonify(get_stocks())

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now(timezone.utc).isoformat()})

if __name__ == '__main__':
    # Initial scrape
    scrape_tradingview()
    
    # Background updater every 5 minutes
    def background_updater():
        while True:
            time.sleep(300)
            scrape_tradingview()
    
    thread = threading.Thread(target=background_updater, daemon=True)
    thread.start()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
