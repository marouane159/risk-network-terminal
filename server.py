from flask import Flask, jsonify, send_from_directory, request, make_response
from flask_cors import CORS
import requests
import xml.etree.ElementTree as ET
import json
import os
import threading
import time
from datetime import datetime, timezone, timedelta

app = Flask(__name__, static_folder='.')

# Very permissive CORS – should cover GitHub Pages + local dev + everything else
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=False)

# Also add manual CORS headers as fallback (some environments ignore flask-cors)
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return response

# Data storage (in-memory)
stocks_cache = []
news_cache = []
masi_cache = {
    "symbol": "MASI",
    "name": "Morocco All Shares Index",
    "price": 0.0,
    "change_percent": 0.0,
    "currency": "MAD",
    "last_update": datetime.now(timezone.utc).isoformat()
}
last_update_time = None

def get_market_status():
    now = datetime.now(timezone.utc)
    # Casablanca is UTC+1, but many sources display local time → we use UTC logic carefully
    weekday = now.weekday()          # 0 = Monday ... 6 = Sunday
    hour = now.hour
    minute = now.minute
    current_minutes = hour * 60 + minute

    open_minutes  = 9 * 60 + 30      # 09:30
    close_minutes = 15 * 60 + 40     # 15:40

    is_weekday = weekday < 5
    is_open_hours = open_minutes <= current_minutes <= close_minutes

    status = {
        "is_open": is_weekday and is_open_hours,
        "open_time": "09:30",
        "close_time": "15:40",
        "current_utc": now.strftime("%Y-%m-%d %H:%M UTC"),
    }

    # Rough next open estimation
    if is_weekday and current_minutes < open_minutes:
        next_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    elif is_weekday and current_minutes > close_minutes:
        next_open = (now + timedelta(days=1)).replace(hour=9, minute=30, second=0, microsecond=0)
    elif weekday >= 5:
        days_to_monday = (7 - weekday) % 7 or 7
        next_open = (now + timedelta(days=days_to_monday)).replace(hour=9, minute=30, second=0, microsecond=0)
    else:
        next_open = now  # already open

    if next_open != now:
        status["next_open"] = next_open.strftime("%Y-%m-%d %H:%M UTC")
    else:
        status["next_open"] = "Market is open"

    return status

def fetch_masi():
    global masi_cache
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] Fetching MASI...")
    try:
        url = "https://scanner.tradingview.com/morocco/scan"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json",
            "Referer": "https://www.tradingview.com/"
        }
        payload = {
            "symbols": {"tickers": ["CSEMA:MASI"], "query": {"types": []}},
            "columns": ["close", "change"]
        }
        r = requests.post(url, json=payload, headers=headers, timeout=20)
        r.raise_for_status()
        data = r.json()

        if data.get("data") and len(data["data"]) > 0:
            values = data["data"][0]["d"]
            price = float(values[0]) if values[0] is not None else masi_cache["price"]
            chg   = float(values[1]) if values[1] is not None else masi_cache["change_percent"]
            masi_cache.update({
                "price": price,
                "change_percent": chg,
                "last_update": datetime.now(timezone.utc).isoformat()
            })
            print(f"MASI → {price:.2f}  ({chg:+.2f}%)")
        else:
            print("No MASI data in response")
    except Exception as e:
        print(f"MASI fetch failed: {e}")

def fetch_stocks():
    global stocks_cache
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] Fetching stocks...")
    try:
        url = "https://scanner.tradingview.com/morocco/scan"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json",
            "Referer": "https://www.tradingview.com/"
        }
        payload = {
            "filter": [{"left": "type", "operation": "equal", "right": "stock"}],
            "columns": [
                "name", "close", "change", "market_cap_basic",
                "sector", "PE", "Recommend.All"
            ],
            "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
            "range": [0, 150]
        }
        r = requests.post(url, json=payload, headers=headers, timeout=25)
        r.raise_for_status()
        data = r.json()

        stocks = []
        for row in data.get("data", []):
            d = row.get("d", [None]*7)
            rating_num = d[6] if len(d) > 6 and d[6] is not None else None
            if rating_num is not None:
                if rating_num <= 1.5:    rating = "Strong Buy"
                elif rating_num <= 2.5:  rating = "Buy"
                elif rating_num <= 3.5:  rating = "Hold"
                elif rating_num <= 4.5:  rating = "Sell"
                else:                    rating = "Strong Sell"
            else:
                rating = "—"

            stocks.append({
                "symbol":       d[0] or "—",
                "price":        float(d[1]) if d[1] is not None else "—",
                "change":       float(d[2]) if d[2] is not None else "—",
                "market_cap":   float(d[3]) if d[3] is not None else "—",
                "sector":       d[4] or "—",
                "pe":           float(d[5]) if d[5] is not None else "—",
                "rating":       rating
            })

        stocks_cache = stocks
        print(f"→ {len(stocks)} stocks loaded")
    except Exception as e:
        print(f"Stocks fetch failed: {e}")

def fetch_news():
    global news_cache
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] Fetching Medias24 news...")
    try:
        url = "https://medias24.com/categorie/leboursier/actus/feed/"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        items = []
        for item in list(root.findall("./channel/item"))[:7]:
            title   = item.find("title").text if item.find("title") is not None else ""
            link    = item.find("link").text if item.find("link") is not None else ""
            pubDate = item.find("pubDate").text if item.find("pubDate") is not None else ""
            items.append({"title": title, "link": link, "pub_date": pubDate})
        news_cache = items
        print(f"→ {len(items)} news items")
    except Exception as e:
        print(f"News fetch failed: {e}")

def background_refresh():
    while True:
        fetch_masi()
        fetch_stocks()
        fetch_news()
        global last_update_time
        last_update_time = datetime.now(timezone.utc).isoformat()
        time.sleep(600)  # 10 minutes

# Start background thread
threading.Thread(target=background_refresh, daemon=True).start()

# ────────────────────────────────────────────────
#                 ROUTES
# ────────────────────────────────────────────────

@app.route('/')
def serve_index():
    if os.path.exists("index.html"):
        return send_from_directory('.', "index.html")
    return "index.html not found – please place it in the same directory as server.py", 404

@app.route('/api/masi')
def api_masi():
    return jsonify(masi_cache)

@app.route('/api/stocks')
def api_stocks():
    return jsonify(stocks_cache)

@app.route('/api/news')
def api_news():
    return jsonify(news_cache)

@app.route('/api/market_status')
def api_market_status():
    return jsonify(get_market_status())

@app.route('/api/last_update')
def api_last_update():
    return jsonify({"last_update": last_update_time})

@app.route('/health')
def health():
    return jsonify({
        "status": "ok",
        "stocks_count": len(stocks_cache),
        "news_count": len(news_cache),
        "masi_price": masi_cache.get("price"),
        "last_update": last_update_time
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
