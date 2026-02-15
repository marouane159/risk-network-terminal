#!/usr/bin/env python3
"""
RISK Network Terminal - Backend Server
Scrapes Investing.com for MASI index + components
Auto-refreshes every 10 minutes
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import requests
import xml.etree.ElementTree as ET
import os
import threading
import time
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
import re

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ────────────────────────────────────────────────
# Your Moroccan stocks database (name used for matching)
# ────────────────────────────────────────────────
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
    hour, minute = now.hour, now.minute
    current_minutes = hour * 60 + minute

    open_min = 9 * 60 + 30
    close_min = 15 * 60 + 40

    is_open = weekday < 5 and open_min <= current_minutes <= close_min

    return {
        "is_open": is_open,
        "open_time": "09:30",
        "close_time": "15:40",
        "current_time": now.strftime("%H:%M"),
        "day_of_week": weekday,
        "next_open": get_next_market_open(now)
    }

def get_next_market_open(current):
    # same as before...
    weekday = current.weekday()
    current_min = current.hour * 60 + current.minute

    if weekday >= 5:
        days_to_monday = 7 - weekday
        next_day = current + timedelta(days=days_to_monday)
    elif current_min > 15*60 + 40:
        next_day = current + timedelta(days=1)
        if next_day.weekday() >= 5:
            next_day += timedelta(days=7 - next_day.weekday())
    else:
        return "Today 09:30"

    return next_day.replace(hour=9, minute=30, second=0).strftime("%Y-%m-%d %H:%M")

def clean_number(text):
    """Handle French/Moroccan formats: 18 573,12 → 18573.12"""
    text = re.sub(r'[\s\xa0\u202f]', '', text.strip())
    text = text.replace(',', '.')
    try:
        return float(text)
    except:
        return None

def scrape_masi_index():
    global masi_cache
    print(f"[{datetime.now()}] Scraping MASI from investing.com...")

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        url = "https://www.investing.com/indices/masi"
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')

        # Look for price/change block - often in a div with price and change together
        price_block = soup.find(string=re.compile(r'[\d\s,.]+.*[-+].*%'))
        if not price_block:
            price_block = soup.find('div', class_=lambda c: c and 'instrument-price' in c) or \
                          soup.find('span', class_=lambda c: c and ('instrument-price' in c or 'last' in c))

        price, change_abs, change_pct = None, 0.0, 0.0

        if price_block:
            text = price_block.get_text(strip=True)
            # Example: "18,573.12 -72.31 (-0.39%)"
            match = re.search(r'([\d\s,.]+)\s*([-+][\d\s,.]+)\s*\(([-+][\d,.]+%)\)', text)
            if match:
                price_str, change_abs_str, change_pct_str = match.groups()
                price = clean_number(price_str)
                change_abs = clean_number(change_abs_str) or 0.0
                change_pct = clean_number(change_pct_str.replace('%', '')) or 0.0
                print(f"Parsed MASI: {price} | {change_abs} ({change_pct}%)")

        if price is None:
            # Fallback: find any large number in ~18000 range
            for span in soup.find_all(['span', 'div']):
                t = span.get_text(strip=True)
                val = clean_number(t)
                if val and 15000 < val < 25000:
                    price = val
                    print(f"Fallback MASI price: {price}")
                    break

        masi_cache.update({
            "price": price if price else masi_cache["price"],
            "change": change_abs,
            "change_percent": change_pct,
            "last_update": datetime.now().isoformat()
        })

        print(f"MASI updated: {masi_cache['price']} ({masi_cache['change_percent']}%)")
        return masi_cache

    except Exception as e:
        print(f"MASI scrape error: {e}")
        return masi_cache

def scrape_masi_components():
    global stocks_cache, last_update
    print(f"[{datetime.now()}] Scraping MASI components from investing.com...")

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        url = "https://www.investing.com/indices/masi-components"
        resp = requests.get(url, headers=headers, timeout=25)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')

        # Find the components table - usually has many rows, class genTbl or cross_rates
        table = None
        for t in soup.find_all('table'):
            rows = t.find_all('tr')
            if len(rows) > 20:  # arbitrary but > most other tables
                table = t
                break

        if not table:
            print("No suitable table found")
            return stocks_cache

        tv_data = {}
        name_to_symbol = {info['name'].lower(): sym for sym, info in ALL_STOCKS.items()}

        for row in table.find_all('tr')[1:]:  # skip header
            cells = row.find_all('td')
            if len(cells) < 6:
                continue

            name_cell = cells[0].get_text(strip=True).lower()
            if not name_cell:
                continue

            # Match name (partial, case-insensitive)
            matched_symbol = None
            for full_name_lower, sym in name_to_symbol.items():
                if full_name_lower in name_cell or name_cell in full_name_lower:
                    matched_symbol = sym
                    break

            if not matched_symbol:
                continue

            price_str = cells[2].get_text(strip=True)   # Last
            chg_pct_str = cells[5].get_text(strip=True) # Chg. %

            price = clean_number(price_str)
            change_pct = clean_number(chg_pct_str.replace('%', '')) if '%' in chg_pct_str else None

            tv_data[matched_symbol] = {
                'symbol': matched_symbol,
                'price': price or 0.0,
                'change': change_pct or 0.0,
                'capital': '—',
                'pe': None,
                'sector': ALL_STOCKS[matched_symbol]['sector'],
                'rating': '—'
            }

        print(f"Matched {len(tv_data)} stocks")

        # Build final result (same as before)
        result = []
        for symbol, info in ALL_STOCKS.items():
            d = tv_data.get(symbol, {})
            result.append({
                'symbol': symbol,
                'name': info['name'],
                'sector': info['sector'],
                'capital': d.get('capital', '—'),
                'price': d.get('price', 0.0),
                'change': d.get('change', 0.0),
                'pe': d.get('pe'),
                'rating': d.get('rating', '—'),
                'has_live_data': d.get('price', 0) > 0
            })

        result.sort(key=lambda x: (not x['has_live_data'], x['symbol']))

        stocks_cache = result
        last_update = datetime.now().isoformat()

        live = sum(1 for r in result if r['has_live_data'])
        print(f"→ {len(result)} total, {live} live")

        return result

    except Exception as e:
        print(f"Components scrape error: {e}")
        return stocks_cache

def get_news():
    # unchanged - your original RSS function
    global news_cache
    try:
        url = "https://medias24.com/categorie/leboursier/actus/feed/"
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
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
                news.append({'title': title, 'link': link, 'category': cat, 'time': max(0, mins)})
            news_cache = news
            return news
    except Exception as e:
        print(f"News error: {e}")
    return news_cache

def background_refresh():
    while True:
        print(f"[{datetime.now()}] Refresh starting...")
        try:
            scrape_masi_components()
            scrape_masi_index()
            get_news()
            print(f"[{datetime.now()}] Refresh done")
        except Exception as e:
            print(f"Refresh error: {e}")
        time.sleep(600)

# Routes (unchanged except function names)
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
    scrape_masi_components()
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
    print("Starting RISK Terminal - Investing.com edition")
    print("═" * 60)

    print("Initial scrape...")
    scrape_masi_components()
    scrape_masi_index()
    get_news()

    threading.Thread(target=background_refresh, daemon=True).start()
    print("Background refresh started (10 min)")

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)
