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

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json"
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)

        if r.status_code != 200:
            print("TradingView API error:", r.status_code)
            return stocks_cache

        data = r.json()
        stocks = []

        for item in data.get("data", []):
            d = item.get("d", [])

            pe_value = d[5]
            recommendation = d[6]

            stocks.append({
                "symbol": d[0],
                "sector": d[1] if d[1] else "—",
                "capital": f"{round(d[4] / 1_000_000_000, 2)}B MAD" if d[4] else "—",
                "price": float(d[2]) if d[2] else 0,
                "change": float(d[3]) if d[3] else 0,
                "pe": float(pe_value) if pe_value else None,
                "rating": convert_rating(recommendation),
                "has_live_data": True
            })

        stocks_cache = stocks
        return stocks_cache

    except Exception as e:
        print("TradingView fetch error:", e)
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
# MASI - FIXED VERSION
# -----------------------
def scrape_masi():
    global masi_cache

    url = "https://www.investing.com/indices/masi"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.google.com/"
    }

    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")

        price = 0.0
        change_percent = 0.0

        # Method 1: Try to find the instrument-price div
        price_div = soup.find("div", class_=re.compile("instrument-price"))
        if price_div:
            try:
                price_text = price_div.get_text(strip=True).replace(",", "").replace(" ", "")
                price = float(price_text)
            except (ValueError, AttributeError):
                pass

        # Method 2: Look for data in script tags (JSON data)
        if price == 0:
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string and "MASI" in script.string:
                    # Try to extract price from JSON-like data
                    price_match = re.search(r'"last"[:\s]+([\d.]+)', script.string)
                    if price_match:
                        try:
                            price = float(price_match.group(1))
                        except:
                            pass

                    change_match = re.search(r'"change"[:\s]+([-\d.]+)', script.string)
                    if change_match:
                        try:
                            change_percent = float(change_match.group(1))
                        except:
                            pass

                    if price > 0:
                        break

        # Method 3: Look for specific span or div with price
        if price == 0:
            # Try finding by data-test attribute or specific classes
            price_selectors = [
                '[data-test="instrument-price-last"]',
                '.last-price-value',
                '.text-5xl',
                'span[data-field="last"]'
            ]

            for selector in price_selectors:
                elem = soup.select_one(selector)
                if elem:
                    try:
                        price_text = elem.get_text(strip=True).replace(",", "")
                        price = float(price_text)
                        break
                    except:
                        pass

        # Extract change percentage if not already found
        if change_percent == 0:
            # Look for percentage change
            change_selectors = [
                '[data-test="instrument-price-change-percent"]',
                '.change-percent-value',
                'span[data-field="change_percent"]'
            ]

            for selector in change_selectors:
                elem = soup.select_one(selector)
                if elem:
                    try:
                        change_text = elem.get_text(strip=True).replace("%", "").replace("+", "")
                        change_percent = float(change_text)
                        break
                    except:
                        pass

        # If still no price, try a broader search
        if price == 0:
            # Look for any element containing a number that looks like MASI index (around 1000-15000)
            text = soup.get_text()
            matches = re.findall(r'(\d{3,5}[.,]\d{2})', text)
            for match in matches:
                try:
                    val = float(match.replace(",", ""))
                    if 1000 <= val <= 15000:  # MASI range
                        price = val
                        break
                except:
                    pass

        masi_cache = {
            "symbol": "MASI",
            "price": price,
            "change_percent": change_percent
        }

        print(f"MASI fetched: {price} ({change_percent}%)")
        return masi_cache

    except Exception as e:
        print(f"MASI fetch error: {e}")
        # Return cached data if available, otherwise empty
        if masi_cache and masi_cache.get("price", 0) > 0:
            return masi_cache
        return {
            "symbol": "MASI",
            "price": 0,
            "change_percent": 0
        }


# -----------------------
# NEWS
# -----------------------
def scrape_news():
    global news_cache

    url = "https://medias24.com/categorie/leboursier/actus/feed/"

    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()

        news = []
        root = ET.fromstring(r.content)
        items = root.findall(".//item")

        for item in items[:8]:
            title_elem = item.find("title")
            link_elem = item.find("link")

            title = title_elem.text if title_elem is not None else ""
            link = link_elem.text if link_elem is not None else ""

            news.append({
                "title": title,
                "link": link,
                "category": "BOURSE",
                "time": 0
            })

        news_cache = news
        return news_cache

    except Exception as e:
        print(f"News fetch error: {e}")
        return news_cache if news_cache else []


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
        "last_update": last_update.isoformat() if last_update else None
    })


# -----------------------
# RENDER ENTRYPOINT
# -----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
