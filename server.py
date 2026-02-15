#!/usr/bin/env python3
"""
RISK Network Terminal - Backend Server
Uses TradingView undocumented API for data
Auto-refreshes every 10 minutes
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import requests
import xml.etree.ElementTree as ET
import json
import os
import threading
import time
from datetime import datetime, timezone, timedelta

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Data storage
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# Cached data
stocks_cache = []
news_cache = []
masi_cache = {"symbol": "MASI", "name": "Morocco All Shares Index", "price": 0.0, "change_percent": 0.0, "currency": "MAD", "last_update": datetime.now().isoformat()}
last_update = None

def get_market_status():
    """Check if Moroccan stock market is open"""
    now = datetime.now(timezone(timedelta(hours=0)))  # UTC, adjust if needed
    weekday = now.weekday()
    hour = now.hour
    minute = now.minute
    current_time = hour * 60 + minute
    
    open_time = 9 * 60 + 30
    close_time = 15 * 60 + 40
    
    is_weekday = weekday < 5
    is_open_hours = open_time <= current_time <= close_time
    
    return {
        "is_open": is_weekday and is_open_hours,
        "open_time": "09:30",
        "close_time": "15:40",
        "current_time": now.strftime("%H:%M"),
        "day_of_week": weekday,
        "next_open": get_next_market_open(now)
    }

def get_next_market_open(current_time):
    """Calculate next market open time"""
    weekday = current_time.weekday()
    hour = current_time.hour
    minute = current_time.minute
    current_minutes = hour * 60 + minute
    
    if weekday >= 5:
        days_until_monday = (7 - weekday) % 7
        next_open = current_time + timedelta(days=days_until_monday)
        return next_open.replace(hour=9, minute=30, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")
    elif current_minutes > close_time:
        next_open = current_time + timedelta(days=1)
        while next_open.weekday() >= 5:
            next_open += timedelta(days=1)
        return next_open.replace(hour=9, minute=30, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")
    elif current_minutes < open_time:
        return current_time.replace(hour=9, minute=30, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")
    else:
        return "Market is open"

def fetch_masi():
    """Fetch MASI index using TradingView API"""
    global masi_cache
    print(f"[{datetime.now()}] Fetching MASI...")
    try:
        url = "https://scanner.tradingview.com/morocco/scan"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Content-Type': 'application/json'
        }
        payload = {
            "symbols": {"tickers": ["CSEMA:MASI"], "query": {"types": []}},
            "columns": ["close", "change"]
        }
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get('data'):
                values = data['data'][0]['d']
                price = float(values[0]) if values[0] is not None else masi_cache['price']
                change_percent = float(values[1]) if values[1] is not None else masi_cache['change_percent']
                masi_cache = {
                    "symbol": "MASI",
                    "name": "Morocco All Shares Index",
                    "price": price,
                    "change_percent": change_percent,
                    "currency": "MAD",
                    "last_update": datetime.now().isoformat()
                }
                print(f"MASI: {price} ({change_percent}%)")
            else:
                print("No data in response")
        else:
            print(f"Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Error fetching MASI: {e}")

def fetch_stocks():
    """Fetch all stocks using TradingView API"""
    global stocks_cache
    print(f"[{datetime.now()}] Fetching stocks...")
    try:
        url = "https://scanner.tradingview.com/morocco/scan"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Content-Type': 'application/json'
        }
        payload = {
            "filter": [{"left": "type", "operation": "equal", "right": "stock"}],
            "options": {"lang": "en"},
            "columns": ["symbol", "market_cap_basic", "sector", "close", "change", "PE", "Recommend.All"],
            "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
            "range": [0, 200]
        }
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            stocks = []
            for item in data.get('data', []):
                values = item['d']
                symbol = values[0] if values[0] else '—'
                market_cap = values[1] if values[1] is not None else '—'
                sector = values[2] if values[2] else '—'
                price = values[3] if values[3] is not None else '—'
                change = values[4] if values[4] is not None else '—'
                pe = values[5] if values[5] is not None else '—'
                recommend = values[6] if values[6] is not None else '—'
                
                # Map recommend to text
                if isinstance(recommend, (int, float)):
                    if recommend < 1.5:
                        rating = "Strong Buy"
                    elif recommend < 2.5:
                        rating = "Buy"
                    elif recommend < 3.5:
                        rating = "Hold"
                    elif recommend < 4.5:
                        rating = "Sell"
                    else:
                        rating = "Strong Sell"
                else:
                    rating = '—'
                
                stocks.append({
                    "symbol": symbol,
                    "market_cap": market_cap,
                    "sector": sector,
                    "price": price,
                    "change": change,
                    "pe": pe,
                    "rating": rating
                })
            stocks_cache = stocks
            print(f"Fetched {len(stocks)} stocks")
        else:
            print(f"Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Error fetching stocks: {e}")

def fetch_news():
    """Fetch RSS news from Medias24"""
    global news_cache
    print(f"[{datetime.now()}] Fetching news...")
    try:
        url = "https://medias24.com/categorie/leboursier/actus/feed/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            items = []
            for item in root.findall('./channel/item')[:6]:
                title = item.find('title').text if item.find('title') is not None else ''
                link = item.find('link').text if item.find('link') is not None else ''
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ''
                items.append({"title": title, "link": link, "pub_date": pub_date})
            news_cache = items
            print(f"Fetched {len(items)} news")
        else:
            print(f"Error {response.status_code}")
    except Exception as e:
        print(f"Error fetching news: {e}")

def refresh_data():
    """Refresh all data"""
    global last_update
    while True:
        fetch_masi()
        fetch_stocks()
        fetch_news()
        last_update = datetime.now().isoformat()
        time.sleep(600)  # 10 minutes

# Start refresh thread
threading.Thread(target=refresh_data, daemon=True).start()

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

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
    return jsonify({"last_update": last_update})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
