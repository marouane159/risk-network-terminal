from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime, timezone

app = Flask(__name__)
CORS(app)

# Configuration
DATA_DIR = "data"
STOCKS_FILE = f"{DATA_DIR}/stocks.json"
NEWS_FILE = f"{DATA_DIR}/news.json"
UPDATE_FILE = f"{DATA_DIR}/last_update.txt"

# COMPLETE LIST - All 54 tickers
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

STOCK_NAMES = {s["symbol"]: s["name"] for s in BASE_STOCKS}
STOCK_SECTORS = {s["symbol"]: s["sector"] for s in BASE_STOCKS}

# Cache for scraped data
cache = {
    'stocks': [],
    'news': [],
    'last_update': None
}

def load_scraped_data():
    """Load data from scraped JSON files"""
    try:
        # Load stocks
        if os.path.exists(STOCKS_FILE):
            with open(STOCKS_FILE, 'r', encoding='utf-8') as f:
                cache['stocks'] = json.load(f)
            print(f"Loaded {len(cache['stocks'])} stocks from file")
        else:
            print("No stocks file found, using fallback data")
            cache['stocks'] = fallback_stocks()
        
        # Load news
        if os.path.exists(NEWS_FILE):
            with open(NEWS_FILE, 'r', encoding='utf-8') as f:
                cache['news'] = json.load(f)
            print(f"Loaded {len(cache['news'])} news from file")
        else:
            print("No news file found, using empty list")
            cache['news'] = []
        
        # Load last update time
        if os.path.exists(UPDATE_FILE):
            with open(UPDATE_FILE, 'r') as f:
                update_time = f.read().strip()
                if update_time:
                    cache['last_update'] = datetime.fromisoformat(update_time)
                    print(f"Last update: {cache['last_update']}")
        
        return True
    except Exception as e:
        print(f"Error loading data: {e}")
        return False

def fallback_stocks():
    """Return fallback stock data when scraping fails"""
    print("Using fallback stock data...")
    fallback_stocks = []
    for stock in BASE_STOCKS:
        fallback_stocks.append({
            'symbol': stock['symbol'],
            'name': stock['name'],
            'sector': stock['sector'],
            'price': 0.0,
            'change': 0.0,
            'volume': 'N/A',
            'trend': [100.0] * 7,
            'has_live_data': False
        })
    return fallback_stocks

@app.route('/')
def home():
    """Serve the main dashboard"""
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('.', filename)

@app.route('/api/stocks')
def get_stocks():
    """Get stocks data"""
    if not cache['stocks']:
        if not load_scraped_data():
            return jsonify({"error": "Failed to load stock data"}), 500
    
    return jsonify(cache['stocks'])

@app.route('/api/news')
def get_news():
    """Get news data"""
    if not cache['news']:
        if not load_scraped_data():
            return jsonify({"error": "Failed to load news data"}), 500
    
    return jsonify(cache['news'])

@app.route('/api/all')
def get_all():
    """Get everything"""
    if not cache['stocks'] or not cache['news']:
        if not load_scraped_data():
            return jsonify({"error": "Failed to load data"}), 500
    
    return jsonify({
        'stocks': cache['stocks'],
        'news': cache['news'],
        'lastUpdate': cache['last_update'].isoformat() if cache['last_update'] else None
    })

@app.route('/api/refresh')
def refresh_data():
    """Manually trigger data refresh"""
    try:
        # Import and run the scraper
        import scraper
        scraper.main()
        
        # Reload data
        load_scraped_data()
        
        return jsonify({"message": "Data refreshed successfully", "stocks": len(cache['stocks']), "news": len(cache['news'])})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/status')
def get_status():
    """Get API status"""
    status = {
        'api_status': 'online',
        'stocks_count': len(cache['stocks']),
        'news_count': len(cache['news']),
        'last_update': cache['last_update'].isoformat() if cache['last_update'] else None,
        'data_files_exist': {
            'stocks': os.path.exists(STOCKS_FILE),
            'news': os.path.exists(NEWS_FILE),
            'update': os.path.exists(UPDATE_FILE)
        }
    }
    return jsonify(status)

if __name__ == '__main__':
    print("\n" + "="*70)
    print("RISK NETWORK GROUP API")
    print(f"Total stocks: {len(BASE_STOCKS)}")
    print("="*70 + "\n")
    
    # Load initial data
    if load_scraped_data():
        print("Data loaded successfully")
    else:
        print("Failed to load data, using fallbacks")
    
    # Run server
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
