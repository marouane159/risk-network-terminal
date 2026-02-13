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

# ALL 54 STOCKS - Hardcoded complete list
ALL_STOCKS = [
    {"symbol": "TGC", "name": "TRAVAUX GENERAUX DE CONSTRUCTIONS", "sector": "Construction", "price": 0.0, "change": 0.0},
    {"symbol": "TMA", "name": "TOTALENERGIES MARKETING", "sector": "Énergie", "price": 0.0, "change": 0.0},
    {"symbol": "TQM", "name": "TAQA MOROCCO", "sector": "Énergie", "price": 0.0, "change": 0.0},
    {"symbol": "NKL", "name": "ENNAKL SA", "sector": "Transport", "price": 0.0, "change": 0.0},
    {"symbol": "LHM", "name": "LAFARGEHOLCIM", "sector": "Construction", "price": 0.0, "change": 0.0},
    {"symbol": "UMR", "name": "UNIMER", "sector": "Agroalimentaire", "price": 0.0, "change": 0.0},
    {"symbol": "WAA", "name": "WAFA ASSURANCE", "sector": "Assurance", "price": 0.0, "change": 0.0},
    {"symbol": "ZDJ", "name": "ZELLIDJA S.A", "sector": "Mines", "price": 0.0, "change": 0.0},
    {"symbol": "MSA", "name": "SODEP MARSA", "sector": "Transport", "price": 0.0, "change": 0.0},
    {"symbol": "RDS", "name": "RESIDENCE DAR SAADA", "sector": "Construction", "price": 0.0, "change": 0.0},
    {"symbol": "CSR", "name": "COSUMAR", "sector": "Industrie", "price": 0.0, "change": 0.0},
    {"symbol": "CFG", "name": "CFG BANK", "sector": "Banque", "price": 0.0, "change": 0.0},
    {"symbol": "CMG", "name": "CMGP CAS", "sector": "Agriculture", "price": 0.0, "change": 0.0},
    {"symbol": "HPS", "name": "HPS", "sector": "Paiment", "price": 0.0, "change": 0.0},
    {"symbol": "S2M", "name": "S2M", "sector": "Paiment", "price": 0.0, "change": 0.0},
    {"symbol": "RIS", "name": "RISMA", "sector": "Hotel Management", "price": 0.0, "change": 0.0},
    {"symbol": "DHO", "name": "DELTA HOLDING", "sector": "Industrie", "price": 0.0, "change": 0.0},
    {"symbol": "DWY", "name": "DISWAY", "sector": "Distribution éléctro", "price": 0.0, "change": 0.0},
    {"symbol": "SNA", "name": "STOKVIS NORD AFRIQUE", "sector": "Distribution service", "price": 0.0, "change": 0.0},
    {"symbol": "SNP", "name": "SNEP", "sector": "Process Industries", "price": 0.0, "change": 0.0},
    {"symbol": "STR", "name": "STROC INDUSTRIE", "sector": "Service Industriel", "price": 0.0, "change": 0.0},
    {"symbol": "INV", "name": "INVOLYS", "sector": "Service de Technologie", "price": 0.0, "change": 0.0},
    {"symbol": "MIC", "name": "MICRODATA", "sector": "Service de Technologie", "price": 0.0, "change": 0.0},
    {"symbol": "DYT", "name": "DISTY TECHNOLOGIES", "sector": "Service de destribution", "price": 0.0, "change": 0.0},
    {"symbol": "ADH", "name": "DOUJA PROM ADDOHA", "sector": "Immobilier", "price": 0.0, "change": 0.0},
    {"symbol": "IMO", "name": "IMMORENT INVEST", "sector": "Immobilier", "price": 0.0, "change": 0.0},
    {"symbol": "ADI", "name": "ALLIANCES", "sector": "Divers", "price": 0.0, "change": 0.0},
    {"symbol": "AFI", "name": "AFRIC INDUSTRIES", "sector": "Industrie", "price": 0.0, "change": 0.0},
    {"symbol": "AFM", "name": "AFMA", "sector": "Finance", "price": 0.0, "change": 0.0},
    {"symbol": "AKT", "name": "AKDITAL S.A", "sector": "Santé", "price": 0.0, "change": 0.0},
    {"symbol": "ALM", "name": "ALUMINIUM DU MAROC", "sector": "Matériaux", "price": 0.0, "change": 0.0},
    {"symbol": "ARD", "name": "ARADEI CAPITAL", "sector": "Immobilier", "price": 0.0, "change": 0.0},
    {"symbol": "ATH", "name": "AUTO HALL", "sector": "Automobile", "price": 0.0, "change": 0.0},
    {"symbol": "ATL", "name": "ATLANTASANAD", "sector": "Distribution", "price": 0.0, "change": 0.0},
    {"symbol": "ATW", "name": "ATTIJARIWAFA BANK", "sector": "Banque", "price": 0.0, "change": 0.0},
    {"symbol": "BAL", "name": "BALIMA", "sector": "Distribution", "price": 0.0, "change": 0.0},
    {"symbol": "BCP", "name": "BANQUE CENTRALE POPULAIRE", "sector": "Banque", "price": 0.0, "change": 0.0},
    {"symbol": "CRS", "name": "CARTIER SAADA", "sector": "Distribution", "price": 0.0, "change": 0.0},
    {"symbol": "CIH", "name": "CREDIT IMMOBILIER ET HOTELIER", "sector": "Banque", "price": 0.0, "change": 0.0},
    {"symbol": "CMT", "name": "CIMENTS DU MAROC", "sector": "Matériaux", "price": 0.0, "change": 0.0},
    {"symbol": "COL", "name": "COLORADO", "sector": "Distribution", "price": 0.0, "change": 0.0},
    {"symbol": "CTM", "name": "COMPAGNIE DE TRANSPORTS AU MAROC", "sector": "Transport", "price": 0.0, "change": 0.0},
    {"symbol": "DIM", "name": "DELATTRE LEVIVIER MAROC", "sector": "Industrie", "price": 0.0, "change": 0.0},
    {"symbol": "DRI", "name": "DARI COUSPATE", "sector": "Agroalimentaire", "price": 0.0, "change": 0.0},
    {"symbol": "EQD", "name": "EQDOM", "sector": "Immobilier", "price": 0.0, "change": 0.0},
    {"symbol": "FBR", "name": "FENIE BROSSETTE", "sector": "Distribution", "price": 0.0, "change": 0.0},
    {"symbol": "IAM", "name": "MAROC TELECOM", "sector": "Télécom", "price": 0.0, "change": 0.0},
    {"symbol": "INM", "name": "INDUSTRIE DU MAROC", "sector": "Industrie", "price": 0.0, "change": 0.0},
    {"symbol": "JET", "name": "JET CONTRACTORS", "sector": "Construction", "price": 0.0, "change": 0.0},
    {"symbol": "LES", "name": "LESIEUR CRISTAL", "sector": "Agroalimentaire", "price": 0.0, "change": 0.0},
    {"symbol": "MOX", "name": "MAGHREB OXYGENE", "sector": "Industrie", "price": 0.0, "change": 0.0},
    {"symbol": "MNG", "name": "MANAGEM", "sector": "Mines", "price": 0.0, "change": 0.0},
    {"symbol": "MUT", "name": "MUTANDIS", "sector": "Agroalimentaire", "price": 0.0, "change": 0.0},
    {"symbol": "SID", "name": "SONASID", "sector": "Agroalimentaire", "price": 0.0, "change": 0.0},
    {"symbol": "SOT", "name": "SOTHEMA", "sector": "Pharma", "price": 0.0, "change": 0.0},
    {"symbol": "SRM", "name": "REALISATIONS MECANIQUES", "sector": "Industrie", "price": 0.0, "change": 0.0},
    {"symbol": "MDP", "name": "MED PAPER", "sector": "Industrie", "price": 0.0, "change": 0.0},
    {"symbol": "VCN", "name": "VICENNE", "sector": "Santé", "price": 0.0, "change": 0.0},
    {"symbol": "SMI", "name": "Société métallurgique d'imiter", "sector": "Finance", "price": 0.0, "change": 0.0},
    {"symbol": "CDM", "name": "Crédit du Maroc", "sector": "Banque", "price": 0.0, "change": 0.0}
]

def get_stocks():
    """Return all 54 stocks, updating prices from file if available"""
    stocks = [s.copy() for s in ALL_STOCKS]
    
    try:
        if os.path.exists(STOCKS_FILE):
            with open(STOCKS_FILE, 'r') as f:
                file_data = json.load(f)
            
            file_dict = {s['symbol']: s for s in file_data}
            
            for stock in stocks:
                symbol = stock['symbol']
                if symbol in file_dict:
                    stock['price'] = float(file_dict[symbol].get('price', 0))
                    stock['change'] = float(file_dict[symbol].get('change', 0))
    except:
        pass
    
    # Sort: with price first
    stocks.sort(key=lambda x: (x['price'] == 0, x['symbol']))
    return stocks

def get_news():
    """Fetch live RSS or return file"""
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
            
            if news:
                return news
    except:
        pass
    
    # Fallback to file
    try:
        if os.path.exists(NEWS_FILE):
            with open(NEWS_FILE, 'r') as f:
                return json.load(f)
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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
