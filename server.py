#!/usr/bin/env python3

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import os

app = Flask(__name__)
CORS(app)

# =========================================
# GLOBAL CACHE
# =========================================

stocks_cache = []
market_summary_cache = {}
news_cache = []
masi_cache = {}
last_update = None

REFRESH_INTERVAL = 600  # 10 minutes


# =========================================
# MARKET STATUS (Morocco)
# =========================================

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


# =========================================
# RATING CONVERTER
# =========================================

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


# =========================================
# TRADINGVIEW MOROCCO SCANNER
# =========================================

def scrape_tradingview():
    global stocks_cache, market_summary_cache

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

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)

        if r.status_code != 200:
            print("TradingView API error:", r.status_code)
            return

        data = r.json()
        stocks = []

        for item in data.get("data", []):
            d = item.get("d", [])

            volume = d[7] if d[7] else 0

            stocks.append({
                "symbol": d[0],
                "sector": d[1] if d[1] else "—",
                "capital": round(d[4] / 1_000_000_000, 2) if d[4] else 0,
                "price": float(d[2]) if d[2] else 0,
                "change": float(d[3]) if d[3] else 0,
                "pe": round(d[5], 2) if d[5] else None,
                "rating": convert_rating(d[6]),
                "volume_raw": volume,
                "volume": round(volume / 1_000_000, 2) if volume else 0,
                "dividend_yield": round(d[8], 2) if d[8] else None,
                "high_52w": round(d[9], 2) if d[9] else None,
                "low_52w": round(d[10], 2) if d[10] else None,
                "has_live_data": True
            })

        # ===== MARKET STATISTICS =====
        advancers = len([s for s in stocks if s["change"] > 0])
        decliners = len([s for s in stocks if s["change"] < 0])
        neutral = len([s for s in stocks if s["change"] == 0])

        # ===== TOP GAINERS / LOSERS =====
        top_gainers = sorted(stocks, key=lambda x: x["change"], reverse=True)[:5]
        top_losers = sorted(stocks, key=lambda x: x["change"])[:5]
        top_volume = sorted(stocks, key=lambda x: x["volume_raw"], reverse=True)[:5]

        # ===== SECTOR BREAKDOWN =====
        sector_breakdown = {}
        for s in stocks:
            sector = s["sector"]
            sector_breakdown.setdefault(sector, 0)
            sector_breakdown[sector] += 1

        # ===== VOLUME SPIKES (top 10% volume) =====
        volumes = [s["volume_raw"] for s in stocks if s["volume_raw"] > 0]
        avg_volume = sum(volumes) / len(volumes) if volumes else 0

        volume_spikes = [
            s for s in stocks
            if s["volume_raw"] > avg_volume * 2
        ]

        stocks_cache = stocks

        market_summary_cache = {
            "advancers": advancers,
            "decliners": decliners,
            "neutral": neutral,
            "top_gainers": top_gainers,
            "top_losers": top_losers,
            "top_volume": top_volume,
            "volume_spikes": volume_spikes[:5],
            "sector_breakdown": sector_breakdown
        }

    except Exception as e:
        print("TradingView fetch error:", e)


# =========================================
# MASI FROM TRADINGVIEW
# =========================================

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

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        data = r.json()

        if "data" in data and len(data["data"]) > 0:
            d = data["data"][0]["d"]
            masi_cache = {
                "symbol": "MASI",
                "price": float(d[0]),
                "change_percent": float(d[1])
            }

    except Exception as e:
        print("MASI fetch error:", e)


# =========================================
# NEWS
# =========================================

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


# =========================================
# AUTO REFRESH
# =========================================

def refresh_if_needed():
    global last_update

    if last_update is None:
        should_refresh = True
    else:
        diff = (datetime.utcnow() - last_update).total_seconds()
        should_refresh = diff > REFRESH_INTERVAL

    if should_refresh:
        print("Refreshing full market system...")
        scrape_tradingview()
        scrape_masi()
        scrape_news()
        last_update = datetime.utcnow()


# =========================================
# ROUTES
# =========================================

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/api/all")
def api_all():
    refresh_if_needed()

    return jsonify({
        "stocks": stocks_cache,
        "market_summary": market_summary_cache,
        "news": news_cache,
        "masi": masi_cache,
        "market_status": get_market_status(),
        "last_update": last_update
    })


# =========================================
# ENTRYPOINT (Render Compatible)
# =========================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
