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
CORS(app)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
STOCKS_FILE = f"{DATA_DIR}/stocks.json"

# Master list provided by user to ensure 100% symbol coverage
BASE_STOCKS = [
    {"symbol": "TGC", "name": "TRAVAUX GENERAUX DE CONSTRUCTIONS", "sector": "Construction"},
    {"symbol": "TMA", "name": "TOTALENERGIES MARKETING ", "sector": "Énergie"},
    {"symbol": "TQM", "name": "TAQA MOROCCO", "sector": "Énergie"},
    {"symbol": "NKL", "name": "ENNAKL SA", "sector": "Transport"},
    {"symbol": "LHM", "name": "LAFARGEHOLCIM", "sector": "Construction"},
    {"symbol": "UMR", "name": "UNIMER", "sector": "Agroalimentaire"},
    {"symbol": "WAA", "name": "WAFA ASSURANCE", "sector": "Assurance"},
    {"symbol": "ZDJ", "name": "ZELLIDJA S.A", "sector": "Mines"},
    {"symbol": "MSA", "name": "SODEP MARSA ", "sector": "Transport"},
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

def scrape_tradingview():
    print(f"[{datetime.now()}] Scraping TradingView...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        url = "https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/"
        response = requests.get(url, headers=headers, timeout=20)
        
        if response.status_code != 200: return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')
        if not table: return None

        scraped_data = {}
        rows = table.find_all('tr')[1:] # Skip Header

        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 11: continue
            
            # Extract Symbol
            sym_tag = cells[0].find('a')
            if not sym_tag: continue
            symbol = sym_tag.text.strip()
            
            try:
                # Clean numeric data
                price = float(cells[1].text.replace('MAD', '').replace(',', '').strip())
                # TradingView uses '−' (Unicode) instead of '-' (ASCII)
                change = float(cells[2].text.replace('%', '').replace('−', '-').replace('+', '').strip())
                cap = cells[4].text.strip()
                pe_val = cells[6].text.strip()
                pe = float(pe_val) if pe_val not in ['—', ''] else None
                rating = cells[10].text.strip()
                sector = cells[11].text.strip() if len(cells) > 11 else ""

                scraped_data[symbol] = {
                    "price": price,
                    "change": change,
                    "capital": cap,
                    "pe": pe,
                    "rating": rating,
                    "sector": sector
                }
            except: continue

        # Merge with BASE_STOCKS to ensure 100% coverage
        final_results = []
        for base in BASE_STOCKS:
            live = scraped_data.get(base['symbol'], {})
            final_results.append({
                "symbol": base['symbol'],
                "name": base['name'],
                "sector": live.get('sector', base['sector']),
                "capital": live.get('capital', '—'),
                "price": live.get('price', 0.0),
                "change": live.get('change', 0.0),
                "pe": live.get('pe', None),
                "rating": live.get('rating', '—'),
                "has_live_data": base['symbol'] in scraped_data
            })

        # Sort: Active stocks first
        final_results.sort(key=lambda x: (not x['has_live_data'], x['symbol']))
        
        with open(STOCKS_FILE, 'w') as f:
            json.dump(final_results, f, ensure_ascii=False, indent=2)
        return final_results

    except Exception as e:
        print(f"Error: {e}")
        return None

@app.route('/api/stocks')
def get_stocks_api():
    if os.path.exists(STOCKS_FILE):
        with open(STOCKS_FILE, 'r') as f:
            return jsonify(json.load(f))
    return jsonify(scrape_tradingview())

@app.route('/api/news')
def get_news_api():
    # Medias24 RSS logic
    try:
        url = "https://medias24.com/categorie/leboursier/actus/feed/"
        resp = requests.get(url, timeout=10)
        root = ET.fromstring(resp.content)
        news = []
        for item in root.findall('.//item')[:10]:
            news.append({
                "title": item.find('title').text,
                "link": item.find('link').text,
                "category": "BOURSE",
                "time": "Recent"
            })
        return jsonify(news)
    except: return jsonify([])

if __name__ == '__main__':
    # Initial Scrape
    scrape_tradingview()
    # Background Update every 5 minutes
    def update_loop():
        while True:
            time.sleep(300)
            scrape_tradingview()
    threading.Thread(target=update_loop, daemon=True).start()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
