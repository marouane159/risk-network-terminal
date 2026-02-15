from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import threading
import time
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Master list with your predefined sectors for reliability
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
    {"symbol": "HPS", "name": "HPS", "sector": "Paiement"},
    {"symbol": "S2M", "name": "S2M", "sector": "Paiement"},
    {"symbol": "RIS", "name": "RISMA", "sector": "Hotel Management"},
    {"symbol": "DHO", "name": "DELTA HOLDING", "sector": "Industrie"},
    {"symbol": "DWY", "name": "DISWAY", "sector": "Distribution"},
    {"symbol": "SNA", "name": "STOKVIS NORD AFRIQUE", "sector": "Distribution"},
    {"symbol": "SNP", "name": "SNEP", "sector": "Industrie"},
    {"symbol": "STR", "name": "STROC INDUSTRIE", "sector": "Industrie"},
    {"symbol": "INV", "name": "INVOLYS", "sector": "Technologie"},
    {"symbol": "MIC", "name": "MICRODATA", "sector": "Technologie"},
    {"symbol": "DYT", "name": "DISTY TECHNOLOGIES", "sector": "Distribution"},
    {"symbol": "ADH", "name": "DOUJA PROM ADDOHA", "sector": "Immobilier"},
    {"symbol": "IMO", "name": "IMMORENT INVEST", "sector": "Immobilier"},
    {"symbol": "ADI", "name": "ALLIANCES", "sector": "Immobilier"},
    {"symbol": "AFI", "name": "AFRIC INDUSTRIES", "sector": "Industrie"},
    {"symbol": "AFM", "name": "AFMA", "sector": "Finance"},
    {"symbol": "AKT", "name": "AKDITAL S.A", "sector": "Santé"},
    {"symbol": "ALM", "name": "ALUMINIUM DU MAROC", "sector": "Matériaux"},
    {"symbol": "ARD", "name": "ARADEI CAPITAL", "sector": "Immobilier"},
    {"symbol": "ATH", "name": "AUTO HALL", "sector": "Automobile"},
    {"symbol": "ATL", "name": "ATLANTASANAD", "sector": "Assurance"},
    {"symbol": "ATW", "name": "ATTIJARIWAFA BANK", "sector": "Banque"},
    {"symbol": "BAL", "name": "BALIMA", "sector": "Immobilier"},
    {"symbol": "BCP", "name": "BANQUE CENTRALE POPULAIRE", "sector": "Banque"},
    {"symbol": "CRS", "name": "CARTIER SAADA", "sector": "Agroalimentaire"},
    {"symbol": "CIH", "name": "CREDIT IMMOBILIER ET HOTELIER", "sector": "Banque"},
    {"symbol": "CMT", "name": "CIMENTS DU MAROC", "sector": "Matériaux"},
    {"symbol": "COL", "name": "COLORADO", "sector": "Industrie"},
    {"symbol": "CTM", "name": "COMPAGNIE DE TRANSPORTS", "sector": "Transport"},
    {"symbol": "DIM", "name": "DELATTRE LEVIVIER", "sector": "Industrie"},
    {"symbol": "DRI", "name": "DARI COUSPATE", "sector": "Agroalimentaire"},
    {"symbol": "EQD", "name": "EQDOM", "sector": "Finance"},
    {"symbol": "FBR", "name": "FENIE BROSSETTE", "sector": "Industrie"},
    {"symbol": "IAM", "name": "MAROC TELECOM", "sector": "Télécom"},
    {"symbol": "INM", "name": "INDUSTRIE DU MAROC", "sector": "Industrie"},
    {"symbol": "JET", "name": "JET CONTRACTORS", "sector": "Construction"},
    {"symbol": "LES", "name": "LESIEUR CRISTAL", "sector": "Agroalimentaire"},
    {"symbol": "MOX", "name": "MAGHREB OXYGENE", "sector": "Industrie"},
    {"symbol": "MNG", "name": "MANAGEM", "sector": "Mines"},
    {"symbol": "MUT", "name": "MUTANDIS", "sector": "Agroalimentaire"},
    {"symbol": "SID", "name": "SONASID", "sector": "Industrie"},
    {"symbol": "SOT", "name": "SOTHEMA", "sector": "Santé"},
    {"symbol": "SRM", "name": "REALISATIONS MECANIQUES", "sector": "Industrie"},
    {"symbol": "MDP", "name": "MED PAPER", "sector": "Industrie"},
    {"symbol": "VCN", "name": "VICENNE", "sector": "Santé"},
    {"symbol": "SMI", "name": "SMI", "sector": "Mines"},
    {"symbol": "CDM", "name": "CREDIT DU MAROC", "sector": "Banque"},
    {"symbol": "CAP", "name": "Cash Plus", "sector": "Finance"},
    {"symbol": "GTM", "name": "SGTM", "sector": "BTP"}
]

data_cache = {"stocks": [], "last_update": ""}

def scrape_tradingview():
    global data_cache
    try:
        url = "https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')
        
        scraped_map = {}
        if table:
            for row in table.find_all('tr')[1:]:
                cells = row.find_all('td')
                if len(cells) >= 10:
                    # Clean the ticker (it often contains "MAD" or names in the same cell)
                    raw_ticker = cells[0].text.strip().split('\n')[0].strip()
                    # TradingView tickers for Morocco often have 'BVC:' or extra spaces
                    clean_ticker = raw_ticker.replace("BVC:", "").split(" ")[0].strip()
                    
                    scraped_map[clean_ticker] = {
                        "price": cells[1].text.strip(),
                        "change": cells[2].text.strip(),
                        "cap": cells[4].text.strip(),
                        "pe": cells[6].text.strip(),
                        "rating": cells[10].text.strip()
                    }

        # Sync with Master List
        final_list = []
        for base in BASE_STOCKS:
            live = scraped_map.get(base["symbol"], {})
            final_list.append({
                "ticker": base["symbol"],
                "name": base["name"],
                "sector": base["sector"],
                "price": live.get("price", "---"),
                "change": live.get("change", "0.00%"),
                "cap": live.get("cap", "---"),
                "pe": live.get("pe", "---"),
                "rating": live.get("rating", "Neutral"),
                "active": base["symbol"] in scraped_map
            })
        
        data_cache["stocks"] = final_list
        data_cache["last_update"] = datetime.now().strftime("%H:%M:%S")
        print(f"Scrape Success at {data_cache['last_update']}")
    except Exception as e:
        print(f"Scrape Error: {e}")

@app.route('/api/stocks')
def get_stocks():
    return jsonify(data_cache["stocks"])

if __name__ == '__main__':
    scrape_tradingview()
    def loop():
        while True:
            time.sleep(300)
            scrape_tradingview()
    threading.Thread(target=loop, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
