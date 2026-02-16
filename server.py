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

stocks_cache = []
news_cache = []
masi_cache = {}
last_update = None

REFRESH_INTERVAL = 600


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
# TRADINGVIEW API
# -----------------------
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
            "Recommend.All"
        ]
    }

    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        data = r.json()

        stocks = []

        for item in data.get("data", []):
            d = item.get("d", [])

            stocks.append({
                "symbol": d[0],
                "sector": d[1] if d[1] else "—",
                "capital": f"{round(d[4] / 1_000_000_000, 2)}B MAD" if d[4] else "—",
                "price": float(d[2]) if d[2] else 0,
                "change": float(d[3]) if d[3] else 0,
                "pe": float(d[5]) if d[5] else None,
                "rating": convert_rating(d[6]),
            })

        stocks_cache = stocks
        return stocks

    except Exception as e:
        print("TradingView error:", e)
        return stocks_cache


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


# -----------------------
# MASI (REAL CHANGE %)
# -----------------------
def scrape_masi():
    global masi_cache

    url = "https://www.investing.com/indices/masi"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(r.text, "html.parser")

        price_div = soup.find("div", class_=re.compile("instrument-price"))
        change_span = soup.find("span", class_=re.compile("instrument-price_change-percent"))

        price = 0
        change = 0

        if price_div:
            price = float(price_div.text.replace(",", "").strip())

        if change_span:
            change_text = change_span.text.replace("%", "").replace("(", "").replace(")", "")
            change = float(change_text)

        masi_cache = {
            "symbol": "MASI",
            "price": price,
            "change_percent": change
        }

    except Exception as e:
        print("MASI error:", e)

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

        for item in items[:6]:
            title = item.find("title").text if item.find("title") else ""
            link = item.find("link").text if item.find("link") else ""

            news.append({"title": title, "link": link})

    news_cache = news
    return news


# -----------------------
# REFRESH
# -----------------------
def refresh_if_needed():
    global last_update

    if last_update is None:
        should_refresh = True
    else:
        diff = (datetime.utcnow() - last_update).total_seconds()
        should_refresh = diff > REFRESH_INTERVAL

    if should_refresh:
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

    # TOP GAINERS / LOSERS
    sorted_stocks = sorted(stocks_cache, key=lambda x: x["change"], reverse=True)

    return jsonify({
        "stocks": stocks_cache,
        "top_gainers": sorted_stocks[:5],
        "top_losers": sorted_stocks[-5:],
        "news": news_cache,
        "masi": masi_cache,
        "market_status": get_market_status(),
        "last_update": last_update
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
