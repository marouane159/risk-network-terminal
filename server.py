#!/usr/bin/env python3
"""
RISK Network Terminal - Backend Server
Scrapes TradingView Morocco + MASI using Playwright (JS rendering)
Auto-refreshes every 10 minutes
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import requests
import xml.etree.ElementTree as ET
import os
import threading
import time
import re
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

# ────────────────────────────────────────────────
# Playwright imports (must be installed + browsers)
# ────────────────────────────────────────────────
from playwright.sync_api import sync_playwright

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Data storage
ALL_STOCKS = {
    "TGC": {"name": "TRAVAUX GENERAUX DE CONSTRUCTIONS", "sector": "Construction"},
    "TMA": {"name": "TOTALENERGIES MARKETING", "sector": "Énergie"},
    "TQM": {"name": "TAQA MOROCCO", "sector": "Énergie"},
    "NKL": {"name": "ENNAKL SA", "sector": "Transport"},
    "LHM": {"name": "LAFARGEHOLCIM", "sector": "Construction"},
    "UMR": {"name": "UNIMER", "sector": "Agroalimentaire"},
    "WAA": {"name": "WAFA ASSURANCE", "sector": "Assurance"},
    "ZDJ": {"name": "ZELLIDJA S.A", "sector": "Mines"},
    "MSA": {"name": "SODEP MARSA", "sector": "Transport"},
    "RDS": {"name": "RESIDENCE DAR SAADA", "sector": "Immobilier"},
    "CSR": {"name": "COSUMAR", "sector": "Agroalimentaire"},
    "CFG": {"name": "CFG BANK", "sector": "Banque"},
    "CMG": {"name": "CMGP CAS", "sector": "Agriculture"},
    "HPS": {"name": "HPS", "sector": "Technologie"},
    "S2M": {"name": "S2M", "sector": "Technologie"},
    "RIS": {"name": "RISMA", "sector": "Hôtellerie"},
    "DHO": {"name": "DELTA HOLDING", "sector": "Industrie"},
    "DWY": {"name": "DISWAY", "sector": "Distribution"},
    "SNA": {"name": "STOKVIS NORD AFRIQUE", "sector": "Distribution"},
    "SNP": {"name": "SNEP", "sector": "Industrie"},
    "STR": {"name": "STROC INDUSTRIE", "sector": "Industrie"},
    "INV": {"name": "INVOLYS", "sector": "Technologie"},
    "MIC": {"name": "MICRODATA", "sector": "Technologie"},
    "DYT": {"name": "DISTY TECHNOLOGIES", "sector": "Distribution"},
    "ADH": {"name": "DOUJA PROM ADDOHA", "sector": "Immobilier"},
    "IMO": {"name": "IMMORENT INVEST", "sector": "Immobilier"},
    "ADI": {"name": "ALLIANCES", "sector": "Divers"},
    "AFI": {"name": "AFRIC INDUSTRIES", "sector": "Industrie"},
    "AFM": {"name": "AFMA", "sector": "Finance"},
    "AKT": {"name": "AKDITAL S.A", "sector": "Santé"},
    "ALM": {"name": "ALUMINIUM DU MAROC", "sector": "Matériaux"},
    "ARD": {"name": "ARADEI CAPITAL", "sector": "Immobilier"},
    "ATH": {"name": "AUTO HALL", "sector": "Automobile"},
    "ATL": {"name": "ATLANTASANAD", "sector": "Assurance"},
    "ATW": {"name": "ATTIJARIWAFA BANK", "sector": "Banque"},
    "BAL": {"name": "BALIMA", "sector": "Distribution"},
    "BCP": {"name": "BANQUE CENTRALE POPULAIRE", "sector": "Banque"},
    "CRS": {"name": "CARTIER SAADA", "sector": "Distribution"},
    "CIH": {"name": "CREDIT IMMOBILIER ET HOTELIER", "sector": "Banque"},
    "CMT": {"name": "CIMENTS DU MAROC", "sector": "Matériaux"},
    "COL": {"name": "COLORADO", "sector": "Distribution"},
    "CTM": {"name": "COMPAGNIE DE TRANSPORTS AU MAROC", "sector": "Transport"},
    "DIM": {"name": "DELATTRE LEVIVIER MAROC", "sector": "Industrie"},
    "DRI": {"name": "DARI COUSPATE", "sector": "Agroalimentaire"},
    "EQD": {"name": "EQDOM", "sector": "Immobilier"},
    "FBR": {"name": "FENIE BROSSETTE", "sector": "Distribution"},
    "IAM": {"name": "MAROC TELECOM", "sector": "Télécom"},
    "INM": {"name": "INDUSTRIE DU MAROC", "sector": "Industrie"},
    "JET": {"name": "JET CONTRACTORS", "sector": "Construction"},
    "LES": {"name": "LESIEUR CRISTAL", "sector": "Agroalimentaire"},
    "MOX": {"name": "MAGHREB OXYGENE", "sector": "Industrie"},
    "MNG": {"name": "MANAGEM", "sector": "Mines"},
    "MUT": {"name": "MUTANDIS", "sector": "Agroalimentaire"},
    "SID": {"name": "SONASID", "sector": "Sidérurgie"},
    "SOT": {"name": "SOTHEMA", "sector": "Pharmacie"},
    "SRM": {"name": "REALISATIONS MECANIQUES", "sector": "Industrie"},
    "MDP": {"name": "MED PAPER", "sector": "Industrie"},
    "VCN": {"name": "VICENNE", "sector": "Santé"},
    "SMI": {"name": "SMI", "sector": "Finance"},
    "CDM": {"name": "Crédit du Maroc", "sector": "Banque"},
    "GTM": {"name": "SGTM", "sector": "BTP"},
    "CAP": {"name": "Cash Plus", "sector": "Finance"}
}

# Cached data
stocks_cache = []
news_cache = []
masi_cache = {
    "symbol": "MASI",
    "name": "Morocco All Shares Index",
    "price": 18573.12,
    "change": 0.0,
    "change_percent": 0.0,
    "currency": "MAD",
    "last_update": datetime.now().isoformat()
}
last_update = None

def get_market_status():
    now = datetime.now(timezone(timedelta(hours=1)))  # Morocco ≈ UTC+1
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
    weekday = current_time.weekday()
    hour = current_time.hour
    minute = current_time.minute
    current_minutes = hour * 60 + minute

    if weekday >= 5:
        days_until_monday = 7 - weekday
        next_open = current_time + timedelta(days=days_until_monday)
        return next_open.replace(hour=9, minute=30, second=0).strftime("%Y-%m-%d %H:%M")
    elif current_minutes > 15 * 60 + 40:
        next_open = current_time + timedelta(days=1)
        if next_open.weekday() >= 5:
            days_until_monday = 7 - next_open.weekday()
            next_open = next_open + timedelta(days=days_until_monday)
        return next_open.replace(hour=9, minute=30, second=0).strftime("%Y-%m-%d %H:%M")
    else:
        return "Today 09:30"

def scrape_masi_index():
    global masi_cache
    print(f"[{datetime.now()}] Scraping MASI index...")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            page.goto("https://fr.tradingview.com/symbols/CSEMA-MASI/", timeout=60000)
            page.wait_for_load_state("networkidle", timeout=45000)
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, 'html.parser')

        price_elem = (
            soup.find('span', class_='last-zoF9r75I') or
            soup.find('span', class_=lambda x: x and 'last-' in str(x)) or
            soup.find('span', {'data-qa-id': 'symbol-last-value'})
        )

        price = None
        if price_elem:
            price_text = price_elem.get_text().strip()
            price_text = price_text.replace('\u202f', '').replace(' ', '').replace('\xa0', '').replace(',', '.')
            try:
                price = float(price_text)
                print(f"Found MASI price: {price}")
            except ValueError:
                print(f"Could not parse price: {price_text}")

        if price is None:
            for span in soup.find_all('span'):
                text = span.get_text().strip()
                if re.match(r'^[\d\s\u202f,\.]+$', text):
                    clean = text.replace('\u202f', '').replace(' ', '').replace('\xa0', '').replace(',', '.')
                    try:
                        val = float(clean)
                        if 8000 < val < 50000:
                            price = val
                            print(f"Found MASI price (fallback): {price}")
                            break
                    except:
                        continue

        change_percent = None
        change_elem = (
            soup.find('span', class_=lambda x: x and 'change-' in str(x)) or
            soup.find('span', {'data-qa-id': 'symbol-change-percent-value'})
        )
        if change_elem:
            txt = change_elem.get_text().strip().replace('%', '').replace('+', '').replace(',', '.')
            try:
                change_percent = float(txt)
                print(f"Found change: {change_percent}%")
            except:
                pass

        masi_cache = {
            "symbol": "MASI",
            "name": "Morocco All Shares Index",
            "price": price if price else masi_cache["price"],
            "change": change_percent or 0.0,
            "change_percent": change_percent or 0.0,
            "currency": "MAD",
            "last_update": datetime.now().isoformat()
        }

        print(f"MASI → {masi_cache['price']} ({masi_cache['change_percent']}%)")
        return masi_cache

    except Exception as e:
        print(f"MASI scrape failed: {e}")
        return masi_cache

def scrape_tradingview():
    global stocks_cache, last_update
    print(f"[{datetime.now()}] Scraping TradingView Morocco stocks...")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            page.goto("https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/", timeout=90000)
            page.wait_for_load_state("networkidle", timeout=60000)
            # Give extra time for table to appear
            page.wait_for_selector("table", timeout=30000)
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, 'html.parser')
        tv_data = {}

        tables = soup.find_all('table')
        print(f"Found {len(tables)} tables")

        for table in tables:
            rows = table.find_all('tr')
            if len(rows) < 5:
                continue

            for row in rows[1:]:
                try:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) < 5:
                        continue

                    symbol_cell = cells[0].find('a') or cells[0]
                    symbol = symbol_cell.get_text().strip().upper()

                    if not symbol or symbol not in ALL_STOCKS:
                        continue

                    data = {
                        'symbol': symbol,
                        'price': 0.0,
                        'change': 0.0,
                        'capital': '—',
                        'pe': None,
                        'sector': ALL_STOCKS[symbol]['sector'],
                        'rating': '—'
                    }

                    for j, cell in enumerate(cells):
                        text = cell.get_text().strip()

                        # Price
                        if j == 1:
                            try:
                                clean = text.replace('MAD', '').replace(',', '').replace(' ', '').replace('\u202f', '').replace('\xa0', '')
                                val = float(clean)
                                if 0 < val < 10000:
                                    data['price'] = val
                            except:
                                pass

                        # Change %
                        if '%' in text:
                            try:
                                clean = text.replace('%', '').replace('(', '-').replace(')', '').replace('+', '').replace(',', '.')
                                val = float(clean)
                                if -50 < val < 50:
                                    data['change'] = val
                            except:
                                pass

                        # Market Cap
                        if any(x in text.lower() for x in ['b', 'm', 'md', 'mm', 'milliard', 'million']) and j > 2:
                            data['capital'] = text

                        # P/E
                        if j >= 5:
                            try:
                                clean = text.replace(',', '.')
                                val = float(clean)
                                if 0 < val < 200:
                                    data['pe'] = val
                            except:
                                pass

                        # Rating / Analyst
                        rating_keywords = ['buy', 'sell', 'hold', 'neutral', 'strong', 'achat', 'vente', 'conserver']
                        if any(kw in text.lower() for kw in rating_keywords) and len(text) < 25:
                            data['rating'] = text

                    tv_data[symbol] = data

                except:
                    continue

        print(f"Scraped {len(tv_data)} valid Moroccan stocks")

        # Build final list
        result = []
        for symbol, info in ALL_STOCKS.items():
            if symbol in tv_data:
                d = tv_data[symbol]
                result.append({
                    'symbol': symbol,
                    'name': info['name'],
                    'sector': d['sector'],
                    'capital': d['capital'],
                    'price': d['price'],
                    'change': d['change'],
                    'pe': d['pe'],
                    'rating': d['rating'],
                    'has_live_data': d['price'] > 0
                })
            else:
                result.append({
                    'symbol': symbol,
                    'name': info['name'],
                    'sector': info['sector'],
                    'capital': '—',
                    'price': 0.0,
                    'change': 0.0,
                    'pe': None,
                    'rating': '—',
                    'has_live_data': False
                })

        result.sort(key=lambda x: (not x['has_live_data'], x['symbol']))

        stocks_cache = result
        last_update = datetime.now().isoformat()

        live = sum(1 for r in result if r['has_live_data'])
        print(f"→ {len(result)} stocks total, {live} with live data")

        return result

    except Exception as e:
        print(f"TradingView scrape failed: {e}")
        return stocks_cache

def get_news():
    global news_cache
    try:
        url = "https://medias24.com/categorie/leboursier/actus/feed/"
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; RISKTerminal/1.0)'}
        r = requests.get(url, headers=headers, timeout=15)

        if r.status_code == 200:
            root = ET.fromstring(r.content)
            items = root.findall('.//item')

            news = []
            now = datetime.now(timezone.utc)

            for item in items[:10]:
                title = item.find('title').text or 'Sans titre'
                link = item.find('link').text or ''
                pub = item.find('pubDate').text
                cat = (item.find('category').text or 'INFO').upper()

                mins = 0
                if pub:
                    try:
                        dt = datetime.strptime(pub, '%a, %d %b %Y %H:%M:%S %z')
                        mins = int((now - dt).total_seconds() / 60)
                    except:
                        pass

                news.append({
                    'title': title,
                    'link': link,
                    'category': cat,
                    'time': max(0, mins)
                })

            news_cache = news
            return news

    except Exception as e:
        print(f"News fetch failed: {e}")

    return news_cache

def background_refresh():
    while True:
        print(f"[{datetime.now()}] Background refresh starting...")
        try:
            scrape_tradingview()
            scrape_masi_index()
            get_news()
            print(f"[{datetime.now()}] Background refresh completed")
        except Exception as e:
            print(f"Refresh error: {e}")
        time.sleep(600)

# ────────────────────────────────────────────────
# Routes
# ────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/stocks')
def api_stocks():
    return jsonify(stocks_cache or [])

@app.route('/api/news')
def api_news():
    return jsonify(news_cache or [])

@app.route('/api/masi')
def api_masi():
    return jsonify(masi_cache)

@app.route('/api/market-status')
def api_market_status():
    return jsonify(get_market_status())

@app.route('/api/all')
def api_all():
    return jsonify({
        'stocks': stocks_cache or [],
        'news': news_cache or [],
        'masi': masi_cache,
        'market_status': get_market_status(),
        'last_update': last_update
    })

@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    scrape_tradingview()
    scrape_masi_index()
    get_news()
    return jsonify({
        'success': True,
        'stocks': stocks_cache,
        'masi': masi_cache,
        'news': news_cache,
        'market_status': get_market_status(),
        'last_update': last_update
    })

if __name__ == '__main__':
    print("═" * 60)
    print("RISK Network Terminal - Starting")
    print("═" * 60)

    print("Initial data scrape...")
    scrape_tradingview()
    scrape_masi_index()
    get_news()

    threading.Thread(target=background_refresh, daemon=True).start()
    print("Auto-refresh thread started (every 10 min)")

    port = int(os.environ.get('PORT', 5000))
    print(f"Listening on port {port}")
    print("═" * 60)

    app.run(host='0.0.0.0', port=port, threaded=True)
