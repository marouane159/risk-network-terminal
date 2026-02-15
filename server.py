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
# Updated CORS for wider compatibility with Render/GitHub Pages
CORS(app, resources={r"/*": {"origins": "*"}})

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
STOCKS_FILE = f"{DATA_DIR}/stocks.json"

# YOUR PROVIDED MASTER LIST - Ensuring 100% coverage
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
    {"symbol": "ALM", "name": "ALUMINIUM DU ", "sector": "Matériaux"},
    {"symbol": "ARD", "name": "ARADEI CAPITAL", "sector": "Immobilier"},
    {"symbol": "ATH", "name": "AUTO HALL", "sector": "Automobile"},
    {"symbol": "ATL", "name": "ATLANTASANAD", "sector": "Distribution"},
    {"symbol": "ATW", "name": "ATTIJARIWAFA BANK", "sector": "Banque"},
    {"symbol": "BAL", "name": "BALIMA", "sector": "Distribution"},
    {"symbol": "BCP", "name": "BANQUE CENTRALE POPULAIRE", "sector": "Banque"},
    {"symbol": "CRS", "name": "CARTIER SAADA", "sector": "Distribution"},
    {"symbol": "CIH", "name": "CREDIT IMMOBILIER ET HOTELIER", "sector": "Banque"},
    {"symbol": "CMT", "name": "CIMENTS DU ", "sector": "Matériaux"},
    {"symbol": "COL", "name": "COLORADO", "sector": "Distribution"},
    {"symbol": "CTM", "name": "COMPAGNIE DE TRANSPORTS AU ", "sector": "Transport"},
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
    {"symbol": "RDS", "name": "RÉSIDENCES DAR SAADA", "sector": "Immobilier"},
    {"symbol": "SID", "name": "SONASID", "sector": "Agroalimentaire"},
    {"symbol": "SNP", "name": "SNEP", "sector": "Industrie"},
    {"symbol": "SOT", "name": "SOTHEMA", "sector": "Pharma"},
    {"symbol": "SRM", "name": "REALISATIONS MECANIQUES", "sector": "Industrie"},
    {"symbol": "STR", "name": "STROC INDUSTRIE", "sector": "Industrie"},
    {"symbol": "MDP", "name": "MED PAPER", "sector": "Industrie"},
    {"symbol": "VCN", "name": "VICENNE", "sector": "Santé"},
    {"symbol": "SMI", "name": "Société métallurgique d'imiter", "sector": "Finance"},
    {"symbol": "CDM", "name": "Crédit du Maroc", "sector": "Banque"}
]

def scrape_tradingview():
    print(f"[{datetime.now()}] Deep-Scraping TradingView...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        url = "https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/"
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200: return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')
        if not table: return None

        tv_extracted = {}
        rows = table.find_all('tr')[1:] # Skip header row

        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 11: continue # Ensure row has full data
            
            # Extract symbol strictly from the <a> tag inside first cell
            symbol_tag = cells[0].find('a')
            if not symbol_tag: continue
            symbol = symbol_tag.text.strip()
            
            try:
                # FIXED COLUMN MAPPING
                # Col 1: Price | Col 2: Change % | Col 4: Cap | Col 6: P/E | Col 10: Rating
                price = float(cells[1].text.replace('MAD', '').replace(',', '').strip())
                change = float(cells[2].text.replace('%', '').replace('−', '-').replace('+', '').strip())
                cap = cells[4].text.strip()
                pe_raw = cells[6].text.strip()
                pe = float(pe_raw) if pe_raw not in ['—', ''] else None
                rating = cells[10].text.strip()

                tv_extracted[symbol] = {
                    "price": price,
                    "change": change,
                    "capital": cap,
                    "pe": pe,
                    "rating": rating
                }
            except: continue

        # Final Merge: Ensure all BASE_STOCKS exist even if not found in scraper
        final_data = []
        for base in BASE_STOCKS:
            live = tv_extracted.get(base['symbol'], {})
            final_data.append({
                "symbol": base['symbol'],
                "name": base['name'],
                "sector": base['sector'], # Keeps your original sectors
                "capital": live.get('capital', '—'),
                "price": live.get('price', 0.0),
                "change": live.get('change', 0.0),
                "pe": live.get('pe', None),
                "rating": live.get('rating', '—'),
                "has_live_data": base['symbol'] in tv_extracted
            })

        with open(STOCKS_FILE, 'w') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        return final_data

    except Exception as e:
        print(f"Scrape Fail: {e}")
        return None

@app.route('/api/stocks')
def api_stocks():
    if not os.path.exists(STOCKS_FILE): scrape_tradingview()
    with open(STOCKS_FILE, 'r') as f: return jsonify(json.load(f))

@app.route('/api/news')
def api_news():
    try:
        url = "https://medias24.com/categorie/leboursier/actus/feed/"
        r = requests.get(url, timeout=10)
        root = ET.fromstring(r.content)
        news = []
        for item in root.findall('.//item')[:10]:
            news.append({"title": item.find('title').text, "link": item.find('link').text})
        return jsonify(news)
    except: return jsonify([])

if __name__ == '__main__':
    # Initial run and background thread to prevent staleness
    scrape_tradingview()
    def loop():
        while True:
            time.sleep(600)
            scrape_tradingview()
    threading.Thread(target=loop, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
