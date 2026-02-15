from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import requests
import xml.etree.ElementTree as ET
import os
import threading
import time
from datetime import datetime, timezone

app = Flask(__name__)
CORS(app)

# Global caches
masi_cache = {"price": "—", "change_pct": "—", "last_update": None}
stocks_cache = []
news_cache = []
last_refresh = None

# Very browser-like headers (TradingView is picky in 2026)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.tradingview.com/",
    "Origin": "https://www.tradingview.com",
    "Content-Type": "application/json",
}

def fetch_masi():
    global masi_cache
    print("[{}] Fetching MASI...".format(datetime.now(timezone.utc).isoformat()))
    try:
        url = "https://scanner.tradingview.com/morocco/scan"
        payload = {
            "symbols": {"tickers": ["IDX:CSEMA:MASI"], "query": {"types": []}},  # try IDX prefix if CSEMA fails
            "columns": ["close", "change"]
        }
        r = requests.post(url, json=payload, headers=HEADERS, timeout=12)
        print("MASI status:", r.status_code)
        if r.status_code != 200:
            print("MASI response preview:", r.text[:300])
            raise ValueError(f"Bad status {r.status_code}")
        data = r.json()
        if "data" in data and data["data"]:
            vals = data["data"][0]["d"]
            price = vals[0] if vals[0] is not None else None
            change = vals[1] if vals[1] is not None else None
            masi_cache = {
                "price": f"{float(price):,.2f}" if price else "—",
                "change_pct": f"{float(change):+.2f}%" if change else "—",
                "last_update": datetime.now(timezone.utc).isoformat()
            }
            print("MASI success:", masi_cache)
        else:
            print("No data key in MASI response")
    except Exception as e:
        print("MASI error:", str(e))

def fetch_stocks():
    global stocks_cache
    print("[{}] Fetching stocks...".format(datetime.now(timezone.utc).isoformat()))
    try:
        url = "https://scanner.tradingview.com/morocco/scan"
        payload = {
            "filter": [{"left": "type", "operation": "equal", "right": "stock"}],
            "columns": [
                "name",
                "close",
                "change",
                "market_cap_basic",
                "sector",
                "pe_basic",
                "Recommend.All"
            ],
            "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
            "range": [0, 100],
            "options": {"lang": "en"}
        }
        r = requests.post(url, json=payload, headers=HEADERS, timeout=20)
        print("Stocks status:", r.status_code)
        if r.status_code != 200:
            print("Stocks response preview:", r.text[:300])
            raise ValueError(f"Bad status {r.status_code}")
        data = r.json()
        stocks = []
        for item in data.get("data", []):
            d = item.get("d", [None] * 7)
            rating = "—"
            rec = d[6]
            if isinstance(rec, (int, float)):
                if rec <= 1.5: rating = "Strong Buy"
                elif rec <= 2.5: rating = "Buy"
                elif rec <= 3.5: rating = "Hold"
                elif rec <= 4.5: rating = "Sell"
                else: rating = "Strong Sell"
            stocks.append({
                "symbol": d[0] or "—",
                "market_cap": f"{d[3]/1e9:.2f}B" if d[3] else "—",
                "sector": d[4] or "—",
                "price": f"{float(d[1]):,.2f}" if d[1] else "—",
                "change_pct": f"{float(d[2]):+.2f}%" if d[2] else "—",
                "pe": f"{float(d[5]):.2f}" if d[5] else "—",
                "rating": rating
            })
        stocks_cache = stocks
        print(f"Stocks success: {len(stocks)} rows")
    except Exception as e:
        print("Stocks error:", str(e))
        stocks_cache = []

def fetch_news():
    global news_cache
    try:
        url = "https://medias24.com/categorie/leboursier/actus/feed/"
        r = requests.get(url, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=10)
        root = ET.fromstring(r.content)
        items = []
        for it in list(root.findall("./channel/item"))[:6]:
            title = (it.find("title") or {}).text or "—"
            link = (it.find("link") or {}).text or "#"
            date = (it.find("pubDate") or {}).text or "—"
            items.append({"title": title, "link": link, "pub_date": date})
        news_cache = items
        print(f"News: {len(items)} items")
    except Exception as e:
        print("News error:", str(e))

def refresh_loop():
    while True:
        fetch_masi()
        fetch_stocks()
        fetch_news()
        global last_refresh
        last_refresh = datetime.now(timezone.utc).isoformat()
        time.sleep(600)

threading.Thread(target=refresh_loop, daemon=True).start()

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/masi')
def get_masi():
    return jsonify(masi_cache)

@app.route('/api/stocks')
def get_stocks():
    return jsonify(stocks_cache)

@app.route('/api/news')
def get_news():
    return jsonify(news_cache)

@app.route('/api/health')
def health():
    return jsonify({
        "status": "running",
        "stocks_count": len(stocks_cache),
        "last_refresh": last_refresh
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
