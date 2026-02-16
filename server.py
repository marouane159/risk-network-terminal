#!/usr/bin/env python3

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import requests
import xml.etree.ElementTree as ET
import os
import re
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
import json

app = Flask(__name__)
CORS(app)

# -----------------------
# GLOBAL CACHE
# -----------------------
stocks_cache = []
news_cache = []
hespress_news_cache = []
masi_cache = {}
macro_cache = {}
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
# SCRAPE TRADINGVIEW - STOCKS
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
            "Recommend.All",
            "volume"  # Added volume column
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
            volume = d[7] if len(d) > 7 else 0

            stocks.append({
                "symbol": d[0],
                "sector": d[1] if d[1] else "—",
                "capital": f"{round(d[4] / 1_000_000_000, 2)}B MAD" if d[4] else "—",
                "price": float(d[2]) if d[2] else 0,
                "change": float(d[3]) if d[3] else 0,
                "pe": float(pe_value) if pe_value else None,
                "rating": convert_rating(recommendation),
                "has_live_data": True,
                "volume": int(volume) if volume else 0
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
# MASI - BMCE CAPITAL BOURSE
# -----------------------
def scrape_masi():
    global masi_cache

    url = "https://www.bmcecapitalbourse.com/bkbbourse/details/1356351,102,608#Tab0"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.bmcecapitalbourse.com/",
        "Connection": "keep-alive",
    }

    try:
        session = requests.Session()
        session.get("https://www.bmcecapitalbourse.com/bkbbourse/", headers=headers, timeout=10)
        r = session.get(url, headers=headers, timeout=30)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")

        price = 0.0
        change_percent = 0.0

        # Method 1: Look for the specific structure <span class="price"><span class="stale">VALUE</span></span>
        price_span = soup.find("span", class_="price")
        if price_span:
            stale_span = price_span.find("span", class_="stale")
            if stale_span:
                try:
                    price_text = stale_span.get_text(strip=True)
                    price_text = price_text.replace(" ", "").replace(" ", "").replace(" ", "").replace(",", ".")
                    price = float(price_text)
                except (ValueError, AttributeError) as e:
                    print(f"Error parsing price method 1: {e}")

        # Method 2: Look for any span with class "stale" containing numbers
        if price == 0:
            stale_spans = soup.find_all("span", class_="stale")
            for span in stale_spans:
                try:
                    text = span.get_text(strip=True)
                    if re.match(r'\d{1,5}[\s  ]?\d{3},\d{2}', text):
                        price_text = text.replace(" ", "").replace(" ", "").replace(" ", "").replace(",", ".")
                        price = float(price_text)
                        break
                except:
                    pass

        # Method 3: Look for any element containing MASI-like number (10000-20000 range)
        if price == 0:
            text = soup.get_text()
            matches = re.findall(r'(\d{2}\s?\d{3},\d{2})', text)
            for match in matches:
                try:
                    val = float(match.replace(" ", "").replace(",", "."))
                    if 10000 <= val <= 20000:
                        price = val
                        break
                except:
                    pass

        # Try to find change percentage
        change_matches = re.findall(r'([+-]?\d+[,.]\d+)%', r.text)
        if change_matches:
            try:
                change_str = change_matches[0].replace(",", ".")
                change_percent = float(change_str)
            except:
                pass

        change_elem = soup.find("span", class_=re.compile("change|variation", re.I))
        if change_elem and change_percent == 0:
            try:
                change_text = change_elem.get_text(strip=True).replace(",", ".").replace("+", "").replace("%", "")
                change_percent = float(change_text)
            except:
                pass

        masi_cache = {
            "symbol": "MASI",
            "price": price,
            "change_percent": change_percent
        }

        return masi_cache

    except Exception as e:
        print(f"MASI fetch error: {e}")
        if masi_cache and masi_cache.get("price", 0) > 0:
            return masi_cache
        return {
            "symbol": "MASI",
            "price": 0,
            "change_percent": 0
        }


# -----------------------
# MACRO INDICATORS - TRADINGVIEW ECONOMICS
# -----------------------
def scrape_macro_indicators():
    """
    Fetch Morocco macroeconomic indicators from TradingView economics API
    """
    global macro_cache
    
    indicators = [
        ("GDP", "MAGDP", "GDP"),
        ("GDP Growth", "MAGDPQQ", "GDP Growth"),
        ("Inflation Rate", "MAIR", "Inflation Rate"),
        ("Unemployment Rate", "MAUR", "Unemployment Rate"),
        ("Interest Rate", "MAINTR", "Interest Rate"),
        ("Balance of Trade", "MABOP", "Balance of Trade"),
        ("Government Debt to GDP", "MAGDPDT", "Government Debt to GDP"),
        ("Population", "MAPOP", "Population")
    ]
    
    results = {}
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.tradingview.com/"
    }
    
    for name, symbol, category in indicators:
        try:
            url = f"https://economics-api.tradingview.com/history?symbol=ECONOMICS:{symbol}&resolution=1M&from=0&to=9999999999"
            r = requests.get(url, headers=headers, timeout=10)
            
            if r.status_code == 200:
                data = r.json()
                if data and 'c' in data and len(data['c']) > 0:
                    # Get the latest value
                    latest_value = data['c'][-1]
                    prev_value = data['c'][-2] if len(data['c']) > 1 else latest_value
                    
                    # Format based on indicator type
                    if "GDP" in name and "Growth" not in name:
                        # GDP in billions
                        formatted = f"{latest_value/1000000000:.2f}B"
                    elif "Population" in name:
                        formatted = f"{latest_value/1000000:.2f}M"
                    elif "Rate" in name or "Debt" in name:
                        formatted = f"{latest_value:.2f}%"
                    else:
                        formatted = f"{latest_value:.2f}"
                    
                    change = latest_value - prev_value
                    change_pct = (change / prev_value * 100) if prev_value != 0 else 0
                    
                    results[name] = {
                        "value": formatted,
                        "raw": latest_value,
                        "change": change,
                        "change_pct": change_pct,
                        "category": category
                    }
        except Exception as e:
            print(f"Error fetching {name}: {e}")
            continue
    
    # Fallback values if API fails
    if not results:
        results = {
            "GDP": {"value": "154.43B", "raw": 154430000000, "change": 0, "change_pct": 0, "category": "GDP"},
            "GDP Growth": {"value": "2.80%", "raw": 2.8, "change": 0, "change_pct": 0, "category": "GDP Growth"},
            "Inflation Rate": {"value": "0.60%", "raw": 0.6, "change": 0, "change_pct": 0, "category": "Inflation Rate"},
            "Unemployment Rate": {"value": "13.10%", "raw": 13.1, "change": 0, "change_pct": 0, "category": "Unemployment Rate"},
            "Interest Rate": {"value": "2.75%", "raw": 2.75, "change": 0, "change_pct": 0, "category": "Interest Rate"},
            "Balance of Trade": {"value": "-3.20B", "raw": -3200000000, "change": 0, "change_pct": 0, "category": "Balance of Trade"},
            "Government Debt to GDP": {"value": "68.50%", "raw": 68.5, "change": 0, "change_pct": 0, "category": "Government Debt to GDP"},
            "Population": {"value": "37.50M", "raw": 37500000, "change": 0, "change_pct": 0, "category": "Population"}
        }
    
    macro_cache = results
    return results


# -----------------------
# NEWS - RISK.MA
# -----------------------
def scrape_news():
    global news_cache

    url = "https://risk.ma/feed/"

    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()

        news = []
        root = ET.fromstring(r.content)
        items = root.findall(".//item")

        for item in items[:10]:
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
        scrape_hespress_economy()
        scrape_macro_indicators()
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

    # Calculate top and worst performers
    performers = {"top": [], "worst": []}
    if stocks_cache:
        # Sort by change percentage
        sorted_stocks = sorted(stocks_cache, key=lambda x: x.get('change', 0), reverse=True)
        performers["top"] = sorted_stocks[:5]
        performers["worst"] = sorted_stocks[-5:][::-1]  # Reverse to show worst first

    return jsonify({
        "stocks": stocks_cache,
        "news": news_cache,
        "hespress_news": hespress_news_cache,
        "masi": masi_cache,
        "macro": macro_cache,
        "market_status": get_market_status(),
        "last_update": last_update.isoformat() if last_update else None,
        "performers": performers
    })


# -----------------------
# RENDER ENTRYPOINT
# -----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
