#!/usr/bin/env python3
"""
RISK NETWORK GROUP - Market Data Scraper
Fetches all Moroccan stocks from TradingView + Medias24 news
"""

import requests
import xml.etree.ElementTree as ET
import json
import os
import time
from datetime import datetime, timezone
from bs4 import BeautifulSoup

# Configuration
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

STOCKS_FILE = f"{DATA_DIR}/stocks.json"
NEWS_FILE = f"{DATA_DIR}/news.json"

# COMPLETE LIST - All 54+ Moroccan tickers
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

def scrape_tradingview():
    """
    Scrape Moroccan stocks from TradingView
    Returns: List of dicts with symbol, name, sector, price, change, has_live_data
    """
    url = "https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }
    
    try:
        print(f"[{datetime.now()}] Fetching TradingView data...")
        session = requests.Session()
        session.headers.update(headers)
        
        # Add retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = session.get(url, timeout=30)
                response.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise e
                print(f"Attempt {attempt + 1} failed, retrying...")
                time.sleep(2)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the table - TradingView uses specific structure
        table = soup.find('table', class_='table-Ngq2xrcG')
        if not table:
            # Fallback: find any table with stock data
            table = soup.find('table')
        
        if not table:
            print("No table found in HTML")
            return None
            
        print(f"Found table, parsing rows...")
        
        # Parse TradingView data into dict: symbol -> {price, change}
        tv_data = {}
        rows = table.find_all('tr')
        print(f"Total rows found: {len(rows)}")
        
        for i, row in enumerate(rows[1:], 1):  # Skip header
            try:
                cells = row.find_all('td')
                if len(cells) < 3:
                    continue
                
                # Extract symbol (first column, usually in an <a> tag)
                symbol_cell = cells[0]
                symbol_link = symbol_cell.find('a')
                symbol = symbol_link.text.strip() if symbol_link else symbol_cell.text.strip()
                
                if not symbol or len(symbol) < 2:
                    continue
                
                # Extract price (second column)
                price_cell = cells[1]
                price_text = price_cell.text.strip().replace('MAD', '').replace(',', '').replace(' ', '')
                
                # Extract change (third column)
                change_cell = cells[2]
                change_text = change_cell.text.strip().replace('%', '').replace('(', '-').replace(')', '').replace('+', '').replace(' ', '')
                
                # Clean and convert
                try:
                    price = float(price_text) if price_text else 0.0
                    change = float(change_text) if change_text else 0.0
                    
                    if price > 0:  # Only store if valid price
                        tv_data[symbol] = {
                            'price': price,
                            'change': change
                        }
                        print(f"  ✓ {symbol}: {price} MAD ({change}%)")
                except ValueError as e:
                    print(f"  ✗ Parse error for {symbol}: price='{price_text}', change='{change_text}'")
                    continue
                    
            except Exception as e:
                print(f"  ✗ Error parsing row {i}: {e}")
                continue
        
        print(f"\nSuccessfully parsed {len(tv_data)} stocks from TradingView")
        
        # Merge with BASE_STOCKS to ensure all 54 are included
        all_stocks = []
        for stock in BASE_STOCKS:
            symbol = stock['symbol']
            
            if symbol in tv_data:
                all_stocks.append({
                    'symbol': symbol,
                    'name': stock['name'],
                    'sector': stock['sector'],
                    'price': tv_data[symbol]['price'],
                    'change': tv_data[symbol]['change'],
                    'has_live_data': True
                })
            else:
                # Include stock even if not found (price 0, change 0)
                all_stocks.append({
                    'symbol': symbol,
                    'name': stock['name'],
                    'sector': stock['sector'],
                    'price': 0.0,
                    'change': 0.0,
                    'has_live_data': False
                })
        
        # Sort: live data first, then alphabetically by symbol
        all_stocks.sort(key=lambda x: (not x['has_live_data'], x['symbol']))
        
        live_count = sum(1 for s in all_stocks if s['has_live_data'])
        print(f"Total: {len(all_stocks)} stocks ({live_count} with live data, {len(all_stocks) - live_count} fallback)")
        
        return all_stocks
        
    except Exception as e:
        print(f"ERROR scraping TradingView: {e}")
        import traceback
        traceback.print_exc()
        return None

def scrape_medias24():
    """Scrape news from Medias24 RSS"""
    url = "https://medias24.com/categorie/leboursier/actus/feed/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        print(f"[{datetime.now()}] Fetching Medias24 RSS...")
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"RSS Error: Status {response.status_code}")
            return []
        
        # Parse XML
        try:
            root = ET.fromstring(response.content)
        except ET.ParseError:
            # Try with cleaned content
            content = response.content.decode('utf-8', errors='ignore')
            root = ET.fromstring(content)
        
        # Find items (handle both RSS 2.0 and Atom)
        items = root.findall('.//item')
        if not items:
            items = root.findall('.//{http://www.w3.org/2005/Atom}entry')
        
        news = []
        now = datetime.now(timezone.utc)
        
        for item in items[:20]:  # Top 20 news
            try:
                title = item.find('title')
                link = item.find('link')
                pubDate = item.find('pubDate')
                category = item.find('category')
                
                title_text = title.text if title is not None else 'Sans titre'
                
                # Handle link (text or href attribute)
                link_text = ''
                if link is not None:
                    link_text = link.text or link.get('href', '')
                
                date_text = pubDate.text if pubDate is not None else ''
                cat_text = category.text if category is not None else 'INFO'
                
                # Calculate minutes ago
                time_mins = 0
                if date_text:
                    try:
                        # Try multiple date formats
                        formats = [
                            '%a, %d %b %Y %H:%M:%S %z',
                            '%a, %d %b %Y %H:%M:%S %Z',
                            '%Y-%m-%dT%H:%M:%S%z'
                        ]
                        pub_date = None
                        for fmt in formats:
                            try:
                                pub_date = datetime.strptime(date_text.strip(), fmt)
                                break
                            except:
                                continue
                        
                        if pub_date:
                            if pub_date.tzinfo is None:
                                pub_date = pub_date.replace(tzinfo=timezone.utc)
                            diff = now - pub_date
                            time_mins = int(diff.total_seconds() / 60)
                    except Exception as e:
                        print(f"Date parse error: {e} for '{date_text}'")
                        time_mins = 0
                
                news.append({
                    'title': title_text,
                    'link': link_text,
                    'date': date_text,
                    'category': cat_text.upper(),
                    'time': max(0, time_mins),
                    'source': 'Medias24.com'
                })
                
            except Exception as e:
                print(f"Error parsing news item: {e}")
                continue
        
        print(f"Fetched {len(news)} news items")
        return news
        
    except Exception as e:
        print(f"ERROR scraping RSS: {e}")
        return []

def save_data(stocks, news):
    """Save data to JSON files"""
    try:
        with open(STOCKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stocks, f, ensure_ascii=False, indent=2)
        print(f"✓ Saved {len(stocks)} stocks to {STOCKS_FILE}")
    except Exception as e:
        print(f"Error saving stocks: {e}")
    
    try:
        with open(NEWS_FILE, 'w', encoding='utf-8') as f:
            json.dump(news, f, ensure_ascii=False, indent=2)
        print(f"✓ Saved {len(news)} news to {NEWS_FILE}")
    except Exception as e:
        print(f"Error saving news: {e}")

def main():
    print("=" * 60)
    print("RISK NETWORK GROUP - MARKET DATA SCRAPER")
    print("=" * 60)
    
    # Scrape stocks
    stocks = scrape_tradingview()
    if stocks is None:
        print("Using fallback data...")
        stocks = [{
            'symbol': s['symbol'],
            'name': s['name'],
            'sector': s['sector'],
            'price': 0.0,
            'change': 0.0,
            'has_live_data': False
        } for s in BASE_STOCKS]
    
    # Scrape news
    news = scrape_medias24()
    
    # Save everything
    save_data(stocks, news)
    
    # Summary
    live_count = sum(1 for s in stocks if s.get('has_live_data', False))
    print("\n" + "=" * 60)
    print(f"SCRAPING COMPLETE")
    print(f"Stocks: {len(stocks)} total ({live_count} live)")
    print(f"News: {len(news)} items")
    print("=" * 60)

if __name__ == '__main__':
    main()
