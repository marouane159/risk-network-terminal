from flask import Flask, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime, timezone

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Complete expanded stock list (54 tickers)
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

# Build lookup dictionaries from BASE_STOCKS
STOCK_NAMES = {s["symbol"]: s["name"] for s in BASE_STOCKS}
STOCK_SECTORS = {s["symbol"]: s["sector"] for s in BASE_STOCKS}

# In-memory cache
cache = {
    'stocks': [],
    'news': [],
    'last_update': None
}

def print_news_to_terminal(news_items):
    """Print fetched news to terminal with formatting"""
    if not news_items:
        print("No news items to display")
        return
    
    print("\n" + "="*80)
    print("LATEST NEWS FROM MEDIAS24 RSS (Le Boursier)")
    print("="*80)
    
    for i, item in enumerate(news_items[:10], 1):
        print(f"\n{i}. {item.get('title', 'N/A')[:70]}")
        print(f"   Date: {item.get('date', 'N/A')}")
        print(f"   Link: {item.get('link', 'N/A')[:60]}...")
        print(f"   Category: {item.get('category', 'N/A')}")
        print("-" * 80)
    
    print(f"\nTotal news items fetched: {len(news_items)}")
    print("="*80 + "\n")

def scrape_tradingview():
    """Scrape TradingView Morocco - ALL available stocks"""
    try:
        url = "https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        print(f"Fetching from TradingView...")
        response = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        stocks = []
        table = soup.find('table')
        
        if table:
            rows = table.find_all('tr')[1:]  # Skip header
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    symbol_elem = cells[0].find('a')
                    if symbol_elem:
                        symbol = symbol_elem.text.strip()
                        price_text = cells[1].text.strip().replace('MAD', '').replace(',', '')
                        change_text = cells[2].text.strip().replace('%', '').replace('(', '-').replace(')', '')
                        
                        try:
                            price = float(price_text)
                            change = float(change_text)
                            
                            # Generate trend
                            trend = []
                            base = price / (1 + (change / 100)) if change != 0 else price * 0.995
                            for i in range(7):
                                point = base + ((price - base) * (i / 6))
                                trend.append(round(point, 2))
                            
                            stocks.append({
                                'symbol': symbol,
                                'name': get_stock_name(symbol),
                                'sector': get_sector(symbol),
                                'price': price,
                                'change': change,
                                'volume': 'N/A',
                                'trend': trend
                            })
                            print(f"  ✓ {symbol}: {price:.2f} MAD ({change:+.2f}%)")
                        except Exception as e:
                            print(f"  ✗ Error parsing {symbol}: {e}")
                            continue
        
        print(f"\nTotal stocks scraped: {len(stocks)}")
        return stocks
        
    except Exception as e:
        print(f"Error scraping TradingView: {e}")
        return []

def scrape_medias24_rss():
    """Scrape news from Medias24 RSS feed - FIXED VERSION"""
    try:
        url = "https://medias24.com/categorie/leboursier/actus/feed/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        print(f"\nFetching RSS from {url}...")
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        
        print(f"RSS Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"RSS fetch failed: {response.status_code}")
            return []
        
        # Parse XML properly
        root = ET.fromstring(response.content)
        
        # CRITICAL FIX: Find channel first, then items
        channel = root.find('channel')
        if channel is None:
            print("No channel found in RSS")
            return []
        
        items = channel.findall('item')
        print(f"Found {len(items)} RSS items")
        
        news = []
        
        for i, item in enumerate(items[:20]):
            try:
                # Extract title
                title_elem = item.find('title')
                title = title_elem.text if title_elem is not None else 'N/A'
                
                # Extract link
                link_elem = item.find('link')
                link = link_elem.text if link_elem is not None else ''
                
                # Extract and parse date properly
                date_elem = item.find('pubDate')
                time_mins = i * 5  # fallback
                date_str = datetime.now().strftime('%Y-%m-%d')
                
                if date_elem is not None and date_elem.text:
                    try:
                        # Parse: Thu, 12 Feb 2026 16:13:22 +0000
                        pub_date = datetime.strptime(date_elem.text, '%a, %d %b %Y %H:%M:%S %z')
                        date_str = pub_date.strftime('%Y-%m-%d %H:%M')
                        
                        # Calculate minutes ago
                        now = datetime.now(timezone.utc)
                        diff = (now - pub_date).total_seconds() / 60
                        time_mins = int(diff) if diff > 0 else 0
                    except Exception as e:
                        print(f"  Date parse error: {e}")
                
                # Extract description
                desc_elem = item.find('description')
                summary = ''
                if desc_elem is not None and desc_elem.text:
                    soup = BeautifulSoup(desc_elem.text, 'html.parser')
                    summary = soup.get_text(strip=True)
                    # Clean up "appeared first on" text
                    if "appeared first on" in summary:
                        summary = summary.split("appeared first on")[0].strip()
                    summary = summary[:200]
                
                # Get category
                cat_elem = item.find('category')
                category = 'INFO'
                if cat_elem is not None and cat_elem.text:
                    category = cat_elem.text.upper()
                
                news.append({
                    'time': time_mins,
                    'title': title,
                    'link': link,
                    'category': category,
                    'source': 'Medias24.com',
                    'date': date_str,
                    'summary': summary
                })
                print(f"  ✓ News {i+1}: {title[:50]}... ({time_mins}m ago)")
                
            except Exception as e:
                print(f"  ✗ Error parsing item {i}: {e}")
                continue
        
        # Print to terminal
        print_news_to_terminal(news)
        return news
        
    except Exception as e:
        print(f"Error scraping RSS: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_stock_name(symbol):
    """Get full name from symbol"""
    if symbol in STOCK_NAMES:
        return STOCK_NAMES[symbol]
    return symbol

def get_sector(symbol):
    """Get sector from symbol"""
    if symbol in STOCK_SECTORS:
        return STOCK_SECTORS[symbol]
    return 'DIVERS'

@app.route('/')
def home():
    return "RISK NETWORK GROUP API - Use /api/stocks or /api/news or /api/all"

@app.route('/api/stocks')
def get_stocks():
    """Get stocks"""
    global cache
    
    if (not cache['last_update'] or 
        (datetime.now() - cache['last_update']).seconds > 30):
        
        print("\n=== REFRESHING CACHE ===")
        cache['stocks'] = scrape_tradingview()
        cache['news'] = scrape_medias24_rss()
        cache['last_update'] = datetime.now()
        print("=== CACHE UPDATED ===\n")
    
    return jsonify(cache['stocks'])

@app.route('/api/news')
def get_news():
    """Get news"""
    global cache
    
    if (not cache['last_update'] or 
        (datetime.now() - cache['last_update']).seconds > 30):
        
        print("\n=== REFRESHING CACHE ===")
        cache['stocks'] = scrape_tradingview()
        cache['news'] = scrape_medias24_rss()
        cache['last_update'] = datetime.now()
        print("=== CACHE UPDATED ===\n")
    
    return jsonify(cache['news'])

@app.route('/api/all')
def get_all():
    """Get everything"""
    global cache
    
    if (not cache['last_update'] or 
        (datetime.now() - cache['last_update']).seconds > 30):
        
        print("\n=== REFRESHING CACHE ===")
        cache['stocks'] = scrape_tradingview()
        cache['news'] = scrape_medias24_rss()
        cache['last_update'] = datetime.now()
        print("=== CACHE UPDATED ===\n")
    
    return jsonify({
        'stocks': cache['stocks'],
        'news': cache['news'],
        'lastUpdate': cache['last_update'].isoformat() if cache['last_update'] else None
    })

if __name__ == '__main__':
    # Print startup info
    print("\n" + "="*80)
    print(f"RISK NETWORK GROUP API SERVER")
    print(f"Loaded {len(BASE_STOCKS)} stock definitions")
    print("="*80 + "\n")
    
    # Initial scrape
    print("Initial data fetch...")
    cache['stocks'] = scrape_tradingview()
    cache['news'] = scrape_medias24_rss()
    cache['last_update'] = datetime.now()
    
    print(f"\n✓ Server ready: {len(cache['stocks'])} stocks, {len(cache['news'])} news")
    
    # Run server
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
