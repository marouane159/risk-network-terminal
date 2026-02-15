#!/usr/bin/env python3

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import requests
import xml.etree.ElementTree as ET
import os
import re
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

# -----------------------
# GLOBAL CACHE
# -----------------------
stocks_cache = []
news_cache = []
masi_cache = {}
last_update = None

REFRESH_INTERVAL = 600  # 10 minutes


# -----------------------
# MARKET STATUS
# -----------------------
def get_market_status():
    now = datetime.now(timezone(timedelta(hours=1)))
    weekday = now.weekday()
    current_minutes = now.hour * 60 + now.minute

    open_time = 9 * 60 + 30
    close_time = 15 * 60 + 40

    is_open = weekday < 5 and open_time <= current_minutes <= close_time

    return {
        "is_open": is_open,
        "next_open": "09:30"
    }


# -----------------------
# SCRAPE TRADINGVIEW (REAL FIX)
# -----------------------
def scrape_tradingview():
    global stocks_cache

    url = "https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers, timeout=30)
    soup = BeautifulSoup(response.text, "html.parser")

    scripts = soup.find_all("script")

    stocks = []

    for script in scripts:
        if "market-movers" in script.text and "symbols" in script.text:
            data_match = re.search(r"symbols\":(\[.*?\])", script.text)

            if data_match:
                try:
                    import json
                    symbols = json.loads(data_match.group(1))

                    for s in symbols:
                        stocks.append({
                            "symbol": s.get("symbol", ""),
                            "sector": s.get("sector", "—"),
                            "capital": "—",
                            "price": float(s.get("close", 0)),
                            "change": float(s.get("change", 0)),
                            "pe": None,
                            "rating": "—",
                            "has_live_data": True
                        })
                except:
                    pass

    stocks_cache = stocks
    return stocks_cache


# -----------------------
# MASI
# -----------------------
def scrape_masi():
    global masi_cache

    url = "https://www.investing.com/indices/masi"
    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, headers=headers, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    price_div = soup.find("div", class_=re.compile("instrument-price"))

    price = 0
    if price_div:
        try:
            price = float(price_div.text.replace(",", "").strip())
        except:
            pass

    masi_cache = {
        "symbol": "MASI",
        "price": price,
        "change_percent": 0
    }

    return masi_cache


# -----------------------
# NEWS
# -----------------------
def scrape_news():
    global news_cache

    url = "https://medias24.com/categorie/leboursier/actus/feed/"
    r = requests.get(url, timeout=15)

    news = []

    if r.status_code == 200:
        root = ET.fromstring(r.content)
        items = root.findall(".//item")

        for item in items[:8]:
            title = item.find("title").text if item.find("title") else ""
            link = item.find("link").text if item.find("link") else ""

            news.append({
                "title": title,
                "link": link,
                "category": "BOURSE",
                "time": 0
            })

    news_cache = news
    return news_cache


# -----------------------
# AUTO REFRESH LOGIC
# -----------------------
def refresh_if_needed():
    global last_update

    if last_update is None:
        should_refresh = True
    else:
        diff = (datetime.utcnow() - last_update).total_seconds()
        should_refresh = diff > REFRESH_INTERVAL

    if should_refresh:
        print("Refreshing data...")
        scrape_tradingview()
        scrape_masi()
        scrape_news()
        last_update = datetime.utcnow()


# -----------------------
# ROUTES
# -----------------------
@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/api/all")
def api_all():
    refresh_if_needed()

    return jsonify({
        "stocks": stocks_cache,
        "news": news_cache,
        "masi": masi_cache,
        "market_status": get_market_status(),
        "last_update": last_update
    })


# -----------------------
# RENDER ENTRYPOINT
# -----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
