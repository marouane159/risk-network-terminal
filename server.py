from flask import Flask, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import threading
import time

app = Flask(__name__)
CORS(app)

# The Full Symbol List to ensure 100% coverage
SYMBOLS = ["TGC", "TMA", "TQM", "NKL", "LHM", "UMR", "WAA", "ZDJ", "MSA", "RDS", "CSR", "CFG", "CMG", "HPS", "S2M", "RIS", "DHO", "DWY", "SNA", "SNP", "STR", "INV", "MIC", "DYT", "ADH", "IMO", "ADI", "AFI", "AFM", "AKT", "ALM", "ARD", "ATH", "ATL", "ATW", "BAL", "BCP", "CRS", "CIH", "CMT", "COL", "CTM", "DIM", "DRI", "EQD", "FBR", "IAM", "INM", "JET", "LES", "MOX", "MNG", "MUT", "SID", "SOT", "SRM", "MDP", "VCN", "SMI", "CDM"]

cached_stocks = []

def scrape_tradingview():
    global cached_stocks
    url = "https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.find_all('tr')[1:] 
        
        live_data = {}
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 11:
                # Robust ticker extraction (splits by newline to get only symbol)
                ticker = cols[0].text.strip().split('\n')[0].replace(" ", "")
                live_data[ticker] = {
                    "price": cols[1].text.strip(),
                    "change": cols[2].text.strip(),
                    "cap": cols[4].text.strip(),
                    "pe": cols[6].text.strip(),
                    "rating": cols[10].text.strip()
                }

        final_results = []
        for sym in SYMBOLS:
            item = live_data.get(sym, {"price": "---", "change": "0.00%", "cap": "---", "pe": "---", "rating": "Neutral"})
            final_results.append({
                "ticker": sym,
                "price": item["price"],
                "change": item["change"],
                "cap": item["cap"],
                "pe": item["pe"],
                "rating": item["rating"]
            })
        cached_stocks = final_results
    except Exception as e:
        print(f"Scrape failed: {e}")

@app.route('/api/stocks')
def get_stocks():
    return jsonify(cached_stocks)

if __name__ == '__main__':
    scrape_tradingview() 
    # Auto-refresh cache every 5 minutes in background
    def update_loop():
        while True:
            time.sleep(300)
            scrape_tradingview()
    threading.Thread(target=update_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
