#!/usr/bin/env python3

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import os
from statistics import mean

app = Flask(__name__)
CORS(app)

stocks_cache = []
news_cache = []
masi_cache = {}
last_update = None

REFRESH_INTERVAL = 600  # 10 minutes


# ==============================
# MARKET STATUS
# ==============================

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


# ==============================
# RATING CONVERTER
# ==============================

def convert_rating(value):
    if value is None:
        return "—"

    if value >= 0.5:
        return "Strong Buy"
    elif value >= 0.1:
        return "Buy"
    elif value > -0.1:
        return "Neutral"
    elif value > -0.5:
        return "Sell"
    else:
        return "Strong Sell"


# ==============================
# TRADINGVIEW API
# ==============================

def scrape_tradingview():
    global stocks_cache

    url = "https://scanner.tradingview.com/morocco/scan"

    payload = {
        "filter": [],
        "options": {"lang": "en"},
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": [
            "name",
            "sector",
            "close",
            "change",
            "market_cap_basic",
            "price_earnings_ttm",
            "Recommend.All",
            "volume",
            "dividend_yield_recent",
            "52_week_high",
            "52_week_low"
        ]
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json"
    }

    r = requests.post(url, json=payload, headers=headers, timeout=30)
    data = r.json()

    stocks = []

    for item in data.get("data", []):
        d = item.get("d", [])

        stocks.append({
            "symbol": d[0],
            "sector": d[1] if d[1] else "—",
            "price": float(d[2]) if d[2] else 0,
            "change": float(d[3]) if d[3] else 0,
            "market_cap": d[4] if d[4] else 0,
            "pe": round(d[5], 2) if d[5] else None,
            "rating_raw": d[6],
            "rating": convert_rating(d[6]),
            "volume": d[7] if d[7] else 0,
            "dividend_yield": round(d[8], 2) if d[8] else None,
            "high_52w": round(d[9], 2) if d[9] else None,
            "low_52w": round(d[10], 2) if d[10] else None,
            "has_live_data": True
        })

    stocks_cache = stocks
    return stocks


# ==============================
# MASI
# ==============================

def scrape_masi():
    global masi_cache

    url = "https://scanner.tradingview.com/morocco/scan"

    payload = {
        "symbols": {"tickers": ["INDEX:MASI"], "query": {"types": []}},
        "columns": ["close", "change"]
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json"
    }

    r = requests.post(url, json=payload, headers=headers, timeout=30)
    data = r.json()

    if "data" in data and len(data["data"]) > 0:
        d = data["data"][0]["d"]

        masi_cache = {
            "symbol": "MASI",
            "price": float(d[0]),
            "change_percent": float(d[1])
        }

    return masi_cache


# ==============================
# NEWS
# ==============================

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
    return news


# ==============================
# ANALYTICS ENGINE
# ==============================

def compute_market_analytics(stocks):

    gainers = sorted(stocks, key=lambda x: x["change"], reverse=True)[:5]
    losers = sorted(stocks, key=lambda x: x["change"])[:5]
    most_active = sorted(stocks, key=lambda x: x["volume"], reverse=True)[:5]

    advancers = len([s for s in stocks if s["change"] > 0])
    decliners = len([s for s in stocks if s["change"] < 0])

    bullish = sorted(
        [s for s in stocks if s["rating_raw"] is not None],
        key=lambda x: x["rating_raw"],
        reverse=True
    )[:5]

    bearish = sorted(
        [s for s in stocks if s["rating_raw"] is not None],
        key=lambda x: x["rating_raw"]
    )[:5]

    sector_map = {}
    for s in stocks:
        if s["sector"] not in sector_map:
            sector_map[s["sector"]] = []
        sector_map[s["sector"]].append(s["change"])

    sector_performance = {
        sector: round(mean(changes), 2)
        for sector, changes in sector_map.items()
    }

    return {
        "gainers": gainers,
        "losers": losers,
        "most_active": most_active,
        "market_breadth": {
            "advancers": advancers,
            "decliners": decliners
        },
        "top_bullish": bullish,
        "top_bearish": bearish,
        "sector_performance": sector_performance
    }


# ==============================
# REFRESH CONTROL
# ==============================

def refresh_if_needed():
    global last_update

    if last_update is None:
        should_refresh = True
    else:
        diff = (datetime.utcnow() - last_update).total_seconds()
        should_refresh = diff > REFRESH_INTERVAL

    if should_refresh:
        print("Refreshing full market engine...")
        stocks = scrape_tradingview()
        scrape_masi()
        scrape_news()
        compute_market_analytics(stocks)
        last_update = datetime.utcnow()


# ==============================
# ROUTES
# ==============================

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/api/all")
def api_all():
    refresh_if_needed()

    analytics = compute_market_analytics(stocks_cache)

    return jsonify({
        "stocks": stocks_cache,
        "news": news_cache,
        "masi": masi_cache,
        "market_status": get_market_status(),
        "analytics": analytics,
        "last_update": last_update
    })


# ==============================
# ENTRYPOINT
# ==============================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
