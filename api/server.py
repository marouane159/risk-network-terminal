from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import requests
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime, timezone

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

DATA_DIR = "data"
STOCKS_FILE = f"{DATA_DIR}/stocks.json"
NEWS_FILE = f"{DATA_DIR}/news.json"

# COMPLETE 54 STOCKS - Guaranteed to be served
ALL_STOCKS = [
    {"symbol": "TGC", "name": "TRAVAUX GENERAUX DE CONSTRUCTIONS", "sector": "Construction", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "TMA", "name": "TOTALENERGIES MARKETING", "sector": "Énergie", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "TQM", "name": "TAQA MOROCCO", "sector": "Énergie", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "NKL", "name": "ENNAKL SA", "sector": "Transport", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "LHM", "name": "LAFARGEHOLCIM", "sector": "Construction", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "UMR", "name": "UNIMER", "sector": "Agroalimentaire", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "WAA", "name": "WAFA ASSURANCE", "sector": "Assurance", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "ZDJ", "name": "ZELLIDJA S.A", "sector": "Mines", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "MSA", "name": "SODEP MARSA", "sector": "Transport", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "RDS", "name": "RESIDENCE DAR SAADA", "sector": "Construction", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "CSR", "name": "COSUMAR", "sector": "Industrie", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "CFG", "name": "CFG BANK", "sector": "Banque", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "CMG", "name": "CMGP CAS", "sector": "Agriculture", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "HPS", "name": "HPS", "sector": "Paiment", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "S2M", "name": "S2M", "sector": "Paiment", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "RIS", "name": "RISMA", "sector": "Hotel Management", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "DHO", "name": "DELTA HOLDING", "sector": "Industrie", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "DWY", "name": "DISWAY", "sector": "Distribution éléctro", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "SNA", "name": "STOKVIS NORD AFRIQUE", "sector": "Distribution service", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "SNP", "name": "SNEP", "sector": "Process Industries", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "STR", "name": "STROC INDUSTRIE", "sector": "Service Industriel", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "INV", "name": "INVOLYS", "sector": "Service de Technologie", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "MIC", "name": "MICRODATA", "sector": "Service de Technologie", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "DYT", "name": "DISTY TECHNOLOGIES", "sector": "Service de destribution", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "ADH", "name": "DOUJA PROM ADDOHA", "sector": "Immobilier", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "IMO", "name": "IMMORENT INVEST", "sector": "Immobilier", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "ADI", "name": "ALLIANCES", "sector": "Divers", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "AFI", "name": "AFRIC INDUSTRIES", "sector": "Industrie", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "AFM", "name": "AFMA", "sector": "Finance", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "AKT", "name": "AKDITAL S.A", "sector": "Santé", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "ALM", "name": "ALUMINIUM DU MAROC", "sector": "Matériaux", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "ARD", "name": "ARADEI CAPITAL", "sector": "Immobilier", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "ATH", "name": "AUTO HALL", "sector": "Automobile", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "ATL", "name": "ATLANTASANAD", "sector": "Distribution", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "ATW", "name": "ATTIJARIWAFA BANK", "sector": "Banque", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "BAL", "name": "BALIMA", "sector": "Distribution", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "BCP", "name": "BANQUE CENTRALE POPULAIRE", "sector": "Banque", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "CRS", "name": "CARTIER SAADA", "sector": "Distribution", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "CIH", "name": "CREDIT IMMOBILIER ET HOTELIER", "sector": "Banque", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "CMT", "name": "CIMENTS DU MAROC", "sector": "Matériaux", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "COL", "name": "COLORADO", "sector": "Distribution", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "CTM", "name": "COMPAGNIE DE TRANSPORTS AU MAROC", "sector": "Transport", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "DIM", "name": "DELATTRE LEVIVIER MAROC", "sector": "Industrie", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "DRI", "name": "DARI COUSPATE", "sector": "Agroalimentaire", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "EQD", "name": "EQDOM", "sector": "Immobilier", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "FBR", "name": "FENIE BROSSETTE", "sector": "Distribution", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "IAM", "name": "MAROC TELECOM", "sector": "Télécom", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "INM", "name": "INDUSTRIE DU MAROC", "sector": "Industrie", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "JET", "name": "JET CONTRACTORS", "sector": "Construction", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "LES", "name": "LESIEUR CRISTAL", "sector": "Agroalimentaire", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "MOX", "name": "MAGHREB OXYGENE", "sector": "Industrie", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "MNG", "name": "MANAGEM", "sector": "Mines", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "MUT", "name": "MUTANDIS", "sector": "Agroalimentaire", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "SID", "name": "SONASID", "sector": "Agroalimentaire", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "SOT", "name": "SOTHEMA", "sector": "Pharma", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "SRM", "name": "REALISATIONS MECANIQUES", "sector": "Industrie", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "MDP", "name": "MED PAPER", "sector": "Industrie", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "VCN", "name": "VICENNE", "sector": "Santé", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "SMI", "name": "Société métallurgique d'imiter", "sector": "Finance", "price": 0.0, "change": 0.0, "has_live_data": False},
    {"symbol": "CDM", "name": "Crédit du Maroc", "sector": "Banque", "price": 0.0, "change": 0.0, "has_live_data": False}
]

def get_stocks_data():
    """
    Returns ALL 54 stocks. Merges file data with ALL_STOCKS list.
    File data updates prices for available tickers, others remain at 0.0
    """
    # Create lookup from ALL_STOCKS (the complete list)
    stocks_dict = {s['symbol']: s.copy() for s in ALL_STOCKS}
    
    # Try to load updates from file
    try:
        if os.path.exists(STOCKS_FILE):
            with open(STOCKS_FILE, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
            
            # Update with live data where available
            for stock in file_data:
                symbol = stock.get('symbol')
                if symbol in stocks_dict:
                    stocks_dict[symbol]['price'] = float(stock.get('price', 0))
                    stocks_dict[symbol]['change'] = float(stock.get('change', 0))
                    stocks_dict[symbol]['has_live_data'] = stock.get('has_live_data', False) or (stocks_dict[symbol]['price'] > 0)
    except Exception as e:
        print(f"Error reading stocks file: {e}")
    
    # Convert back to list and sort (live data first)
    result = list(stocks_dict.values())
    result.sort(key=lambda x: (not x['has_live_data'], x['symbol']))
    
    return result

def get_news_data():
    """Fetch or return cached news"""
    # Try live RSS first
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
                        'date': pubDate,
                        'category': category.upper(),
                        'time': max(0, time_mins),
                        'source': 'Medias24.com'
                    })
                except:
                    continue
            
            if news:
                return news
    except:
        pass
    
    # Fallback to file
    try:
        if os.path.exists(NEWS_FILE):
            with open(NEWS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    
    return []

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/stocks')
def get_stocks():
    """Returns ALL 54 stocks, with live prices where available"""
    stocks = get_stocks_data()
    return jsonify(stocks)

@app.route('/api/news')
def get_news():
    news = get_news_data()
    return jsonify(news)

@app.route('/api/all')
def get_all():
    stocks = get_stocks_data()
    news = get_news_data()
    return jsonify({
        'stocks': stocks,
        'news': news,
        'updated': datetime.now().isoformat(),
        'total_stocks': len(stocks),
        'live_stocks': sum(1 for s in stocks if s['price'] > 0)
    })

@app.route('/api/status')
def status():
    stocks = get_stocks_data()
    live_count = sum(1 for s in stocks if s['price'] > 0)
    return jsonify({
        'status': 'online',
        'total_stocks': 54,
        'live_stocks': live_count,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
