from flask import Flask, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import urljoin

app = Flask(__name__)
CORS(app)

# COMPLETE LIST - All 54 tickers
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

STOCK_NAMES = {s["symbol"]: s["name"] for s in BASE_STOCKS}
STOCK_SECTORS = {s["symbol"]: s["sector"] for s in BASE_STOCKS}

cache = {'stocks': [], 'news': [], 'last_update': None}

def clean_html_text(html_text):
    """Clean HTML tags from text and normalize whitespace"""
    if not html_text:
        return ''
    
    # Remove HTML tags
    soup = BeautifulSoup(html_text, 'html.parser')
    text = soup.get_text()
    
    # Clean up whitespace and special characters
    text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single
    text = re.sub(r'\n+', ' ', text)  # Newlines to spaces
    text = text.strip()
    
    return text

def parse_rss_date(date_str):
    """Parse various RSS date formats with robust error handling"""
    if not date_str:
        return None, 0
    
    # Common RSS/Atom date formats
    date_formats = [
        '%a, %d %b %Y %H:%M:%S %z',     # Wed, 15 Jun 2024 10:00:00 +0000
        '%a, %d %b %Y %H:%M:%S %Z',     # Wed, 15 Jun 2024 10:00:00 GMT
        '%d %b %Y %H:%M:%S %z',         # 15 Jun 2024 10:00:00 +0000
        '%Y-%m-%dT%H:%M:%S%z',          # 2024-06-15T10:00:00+00:00
        '%Y-%m-%d %H:%M:%S',            # 2024-06-15 10:00:00
        '%Y-%m-%d'                      # 2024-06-15
    ]
    
    date_str = date_str.strip()
    
    for fmt in date_formats:
        try:
            date_obj = datetime.strptime(date_str, fmt)
            return date_obj.strftime('%Y-%m-%d %H:%M'), 0
        except ValueError:
            continue
    
    # If no format matches, try to extract time difference
    now = datetime.now(timezone.utc)
    
    # Try to parse relative times like "2 hours ago"
    time_patterns = [
        (r'(\d+)\s*hour', lambda m: now.timestamp() - int(m.group(1)) * 3600),
        (r'(\d+)\s*min', lambda m: now.timestamp() - int(m.group(1)) * 60),
        (r'(\d+)\s*sec', lambda m: now.timestamp() - int(m.group(1))),
    ]
    
    for pattern, calc_func in time_patterns:
        match = re.search(pattern, date_str.lower())
        if match:
            timestamp = calc_func(match)
            pub_date = datetime.fromtimestamp(timestamp, timezone.utc)
            return pub_date.strftime('%Y-%m-%d %H:%M'), 0
    
    # If all parsing fails, return current time
    return now.strftime('%Y-%m-%d %H:%M'), 0

def scrape_tradingview():
    """Scrape TradingView and merge with ALL 54 BASE_STOCKS"""
    try:
        url = "https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        print(f"Fetching TradingView...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # Raise exception for bad status codes
        soup = BeautifulSoup(response.text, 'html.parser')
        
        tv_data = {}
        table = soup.find('table')
        
        if table:
            for row in table.find_all('tr')[1:]:  # Skip header
                cells = row.find_all('td')
                if len(cells) >= 3:
                    symbol_elem = cells[0].find('a')
                    if symbol_elem:
                        symbol = symbol_elem.text.strip()
                        try:
                            price_text = cells[1].text.strip()
                            change_text = cells[2].text.strip()
                            
                            # Clean and parse price
                            price = float(price_text.replace('MAD', '').replace(',', '').strip())
                            
                            # Clean and parse change (handle various formats)
                            change_text = change_text.replace('%', '').replace('(', '-').replace(')', '').strip()
                            change = float(change_text)
                            
                            tv_data[symbol] = {'price': price, 'change': change}
                        except (ValueError, AttributeError) as e:
                            print(f"  Warning: Failed to parse row for {symbol}: {e}")
                            continue
        
        print(f"TradingView returned {len(tv_data)} stocks")
        
        all_stocks = []
        for stock in BASE_STOCKS:
            symbol = stock['symbol']
            
            if symbol in tv_data:
                price = tv_data[symbol]['price']
                change = tv_data[symbol]['change']
                has_data = True
            else:
                price = 0.0
                change = 0.0
                has_data = False
            
            # Generate trend data
            trend = []
            if has_data and change != 0:
                base = price / (1 + (change / 100))
            else:
                base = 100.0
            
            for i in range(7):
                if has_data:
                    point = base + ((price - base) * (i / 6))
                else:
                    point = base + (i * 0.1)
                trend.append(round(point, 2))
            
            all_stocks.append({
                'symbol': symbol,
                'name': stock['name'],
                'sector': stock['sector'],
                'price': price if has_data else 0.0,
                'change': change if has_data else 0.0,
                'volume': 'N/A',
                'trend': trend,
                'has_live_data': has_data
            })
        
        # Sort stocks: those with live data first, then alphabetically
        all_stocks.sort(key=lambda x: (not x['has_live_data'], x['symbol']))
        
        print(f"Returning ALL {len(all_stocks)} stocks ({len(tv_data)} with live data)")
        return all_stocks
        
    except requests.exceptions.RequestException as e:
        print(f"Network error fetching TradingView: {e}")
        return fallback_stocks()
    except Exception as e:
        print(f"Error scraping TradingView: {e}")
        return fallback_stocks()

def fallback_stocks():
    """Return fallback stock data when scraping fails"""
    print("Using fallback stock data...")
    return [{
        'symbol': stock['symbol'],
        'name': stock['name'],
        'sector': stock['sector'],
        'price': 0.0,
        'change': 0.0,
        'volume': 'N/A',
        'trend': [100.0] * 7,
        'has_live_data': False
    } for stock in BASE_STOCKS]

def scrape_medias24_rss():
    """Scrape news from Medias24 RSS feed with robust parsing"""
    try:
        url = "https://medias24.com/categorie/leboursier/actus/feed/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8'
        }
        
        print(f"Fetching RSS from {url}...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        # Parse XML with error handling
        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as e:
            print(f"XML parsing error: {e}")
            # Try to fix encoding issues
            content = response.content.decode('utf-8', errors='ignore')
            root = ET.fromstring(content)
        
        # Find items - handle both RSS and Atom feeds
        items = root.findall('.//item') or root.findall('.//entry')
        
        if not items:
            print("No items found in RSS feed")
            return []
        
        print(f"Found {len(items)} RSS items")
        
        news = []
        now = datetime.now(timezone.utc)
        
        for i, item in enumerate(items[:20]):  # Limit to 20 items
            try:
                # Extract title
                title_elem = item.find('title')
                title = clean_html_text(title_elem.text) if title_elem is not None and title_elem.text else 'N/A'
                
                # Extract link
                link = ''
                link_elem = item.find('link')
                if link_elem is not None:
                    if link_elem.text:
                        link = link_elem.text.strip()
                    else:
                        # Handle link as attribute (Atom feeds)
                        link = link_elem.get('href', '')
                
                # Ensure link is absolute
                if link and not link.startswith('http'):
                    link = urljoin('https://medias24.com', link)
                
                # Extract and parse pub date
                date_elem = (item.find('pubDate') or 
                           item.find('published') or 
                           item.find('updated') or
                           item.find('dc:date'))
                
                date_str = datetime.now().strftime('%Y-%m-%d %H:%M')
                time_mins = i * 5
                
                if date_elem is not None and date_elem.text:
                    parsed_date, _ = parse_rss_date(date_elem.text)
                    if parsed_date:
                        date_str = parsed_date
                        try:
                            pub_date = datetime.strptime(parsed_date, '%Y-%m-%d %H:%M')
                            diff = (now - pub_date.replace(tzinfo=timezone.utc)).total_seconds() / 60
                            time_mins = int(max(0, diff))
                        except:
                            pass
                
                # Extract summary/description
                summary = ''
                desc_selectors = ['description', 'summary', 'content', 'content:encoded']
                for selector in desc_selectors:
                    desc_elem = item.find(selector)
                    if desc_elem is not None:
                        if desc_elem.text:
                            summary = clean_html_text(desc_elem.text)
                            break
                        elif 'encoded' in desc_elem.attrib:
                            summary = clean_html_text(desc_elem.attrib['encoded'])
                            break
                
                # Clean up summary
                if summary:
                    # Remove "appeared first on" text
                    if "appeared first on" in summary.lower():
                        summary = re.split(r"appeared first on", summary, flags=re.IGNORECASE)[0].strip()
                    
                    # Limit summary length
                    summary = summary[:200]
                
                # Extract category
                category = 'INFO'
                cat_elem = item.find('category')
                if cat_elem is not None and cat_elem.text:
                    category = clean_html_text(cat_elem.text).upper()
                
                news_item = {
                    'time': time_mins,
                    'title': title,
                    'link': link,
                    'category': category,
                    'source': 'Medias24.com',
                    'date': date_str,
                    'summary': summary
                }
                
                news.append(news_item)
                print(f"  News {i+1}: {title[:40]}... ({time_mins}m)")
                
            except Exception as e:
                print(f"  Error parsing item {i}: {e}")
                continue
        
        print(f"Successfully parsed {len(news)} news items")
        return news
        
    except requests.exceptions.RequestException as e:
        print(f"Network error fetching RSS: {e}")
        return []
    except Exception as e:
        print(f"RSS scraping error: {e}")
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
    print("\n" + "="*70)
    print(f"RISK NETWORK GROUP API")
    print(f"Total stocks: {len(BASE_STOCKS)}")
    print("="*70 + "\n")
    
    print("Initial fetch...")
    cache['stocks'] = scrape_tradingview()
    cache['news'] = scrape_medias24_rss()
    cache['last_update'] = datetime.now()
    
    live_count = sum(1 for s in cache['stocks'] if s.get('has_live_data', False))
    print(f"\nReady: {len(cache['stocks'])} stocks ({live_count} live), {len(cache['news'])} news")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
