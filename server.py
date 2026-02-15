from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import requests
import threading
import time
from datetime import datetime
import xml.etree.ElementTree as ET

app = Flask(__name__, static_folder=".")
CORS(app)

CACHE = {
    "stocks": [],
    "masi": {},
    "last_update": None
}

UPDATE_INTERVAL = 600  # 10 minutes


# -------------------------
# SCRAPE TRADINGVIEW STOCKS
# -------------------------
def fetch_stocks():
    try:
        url = "https://scanner.tradingview.com/morocco/scan"

        payload = {
            "filter": [],
            "options": {"lang": "en"},
            "symbols": {"query": {"types": []}, "tickers": []},
            "columns": [
                "name",
                "market_cap_basic",
                "sector",
                "close",
                "change",
                "price_earnings_ttm",
                "Recommend.All"
            ]
        }

        response = requests.post(url, json=payload)
        data = response.json()

        stocks = []

        for item in data.get("data", []):
            d = item["d"]

            stocks.append({
                "symbol": d[0],
                "market_cap": d[1],
                "sector": d[2],
                "price": d[3],
                "change": d[4],
                "pe": d[5],
                "rating": d[6]
            })

        return stocks

    except Exception as e:
        print("Stocks error:", e)
        return []


# -------------------------
# SCRAPE MASI INDEX
# -------------------------
def fetch_masi():
    try:
        url = "https://scanner.tradingview.com/morocco/scan"

        payload = {
            "symbols": {"tickers": ["CSEMA:MASI"], "query": {"types": []}},
            "columns": ["close", "change"]
        }

        response = requests.post(url, json=payload)
        data = response.json()

        if data.get("data"):
            d = data["data"][0]["d"]
            return {
                "price": d[0],
                "change": d[1]
            }

        return {}

    except Exception as e:
        print("MASI error:", e)
        return {}


# -------------------------
# SCRAPE NEWS RSS
# -------------------------
def fetch_news():
    try:
        rss_url = "https://medias24.com/categorie/leboursier/actus/feed/"
        response = requests.get(rss_url)
        root = ET.fromstring(response.content)

        items = []
        for item in root.findall(".//item")[:6]:
            items.append({
                "title": item.find("title").text,
                "link": item.find("link").text
            })

        return items

    except Exception as e:
        print("News error:", e)
        return []


# -------------------------
# AUTO UPDATE THREAD
# -------------------------
def update_data():
    while True:
        print("Updating data...")
        CACHE["stocks"] = fetch_stocks()
        CACHE["masi"] = fetch_masi()
        CACHE["news"] = fetch_news()
        CACHE["last_update"] = datetime.utcnow().isoformat()
        time.sleep(UPDATE_INTERVAL)


threading.Thread(target=update_data, daemon=True).start()


# -------------------------
# ROUTES
# -------------------------
@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/api/data")
def api_data():
    return jsonify(CACHE)


# -------------------------
# START
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
