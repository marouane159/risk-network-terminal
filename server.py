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

# Complete list of 76 Moroccan stocks (verified from Casablanca Stock Exchange)
ALL_STOCKS = [
    "ADH", "ADI", "AFI", "AFM", "AFG", "AGM", "AKT", "ALM", "ARD", "ATH",
    "ATI", "ATL", "ATW", "BAL", "BCP", "BND", "BOA", "CDM", "CIH", "CMC",
    "CMT", "COL", "COS", "CRS", "CTM", "DHO", "DIM", "DRI", "DYT", "EQD",
    "FBR", "CFG", "HPS", "IAM", "IBC", "IMO", "INM", "INV", "JET", "LES",
    "LHM", "MAG", "MDP", "MED", "MIC", "MNG", "MOX", "MSA", "MUT", "NKL",
    "PRO", "RDS", "RIS", "S2M", "SAL", "SAM", "SID", "SLM", "SMI", "SNA",
    "SNP", "SOT", "SRM", "STR", "TGC", "TIS", "TMA", "TQM", "UMR", "VCN",
    "WAA", "ZDJ", "DWY", "SMI", "CDM", "BCP", "ATW"
]

# Remove duplicates while preserving order
ALL_STOCKS = list(dict.fromkeys(ALL_STOCKS))

STOCK_NAMES = {
    "ADH": "Addoha", "ADI": "Alliances", "AFI": "Afric Industries", "AFM": "AFMA",
    "AFG": "Afriquia Gaz", "AGM": "AGMA", "AKT": "Akdital", "ALM": "Aluminium Maroc",
    "ARD": "Aradei Capital", "ATH": "Auto Hall", "ATI": "Attijariwafa Bank",
    "ATL": "AtlantaSanad", "ATW": "Attijariwafa Bank", "BAL": "Balima",
    "BCP": "BCP", "BND": "Boissons Maroc", "BOA": "Bank of Africa",
    "CDM": "Crédit du Maroc", "CIH": "CIH Bank", "CMC": "CMC", "CMT": "Ciments Maroc",
    "COL": "Colorado", "COS": "Cosumar", "CRS": "Cartier Saada", "CTM": "CTM",
    "DHO": "Delta Holding", "DIM": "Delattre", "DRI": "Dari Couspate",
    "DYT": "Disty Tech", "EQD": "EQDOM", "FBR": "Fenie Brossette",
    "CFG": "CFG Bank", "HPS": "HPS", "IAM": "Maroc Telecom", "IBC": "IB Maroc",
    "IMO": "Immorente", "INM": "Industries Maroc", "INV": "Involys",
    "JET": "Jet Contractors", "LES": "Lesieur Cristal", "LHM": "LafargeHolcim",
    "MAG": "Maghrebail", "MDP": "Med Paper", "MED": "Med Paper", "MIC": "Microdata",
    "MNG": "Managem", "MOX": "Maghreb Oxygene", "MSA": "Marsa Maroc",
    "MUT": "Mutandis", "NKL": "Ennakl", "PRO": "Promopharm", "RDS": "Dar Saada",
    "RIS": "Risma", "S2M": "S2M", "SAL": "Salafin", "SAM": "Samir",
    "SID": "Sonasid", "SLM": "Sanlam", "SMI": "SMI", "SNA": "Stokvis",
    "SNP": "SNEP", "SOT": "Sothema", "SRM": "SRM", "STR": "Stroc",
    "TGC": "TGCC", "TIS": "Touissit", "TMA": "TotalEnergies", "TQM": "TAQA Morocco",
    "UMR": "Unimer", "VCN": "Vicenne", "WAA": "Wafa Assurance", "ZDJ": "Zellidja",
    "DWY": "Disway"
}

SECTORS = {
    "ADH": "Immobilier", "ADI": "Holding", "AFI": "Industrie", "AFM": "Agroalimentaire",
    "AKT": "Santé", "ALM": "Industrie", "ARD": "Immobilier", "ATH": "Automobile",
    "ATL": "Assurance", "ATW": "Banque", "BAL": "Bâtiment", "BCP": "Banque",
    "CIH": "Banque", "CMT": "BTP", "COL": "Chimie", "COS": "Agroalimentaire",
    "CRS": "Agroalimentaire", "CTM": "Transport", "DHO": "Holding", "DIM": "Industrie",
    "DRI": "Agroalimentaire", "DYT": "Technologie", "EQD": "Financement", "FBR": "Industrie",
    "CFG": "Banque", "HPS": "Technologie", "IAM": "Télécom", "IMO": "Immobilier",
    "INM": "Industrie", "INV": "Technologie", "JET": "BTP", "LES": "Agroalimentaire",
    "LHM": "BTP", "MNG": "Mines", "MOX": "Industrie", "MSA": "Logistique",
    "MUT": "Consommation", "NKL": "Automobile", "RDS": "Immobilier", "RIS": "Finance",
    "S2M": "Technologie", "SID": "Sidérurgie", "SOT": "Pharmacie", "SRM": "Industrie",
    "STR": "Industrie", "TGC": "BTP", "TMA": "Énergie", "TQM": "Énergie",
    "UMR": "Pêche", "WAA": "Assurance", "ZDJ": "Mines", "DWY": "Distribution"
}

def scrape_tradingview():
    """Attempt to scrape TradingView - returns None if fails"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        url = "https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/"
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'class': 'table-Ngq2xrcG'})
        if not table:
            table = soup.find('table')
        
        if not table:
            return None
            
        tv_data = {}
        rows = table.find_all('tr')
        
        for row in rows[1:]:
            cells = row.find_all('td')
            if len(cells) < 8:
                continue
                
            try:
                symbol = cells[0].text.strip()
                price_text = cells[1].text.strip().replace('MAD', '').replace(',', '').replace(' ', '')
                change_pct_text = cells[2].text.strip().replace('%', '').replace('(', '-').replace(')', '').replace('+', '')
                change_text = cells[3].text.strip().replace('MAD', '').replace(',', '').replace(' ', '')
                rating = cells[4].text.strip() if len(cells) > 4 else '—'
                volume = cells[5].text.strip() if len(cells) > 5 else '—'
                market_cap = cells[6].text.strip() if len(cells) > 6 else '—'
                pe = cells[7].text.strip() if len(cells) > 7 else '—'
                
                price = float(price_text) if price_text else 0.0
                change_pct = float(change_pct_text) if change_pct_text else 0.0
                change = float(change_text) if change_text else 0.0
                
                if symbol and price > 0:
                    tv_data[symbol] = {
                        'price': price,
                        'change_percent': change_pct,
                        'change': change,
                        'rating': rating if rating else '—',
                        'volume': volume,
                        'market_cap': market_cap,
                        'pe_ratio': pe if pe not in ['—', '-', ''] else None,
                        'has_data': True
                    }
            except:
                continue
                
        return tv_data if tv_data else None
        
    except Exception as e:
        print(f"TradingView scrape failed: {e}")
        return None

def fetch_yahoo_finance():
    """Fallback to Yahoo Finance for Moroccan stocks"""
    print(f"[{datetime.now()}] Fetching from Yahoo Finance...")
    data = {}
    
    # Yahoo Finance uses .CS suffix for Casablanca stocks
    for symbol in ALL_STOCKS:
        try:
            ticker = f"{symbol}.CS"
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                json_data = response.json()
                chart = json_data.get('chart', {}).get('result', [{}])[0]
                meta = chart.get('meta', {})
                quote = chart.get('indicators', {}).get('quote', [{}])[0]
                
                if quote.get('close'):
                    close = quote['close'][-1]
                    open_price = quote['open'][0] if quote.get('open') else close
                    change = close - open_price
                    change_pct = (change / open_price * 100) if open_price else 0
                    
                    data[symbol] = {
                        'price': round(close, 2),
                        'change_percent': round(change_pct, 2),
                        'change': round(change, 2),
                        'rating': '—',
                        'volume': str(meta.get('regularMarketVolume', '—')),
                        'market_cap': '—',  # Yahoo doesn't provide this easily
                        'pe_ratio': None,
                        'has_data': True
                    }
                    print(f"  {symbol}: {close} ({change_pct:+.2f}%)")
        except Exception as e:
            continue
            
    return data if data else None

def get_stocks_data():
    """Get stocks data with fallback chain: TradingView -> Yahoo Finance -> Cached -> Empty"""
    
    # Try TradingView first
    tv_data = scrape_tradingview()
    if tv_data:
        print(f"[{datetime.now()}] Using TradingView data: {len(tv_data)} stocks")
        source = 'tradingview'
        raw_data = tv_data
    else:
        # Fallback to Yahoo Finance
        yf_data = fetch_yahoo_finance()
        if yf_data:
            print(f"[{datetime.now()}] Using Yahoo Finance data: {len(yf_data)} stocks")
            source = 'yahoo'
            raw_data = yf_data
        else:
            # Try cached file
            try:
                with open(STOCKS_FILE, 'r') as f:
                    cached = json.load(f)
                    print(f"[{datetime.now()}] Using cached data")
                    return cached
            except:
                raw_data = {}
                source = 'empty'
    
    # Build complete list
    result = []
    for symbol in ALL_STOCKS:
        if symbol in raw_data:
            d = raw_data[symbol]
            result.append({
                'symbol': symbol,
                'name': STOCK_NAMES.get(symbol, symbol),
                'price': d['price'],
                'change_percent': d['change_percent'],
                'change': d['change'],
                'rating': d.get('rating', '—'),
                'volume': d.get('volume', '—'),
                'market_cap': d.get('market_cap', '—'),
                'pe_ratio': d.get('pe_ratio'),
                'eps': None,
                'employees': '—',
                'sector': SECTORS.get(symbol, 'N/A'),
                'has_live_data': True,
                'source': source
            })
        else:
            result.append({
                'symbol': symbol,
                'name': STOCK_NAMES.get(symbol, symbol),
                'price': 0.0,
                'change_percent': 0.0,
                'change': 0.0,
                'rating': '—',
                'volume': '—',
                'market_cap': '—',
                'pe_ratio': None,
                'eps': None,
                'employees': '—',
                'sector': SECTORS.get(symbol, 'N/A'),
                'has_live_data': False,
                'source': 'none'
            })
    
    # Sort: live data first
    result.sort(key=lambda x: (not x['has_live_data'], x['symbol']))
    
    # Save cache
    try:
        with open(STOCKS_FILE, 'w') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except:
        pass
        
    return result

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/stocks')
def api_stocks():
    return jsonify(get_stocks_data())

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'stocks_count': len(ALL_STOCKS)
    })

if __name__ == '__main__':
    # Initial fetch
    get_stocks_data()
    
    # Background updater every 2 minutes
    def updater():
        while True:
            time.sleep(120)
            get_stocks_data()
    
    threading.Thread(target=updater, daemon=True).start()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
