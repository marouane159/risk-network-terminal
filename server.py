from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import requests
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime, timezone

app = Flask(__name__)
CORS(app)

DATA_DIR = "data"
STOCKS_FILE = f"{DATA_DIR}/stocks.json"
NEWS_FILE = f"{DATA_DIR}/news.json"
RSS_URL = "https://medias24.com/categorie/leboursier/actus/feed/"

# COMPLETE 54 STOCKS BASE LIST
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

def load_json_data():
    """Load local JSON data with fallback to base list"""
    stocks = []
    news = []
    
    # Load stocks
    try:
        if os.path.exists(STOCKS_FILE):
            with open(STOCKS_FILE, 'r', encoding='utf-8') as f:
                file_stocks = json.load(f)
                # Create dict for quick lookup
                stock_dict = {s['symbol']: s for s in file_stocks}
                
                # Ensure all 54 stocks are present
                for base in BASE_STOCKS:
                    symbol = base['symbol']
                    if symbol in stock_dict:
                        stocks.append(stock_dict[symbol])
                    else:
                        stocks.append({
                            'symbol': symbol,
                            'name': base['name'],
                            'sector': base['sector'],
                            'price': 0.0,
                            'change': 0.0,
                            'has_live_data': False
                        })
        else:
            # No file, return base list with zeros
            stocks = [{
                'symbol': s['symbol'],
                'name': s['name'],
                'sector': s['sector'],
                'price': 0.0,
                'change': 0.0,
                'has_live_data': False
            } for s in BASE_STOCKS]
    except Exception as e:
        print(f"Error loading stocks: {e}")
        stocks = [{
            'symbol': s['symbol'],
            'name': s['name'],
            'sector': s['sector'],
            'price': 0.0,
            'change': 0.0,
            'has_live_data': False
        } for s in BASE_STOCKS]
    
    # Load news
    try:
        if os.path.exists(NEWS_FILE):
            with open(NEWS_FILE, 'r', encoding='utf-8') as f:
                news = json.load(f)
    except:
        pass
    
    return stocks, news

def fetch_rss():
    """Fetch and parse Medias24 RSS feed with robust error handling"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(RSS_URL, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return []
        
        # Parse XML
        try:
            root = ET.fromstring(response.content)
        except ET.ParseError:
            # Try with encoding fix
            content = response.content.decode('utf-8', errors='ignore')
            root = ET.fromstring(content)
        
        # Find all item elements (handle both RSS and Atom)
        items = root.findall('.//item')
        if not items:
            items = root.findall('.//entry')  # Atom format
        
        news = []
        now = datetime.now(timezone.utc)
        
        for item in items[:15]:  # Get top 15
            try:
                title = item.find('title')
                link = item.find('link')
                pubDate = item.find('pubDate')
                category = item.find('category')
                
                title_text = title.text if title is not None else 'Sans titre'
                link_text = link.text if link is not None else ''
                
                # Handle link as attribute (Atom)
                if not link_text and link is not None:
                    link_text = link.get('href', '')
                
                date_text = pubDate.text if pubDate is not None else ''
                cat_text = category.text if category is not None else 'INFO'
                
                # Calculate minutes ago
                time_mins = 0
                if date_text:
                    try:
                        # Try different date formats
                        try:
                            pub_date = datetime.strptime(date_text, '%a, %d %b %Y %H:%M:%S %z')
                        except:
                            try:
                                pub_date = datetime.strptime(date_text, '%a, %d %b %Y %H:%M:%S %Z')
                            except:
                                pub_date = datetime.strptime(date_text[:25], '%a, %d %b %Y %H:%M:%S')
                        
                        if pub_date.tzinfo is None:
                            pub_date = pub_date.replace(tzinfo=timezone.utc)
                        
                        diff = now - pub_date
                        time_mins = int(diff.total_seconds() / 60)
                    except Exception as e:
                        time_mins = 0
                
                news.append({
                    'title': title_text,
                    'link': link_text,
                    'date': date_text,
                    'category': cat_text.upper(),
                    'time': time_mins,
                    'source': 'Medias24.com'
                })
            except Exception as e:
                continue
        
        return news
    except Exception as e:
        print(f"RSS Error: {e}")
        return []

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/stocks')
def get_stocks():
    stocks, _ = load_json_data()
    return jsonify(stocks)

@app.route('/api/news')
def get_news():
    # Try fresh RSS first
    fresh_news = fetch_rss()
    if fresh_news:
        return jsonify(fresh_news)
    
    # Fallback to file
    _, news = load_json_data()
    if news:
        return jsonify(news)
    
    # Empty but valid response
    return jsonify([])

@app.route('/api/all')
def get_all():
    stocks, cached_news = load_json_data()
    fresh_news = fetch_rss()
    news = fresh_news if fresh_news else cached_news
    
    return jsonify({
        'stocks': stocks,
        'news': news if news else [],
        'updated': datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
