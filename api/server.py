from flask import Flask, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime, timezone

app = Flask(__name__)
CORS(app)

# COMPLETE LIST - All 54 tickers (your exact list, cleaned)
BASE_STOCKS = [
    {"symbol": "TGC", "name": "TRAVAUX GENERAUX DE CONSTRUCTIONS", "sector": "Construction"},
    {"symbol": "TMA", "name": "TOTALENERGIES MARKETING", "sector": "Énergie"},
    {"symbol": "TQM", "name": "TAQA MOROCCO", "sector": "Énergie"},
    {"symbol": "NKL", "name": "ENNAKL SA", "sector": "Transport"},
    {"symbol": "LHM", "name": "LAFARGEHOLCIM", "sector": "Construction"},
    {"symbol": "UMR", "name": "UNIMER", "sector": "Agroalimentaire"},
    {"symbol": "WAA", "name": "WAFA ASSURANCE", "sector": "Assurance"},
    {"symbol": "ZDJ", "name": "ZELLIDJA S.A", "sector": "Mines"},
    {"symbol": "MSA", "name": "SODEP MARSA", "sector": "Transport"},
    {"symbol": "RDS", "name": "RESIDENCE DAR SAADA", "sector": "Construction"},
    {"symbol": "CSR", "name": "COSUMAR", "sector": "Industrie"},
    {"symbol": "CFG", "name": "CFG BANK", "sector": "Banque"},
    {"symbol": "CMG", "name": "CMGP CAS", "sector": "Agriculture"},
    {"symbol": "HPS", "name": "HPS", "sector": "Paiment"},
    {"symbol": "S2M", "name": "S2M", "sector": "Paiment"},
    {"symbol": "RIS", "name": "RISMA", "sector": "Hotel Management"},
    {"symbol": "DHO", "name": "DELTA HOLDING", "sector": "Industrie"},
    {"symbol": "DWY", "name": "DISWAY", "sector": "Distribution éléctro"},
    {"symbol": "SNA", "name": "STOKVIS NORD AFRIQUE", "sector": "Distribution service"},
    {"symbol": "SNP", "name": "SNEP", "sector": "Process Industries"},
    {"symbol": "STR", "name": "STROC INDUSTRIE", "sector": "Service Industriel"},
    {"symbol": "INV", "name": "INVOLYS", "sector": "Service de Technologie"},
    {"symbol": "MIC", "name": "MICRODATA", "sector": "Service de Technologie"},
    {"symbol": "DYT", "name": "DISTY TECHNOLOGIES", "sector": "Service de destribution"},
    {"symbol": "ADH", "name": "DOUJA PROM ADDOHA", "sector": "Immobilier"},
    {"symbol": "IMO", "name": "IMMORENT INVEST", "sector": "Immobilier"},
    {"symbol": "ADI", "name": "ALLIANCES", "sector": "Divers"},
    {"symbol": "AFI", "name": "AFRIC INDUSTRIES", "sector": "Industrie"},
    {"symbol": "AFM", "name": "AFMA", "sector": "Finance"},
    {"symbol": "AKT", "name": "AKDITAL S.A", "sector": "Santé"},
    {"symbol": "ALM", "name": "ALUMINIUM DU MAROC", "sector": "Matériaux"},
    {"symbol": "ARD", "name": "ARADEI CAPITAL", "sector": "Immobilier"},
    {"symbol": "ATH", "name": "AUTO HALL", "sector": "Automobile"},
    {"symbol": "ATL", "name": "ATLANTASANAD", "sector": "Distribution"},
    {"symbol": "ATW", "name": "ATTIJARIWAFA BANK", "sector": "Banque"},
    {"symbol": "BAL", "name": "BALIMA", "sector": "Distribution"},
    {"symbol": "BCP", "name": "BANQUE CENTRALE POPULAIRE", "sector": "Banque"},
    {"symbol": "CRS", "name": "CARTIER SAADA", "sector": "Distribution"},
    {"symbol": "CIH", "name": "CREDIT IMMOBILIER ET HOTELIER", "sector": "Banque"},
    {"symbol": "CMT", "name": "CIMENTS DU MAROC", "sector": "Matériaux"},
    {"symbol": "COL", "name": "COLORADO", "sector": "Distribution"},
    {"symbol": "CTM", "name": "COMPAGNIE DE TRANSPORTS AU MAROC", "sector": "Transport"},
    {"symbol": "DIM", "name": "DELATTRE LEVIVIER MAROC", "sector": "Industrie"},
    {"symbol": "DRI", "name": "DARI COUSPATE", "sector": "Agroalimentaire"},
    {"symbol": "EQD", "name": "EQDOM", "sector": "Immobilier"},
    {"symbol": "FBR", "name": "FENIE BROSSETTE", "sector": "Distribution"},
    {"symbol": "IAM", "name": "MAROC TELECOM", "sector": "Télécom"},
    {"symbol": "INM", "name": "INDUSTRIE DU MAROC", "sector": "Industrie"},
    {"symbol": "JET", "name": "JET CONTRACTORS", "sector": "Construction"},
    {"symbol": "LES", "name": "LESIEUR CRISTAL", "sector": "Agroalimentaire"},
    {"symbol": "MOX", "name": "MAGHREB OXYGENE", "sector": "Industrie"},
    {"symbol": "MNG", "name": "MANAGEM", "sector": "Mines"},
    {"symbol": "MUT", "name": "MUTANDIS", "sector": "Agroalimentaire"},
    {"symbol": "SID", "name": "SONASID", "sector": "Agroalimentaire"},
    {"symbol": "SOT", "name": "SOTHEMA", "sector": "Pharma"},
    {"symbol": "SRM", "name": "REALISATIONS MECANIQUES", "sector": "Industrie"},
    {"symbol": "MDP", "name": "MED PAPER", "sector": "Industrie"},
    {"symbol": "VCN", "name": "VICENNE", "sector": "Santé"},
    {"symbol": "SMI", "name": "Société métallurgique d'imiter", "sector": "Finance"},
    {"symbol": "CDM", "name": "Crédit du Maroc", "sector": "Banque"}
]

# Build lookup
STOCK_NAMES = {s["symbol"]: s["name"] for s in BASE_STOCKS}
STOCK_SECTORS = {s["symbol"]: s["sector"] for s in BASE_STOCKS}

cache = {'stocks': [], 'news': [], 'last_update': None}

def print_news_to_terminal(news_items):
    if not news_items:
        print("No news items")
        return
    print("\n" + "="*80)
    print("LATEST NEWS FROM MEDIAS24 RSS")
    print("="*80)
    for i, item in enumerate(news_items[:10], 1):
        print(f"\n{i}. {item.get('title', 'N/A')[:70]}")
        print(f"   Link: {item.get('link', 'N/A')[:60]}...")
        print(f"   Time: {item.get('time', 'N/A')}m ago | Category: {item.get('category', 'N/A')}")
        print("-" * 80)
    print(f"\nTotal: {len(news_items)} news items")
    print("="*80 + "\n")

def scrape_tradingview():
    """Scrape TradingView and merge with ALL 54 BASE_STOCKS"""
    try:
        url = "https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        print(f"Fetching TradingView...")
        response = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Parse TradingView data into dict
        tv_data = {}
        table = soup.find('table')
        
        if table:
            for row in table.find_all('tr')[1:]:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    symbol_elem = cells[0].find('a')
                    if symbol_elem:
                        symbol = symbol_elem.text.strip()
                        try:
                            price = float(cells[1].text.strip().replace('MAD', '').replace(',', ''))
                            change = float(cells[2].text.strip().replace('%', '').replace('(', '-').replace(')', ''))
                            tv_data[symbol] = {'price': price, 'change': change}
                        except:
                            continue
        
        print(f"TradingView returned {len(tv_data)} stocks")
        
        # CRITICAL: Build ALL 54 stocks, using TV data where available
        all_stocks = []
        for stock in BASE_STOCKS:
            symbol = stock['symbol']
            
            if symbol in tv_data:
                # Use live TradingView data
                price = tv_data[symbol]['price']
                change = tv_data[symbol]['change']
                has_data = True
            else:
                # Use placeholder for stocks not in TV (market closed or illiquid)
                price = 0.0
                change = 0.0
                has_data = False
            
            # Generate trend
            trend = []
            if has_data and change != 0:
                base = price / (1 + (change / 100))
            else:
                base = 100.0  # Default base for placeholder
            
            for i in range(7):
                if has_data:
                    point = base + ((price - base) * (i / 6))
                else:
                    point = base + (i * 0.1)  # Flat trend for placeholder
                trend.append(round(point, 2))
            
            all_stocks.append({
                'symbol': symbol,
                'name': stock['name'],
                'sector': stock['sector'],
                'price': price if has_data else 0.0,
                'change': change if has_data else 0.0,
                'volume': 'N/A',
                'trend': trend,
                'has_live_data': has_data  # Flag to show if live or placeholder
            })
        
        # Sort: live data first, then alphabetically
        all_stocks.sort(key=lambda x: (not x['has_live_data'], x['symbol']))
        
        print(f"\n✓ Returning ALL {len(all_stocks)} stocks ({len(tv_data)} with live data)")
        return all_stocks
        
    except Exception as e:
        print(f"Error: {e}")
        # Return all BASE_STOCKS with placeholder data on error
        return [{
            'symbol': s['symbol'],
            'name': s['name'],
            'sector': s['sector'],
            'price': 0.0,
            'change': 0.0,
            'volume': 'N/A',
            'trend': [100.0] * 7,
            'has_live_data': False
        } for s in BASE_STOCKS]

def scrape_medias24_rss():
    """Scrape news from Medias24 RSS"""
    try:
        url = "https://medias24.com/categorie/leboursier/actus/feed/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        print(f"\nFetching RSS...")
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"RSS failed: {response.status_code}")
            return []
        
        root = ET.fromstring(response.content)
        channel = root.find('channel')
        if channel is None:
            print("No channel in RSS")
            return []
        
        items = channel.findall('item')
        print(f"Found {len(items)} RSS items")
        
        news = []
        for i, item in enumerate(items[:20]):
            try:
                title = item.find('title').text if item.find('title') is not None else 'N/A'
                link = item.find('link').text if item.find('link') is not None else ''
                
                # Parse date
                time_mins = i * 5
                date_str = datetime.now().strftime('%Y-%m-%d')
                date_elem = item.find('pubDate')
                if date_elem and date_elem.text:
                    try:
                        pub_date = datetime.strptime(date_elem.text, '%a, %d %b %Y %H:%M:%S %z')
                        date_str = pub_date.strftime('%Y-%m-%d %H:%M')
                        now = datetime.now(timezone.utc)
                        diff = (now - pub_date).total_seconds() / 60
                        time_mins = int(diff) if diff > 0 else 0
                    except:
                        pass
                
                # Summary
                summary = ''
                desc = item.find('description')
                if desc and desc.text:
                    soup = BeautifulSoup(desc.text, 'html.parser')
                    summary = soup.get_text(strip=True)
                    if "appeared first on" in summary:
                        summary = summary.split("appeared first on")[0].strip()
                    summary = summary[:200]
                
                # Category
                cat = item.find('category')
                category = cat.text.upper() if cat and cat.text else 'INFO'
                
                news.append({
                    'time': time_mins,
                    'title': title,
                    'link': link,
                    'category': category,
                    'source': 'Medias24.com',
                    'date': date_str,
                    'summary': summary
                })
                print(f"  ✓ {i+1}: {title[:50]}... ({time_mins}m)")
                
            except Exception as e:
                print(f"  ✗ Error item {i}: {e}")
                continue
        
        print_news_to_terminal(news)
        return news
        
    except Exception as e:
        print(f"RSS error: {e}")
        return []

@app.route('/')
def home():
    return "RISK NETWORK GROUP API - Use /api/stocks or /api/news or /api/all"

@app.route('/api/stocks')
def get_stocks():
    global cache
    if (not cache['last_update'] or 
        (datetime.now() - cache['last_update']).seconds > 30):
        print("\n=== REFRESHING ===")
        cache['stocks'] = scrape_tradingview()
        cache['news'] = scrape_medias24_rss()
        cache['last_update'] = datetime.now()
        print("=== DONE ===\n")
    return jsonify(cache['stocks'])

@app.route('/api/news')
def get_news():
    global cache
    if (not cache['last_update'] or 
        (datetime.now() - cache['last_update']).seconds > 30):
        print("\n=== REFRESHING ===")
        cache['stocks'] = scrape_tradingview()
        cache['news'] = scrape_medias24_rss()
        cache['last_update'] = datetime.now()
        print("=== DONE ===\n")
    return jsonify(cache['news'])

@app.route('/api/all')
def get_all():
    global cache
    if (not cache['last_update'] or 
        (datetime.now() - cache['last_update']).seconds > 30):
        print("\n=== REFRESHING ===")
        cache['stocks'] = scrape_tradingview()
        cache['news'] = scrape_medias24_rss()
        cache['last_update'] = datetime.now()
        print("=== DONE ===\n")
    
    return jsonify({
        'stocks': cache['stocks'],
        'news': cache['news'],
        'lastUpdate': cache['last_update'].isoformat() if cache['last_update'] else None
    })

if __name__ == '__main__':
    print("\n" + "="*80)
    print(f"RISK NETWORK GROUP API")
    print(f"Total stock definitions: {len(BASE_STOCKS)}")
    print("="*80 + "\n")
    
    print("Initial fetch...")
    cache['stocks'] = scrape_tradingview()
    cache['news'] = scrape_medias24_rss()
    cache['last_update'] = datetime.now()
    
    print(f"\n✓ Ready: {len(cache['stocks'])} stocks, {len(cache['news'])} news")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
