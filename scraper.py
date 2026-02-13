#!/usr/bin/env python3
"""
RISK NETWORK GROUP - Market Data Scraper
Fetches all 54 tickers + Medias24 news
"""

import requests
import xml.etree.ElementTree as ET
import json
import random
import os
import sys
import re
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Configuration
DATA_DIR = "data"
STOCKS_FILE = f"{DATA_DIR}/stocks.json"
NEWS_FILE = f"{DATA_DIR}/news.json"
UPDATE_FILE = f"{DATA_DIR}/last_update.txt"

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

def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def ensure_data_dir():
    """Ensure data directory exists"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        log(f"Created data directory: {DATA_DIR}")

def clean_html_text(html_text):
    """Clean HTML tags from text and normalize whitespace"""
    if not html_text:
        return ''
    
    # Remove HTML tags using BeautifulSoup
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
            # Handle timezone naive dates
            if date_obj.tzinfo is None:
                date_obj = date_obj.replace(tzinfo=timezone.utc)
            return date_obj.strftime('%Y-%m-%d %H:%M'), 0
        except ValueError:
            continue
    
    # If no format matches, return current time
    now = datetime.now(timezone.utc)
    return now.strftime('%Y-%m-%d %H:%M'), 0

def get_moroccan_stocks():
    """Fetch all 54 stocks with TradingView merge"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        url = "https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/"
        log(f"Fetching TradingView from {url}")
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # Raise exception for bad status codes
        
        soup = BeautifulSoup(response.text, 'html.parser')
        tv_data = {}
        
        # Find the main table
        table = soup.find('table')
        if not table:
            log("No table found in TradingView page", "ERROR")
            return None
        
        log("Found table, parsing rows...")
        rows = table.find_all('tr')[1:]  # Skip header row
        
        for row_num, row in enumerate(rows, 1):
            try:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    symbol_cell = cells[0].find('a')
                    if symbol_cell:
                        symbol = symbol_cell.text.strip()
                        if not symbol:
                            continue
                        
                        # Clean and parse price
                        price_text = cells[1].text.strip()
                        price = float(price_text.replace('MAD', '').replace(',', '').strip())
                        
                        # Clean and parse change
                        change_text = cells[2].text.strip()
                        change_text = change_text.replace('%', '').replace('(', '-').replace(')', '').strip()
                        change = float(change_text)
                        
                        tv_data[symbol] = {'price': price, 'change': change}
                        log(f"  Parsed {symbol}: {price} MAD, {change}%")
                        
            except (ValueError, AttributeError) as e:
                log(f"  Warning: Failed to parse row {row_num}: {e}", "WARNING")
                continue
        
        log(f"TradingView: Successfully parsed {len(tv_data)} stocks")
        
        # Merge with BASE_STOCKS
        all_stocks = []
        for stock in BASE_STOCKS:
            symbol = stock['symbol']
            
            if symbol in tv_data:
                price = tv_data[symbol]['price']
                change = tv_data[symbol]['change']
                has_data = True
                log(f"  Found live data for {symbol}: {price} MAD")
            else:
                price = 0.0
                change = 0.0
                has_data = False
                log(f"  No live data for {symbol}, using fallback", "DEBUG")
            
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
                "symbol": symbol,
                "name": stock['name'],
                "sector": stock['sector'],
                "price": price if has_data else 0.0,
                "change": change if has_data else 0.0,
                "volume": "N/A",
                "trend": trend,
                "has_live_data": has_data
            })
        
        # Sort stocks: live data first, then alphabetically
        all_stocks.sort(key=lambda x: (not x['has_live_data'], x['symbol']))
        
        live_count = sum(1 for s in all_stocks if s['has_live_data'])
        log(f"Total: {len(all_stocks)} stocks ({live_count} with live data)")
        return all_stocks
        
    except requests.exceptions.RequestException as e:
        log(f"Network error fetching TradingView: {e}", "ERROR")
        return None
    except Exception as e:
        log(f"Error scraping TradingView: {e}", "ERROR")
        return None

def fetch_medias24_news():
    """Fetch Medias24 RSS with robust parsing"""
    log("Fetching Medias24 RSS...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8'
        }
        
        url = "https://medias24.com/categorie/leboursier/actus/feed/"
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        log(f"RSS Response: {response.status_code}, Content-Type: {response.headers.get('content-type', 'unknown')}")
        
        # Parse XML with error handling
        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as e:
            log(f"XML parsing error: {e}", "ERROR")
            # Try to fix encoding issues
            content = response.content.decode('utf-8', errors='ignore')
            root = ET.fromstring(content)
        
        # Find items - handle both RSS and Atom feeds
        items = root.findall('.//item') or root.findall('.//entry')
        
        if not items:
            log("No items found in RSS feed", "ERROR")
            return []
        
        log(f"Found {len(items)} RSS items")
        
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
                            pub_date = pub_date.replace(tzinfo=timezone.utc)
                            diff = (now - pub_date).total_seconds() / 60
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
                log(f"  News {i+1}: {title[:40]}... ({time_mins}m ago)")
                
            except Exception as e:
                log(f"  Error parsing item {i}: {e}", "WARNING")
                continue
        
        log(f"Successfully parsed {len(news)} news items")
        
        # Terminal output
        print("\n" + "="*70)
        print("LATEST NEWS FROM MEDIAS24 (Le Boursier)")
        print("="*70)
        for n in news[:5]:
            print(f"\n• {n['title'][:60]}...")
            if n['link']:
                print(f"  Link: {n['link'][:70]}")
            print(f"  {n['time']}m ago | {n['category']}")
            if n['summary']:
                print(f"  Summary: {n['summary'][:100]}...")
        print(f"\nTotal: {len(news)} news items")
        print("="*70 + "\n")
        
        return news
        
    except requests.exceptions.RequestException as e:
        log(f"Network error fetching RSS: {e}", "ERROR")
        return []
    except Exception as e:
        log(f"RSS scraping error: {e}", "ERROR")
        return []

def save_data(stocks, news):
    """Save stocks and news data to files"""
    ensure_data_dir()
    
    try:
        # Save stocks
        with open(STOCKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stocks, f, ensure_ascii=False, indent=2)
        
        # Save news
        with open(NEWS_FILE, 'w', encoding='utf-8') as f:
            json.dump(news, f, ensure_ascii=False, indent=2)
        
        # Save timestamp
        with open(UPDATE_FILE, 'w') as f:
            f.write(datetime.now().isoformat())
        
        log(f"Successfully saved: {len(stocks)} stocks, {len(news)} news")
        log(f"Files: {STOCKS_FILE}, {NEWS_FILE}, {UPDATE_FILE}")
        
    except Exception as e:
        log(f"Error saving data: {e}", "ERROR")

def load_fallback_stocks():
    """Load fallback stock data"""
    log("Loading fallback stock data...")
    fallback_stocks = []
    for stock in BASE_STOCKS:
        fallback_stocks.append({
            "symbol": stock['symbol'],
            "name": stock['name'],
            "sector": stock['sector'],
            "price": 0.0,
            "change": 0.0,
            "volume": "N/A",
            "trend": [100.0] * 7,
            "has_live_data": False
        })
    return fallback_stocks

def load_cached_stocks():
    """Load previously cached stocks"""
    try:
        if os.path.exists(STOCKS_FILE):
            with open(STOCKS_FILE, 'r', encoding='utf-8') as f:
                cached_stocks = json.load(f)
            log(f"Loaded {len(cached_stocks)} cached stocks")
            return cached_stocks
    except Exception as e:
        log(f"Error loading cached stocks: {e}", "WARNING")
    return None

def main():
    """Main execution function"""
    log("=" * 70)
    log(f"RISK NETWORK GROUP SCRAPER v2.0")
    log(f"Target: {len(BASE_STOCKS)} stocks + Medias24 news")
    log("=" * 70)
    
    # Fetch fresh data
    stocks = get_moroccan_stocks()
    news = fetch_medias24_news()
    
    # Handle stock fetch failures
    if stocks is None:
        log("Stock fetch failed, trying cache...", "WARNING")
        cached_stocks = load_cached_stocks()
        if cached_stocks:
            stocks = cached_stocks
            log("Using cached stocks", "INFO")
        else:
            stocks = load_fallback_stocks()
            log("Using fallback stocks", "WARNING")
    
    # Save all data
    save_data(stocks, news)
    
    # Final summary
    live_count = sum(1 for s in stocks if s.get('has_live_data', False))
    log("=" * 70)
    log(f"SCRAPING COMPLETE")
    log(f"• Total stocks: {len(stocks)} ({live_count} live, {len(stocks) - live_count} fallback)")
    log(f"• News items: {len(news)}")
    log(f"• Data directory: {DATA_DIR}")
    log("=" * 70)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        log("\nScraping interrupted by user", "WARNING")
        sys.exit(1)
    except Exception as e:
        log(f"Fatal error: {e}", "ERROR")
        sys.exit(1)
