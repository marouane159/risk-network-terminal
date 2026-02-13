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

# Fallback stock list (same as scraper)
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

def load_stocks():
    """Load stocks from file with fallback to base list"""
    try:
        if os.path.exists(STOCKS_FILE):
            with open(STOCKS_FILE, 'r', encoding='utf-8') as f:
                file_stocks = json.load(f)
                if file_stocks and len(file_stocks) > 0:
                    return file_stocks
    except Exception as e:
        print(f"Error loading stocks file: {e}")
    
    # Return base list with zeros if file missing/corrupt
    return [{
        'symbol': s['symbol'],
        'name': s['name'],
        'sector': s['sector'],
        'price': 0.0,
        'change': 0.0,
        'has_live_data': False
    } for s in BASE_STOCKS]

def load_news():
    """Load news from file"""
    try:
        if os.path.exists(NEWS_FILE):
            with open(NEWS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return []

def fetch_rss_live():
    """Attempt to fetch fresh RSS data"""
    try:
        url = "https://medias24.com/categorie/leboursier/actus/feed/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return None
            
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
        
        return news if news else None
    except:
        return None

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/stocks')
def get_stocks():
    stocks = load_stocks()
    return jsonify(stocks)

@app.route('/api/news')
def get_news():
    # Try live fetch first
    live_news = fetch_rss_live()
    if live_news:
        return jsonify(live_news)
    
    # Fallback to file
    news = load_news()
    return jsonify(news if news else [])

@app.route('/api/all')
def get_all():
    stocks = load_stocks()
    
    # Try live news, fallback to file
    live_news = fetch_rss_live()
    news = live_news if live_news else load_news()
    
    return jsonify({
        'stocks': stocks,
        'news': news if news else [],
        'updated': datetime.now().isoformat()
    })

@app.route('/api/status')
def status():
    stocks = load_stocks()
    live_stocks = sum(1 for s in stocks if s.get('has_live_data', False))
    return jsonify({
        'status': 'online',
        'total_stocks': len(stocks),
        'live_stocks': live_stocks,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
