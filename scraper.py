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

# Configuration
DATA_DIR = "data"
STOCKS_FILE = f"{DATA_DIR}/stocks.json"
NEWS_FILE = f"{DATA_DIR}/news.json"
UPDATE_FILE = f"{DATA_DIR}/last_update.txt"

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

# Build lookup dictionaries
STOCK_NAMES = {s["symbol"]: s["name"] for s in BASE_STOCKS}
STOCK_SECTORS = {s["symbol"]: s["sector"] for s in BASE_STOCKS}

def log(message, level="INFO"):
    """Print log messages"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def get_moroccan_stocks():
    """
    CRITICAL FIX: Merge TradingView data with ALL 54 BASE_STOCKS
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # FIX: Remove trailing space from URL
        url = "https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/"
        log(f"Fetching from TradingView: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            log(f"Failed to fetch data. Status: {response.status_code}", "ERROR")
            return None
            
        # Parse TradingView data into dict
        soup = BeautifulSoup(response.text, 'html.parser')
        tv_data = {}
        
        table = soup.find('table')
        if table:
            for row in table.find_all('tr')[1:]:  # Skip header
                cells = row.find_all('td')
                if len(cells) >= 3:
                    symbol_cell = cells[0].find('a')
                    if symbol_cell:
                        symbol = symbol_cell.text.strip()
                        try:
                            price = float(cells[1].text.strip().replace('MAD', '').replace(',', ''))
                            change = float(cells[2].text.strip().replace('%', '').replace('(', '-').replace(')', ''))
                            tv_data[symbol] = {'price': price, 'change': change}
                        except:
                            continue
        
        log(f"TradingView returned {len(tv_data)} stocks with live data")
        
        # CRITICAL: Build ALL 54 stocks, using TV data where available
        all_stocks = []
        for stock in BASE_STOCKS:
            symbol = stock['symbol']
            
            if symbol in tv_data:
                # Use live TradingView data
                price = tv_data[symbol]['price']
                change = tv_data[symbol]['change']
                has_data = True
                log(f"  ✓ {symbol}: {price:.2f} MAD ({change:+.2f}%) [LIVE]")
            else:
                # Use placeholder for stocks not in TV
                price = 0.0
                change = 0.0
                has_data = False
                log(f"  ○ {symbol}: No live data (placeholder)")
            
            # Generate trend
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
        
        # Sort: live data first, then alphabetically
        all_stocks.sort(key=lambda x: (not x['has_live_data'], x['symbol']))
        
        log(f"\n✓ Total: {len(all_stocks)} stocks ({len(tv_data)} with live data)")
        return all_stocks
        
    except Exception as e:
        log(f"Error: {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        return None

def parse_change(change_text):
    """Parse change percentage from text"""
    try:
        clean = change_text.replace('%', '').replace('+', '').replace('(', '-').replace(')', '').strip()
        return float(clean)
    except:
        return 0.0

def format_volume(vol_text):
    """Format volume text"""
    try:
        vol_text = vol_text.upper().replace(',', '')
        if 'K' in vol_text:
            return vol_text
        elif 'M' in vol_text:
            return vol_text
        elif 'B' in vol_text:
            return vol_text
        else:
            num = float(vol_text)
            if num >= 1000000:
                return f"{num/1000000:.2f}M"
            elif num >= 1000:
                return f"{num/1000:.2f}K"
            return str(int(num))
    except:
        return "N/A"

def generate_trend(price, change):
    """Generate 7-point trend line"""
    trend = []
    base = price / (1 + (change / 100)) if change != 0 else price * 0.995
    
    for i in range(7):
        noise = random.uniform(-0.002, 0.002) * price
        point = base + ((price - base) * (i / 6)) + noise
        trend.append(round(point, 2))
    
    return trend

def fetch_medias24_news():
    """
    Fetch news from Medias24 RSS feed
    """
    log("Fetching Medias24 RSS...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        # FIX: Remove trailing space
        url = "https://medias24.com/categorie/leboursier/actus/feed/"
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            log(f"RSS failed: {response.status_code}", "WARNING")
            return []
        
        # Parse XML properly
        root = ET.fromstring(response.content)
        
        # FIX: Find channel first
        channel = root.find('channel')
        if channel is None:
            log("No channel found in RSS", "ERROR")
            return []
        
        items = channel.findall('item')
        log(f"Found {len(items)} RSS items")
        
        news = []
        for i, item in enumerate(items[:20]):
            try:
                title_elem = item.find('title')
                title = title_elem.text if title_elem is not None else 'N/A'
                
                link_elem = item.find('link')
                link = link_elem.text if link_elem is not None else ''
                
                # Parse date properly
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
                    except Exception as e:
                        log(f"Date parse error: {e}", "WARNING")
                
                # Clean description
                summary = ''
                desc = item.find('description')
                if desc and desc.text:
                    soup = BeautifulSoup(desc.text, 'html.parser')
                    summary = soup.get_text(strip=True)
                    if "appeared first on" in summary:
                        summary = summary.split("appeared first on")[0].strip()
                    summary = summary[:200]
                
                # Get category
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
                log(f"  ✓ News {i+1}: {title[:45]}... ({time_mins}m)")
                
            except Exception as e:
                log(f"  ✗ Error item {i}: {e}", "WARNING")
                continue
        
        log(f"Successfully parsed {len(news)} news items")
        
        # Print summary to terminal
        print("\n" + "="*70)
        print("NEWS FETCHED FROM MEDIAS24 RSS:")
        print("="*70)
        for n in news[:5]:
            print(f"\n• {n['title'][:60]}...")
            print(f"  Link: {n['link'][:70]}")
            print(f"  Time: {n['time']}m ago | Category: {n['category']}")
        print(f"\nTotal: {len(news)} news items")
        print("="*70 + "\n")
        
        return news
        
    except Exception as e:
        log(f"RSS error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return []

def detect_category(title):
    """Detect news category"""
    title_lower = title.lower()
    if any(w in title_lower for w in ['resultat', 'rnpg', 'ca ', 'bilan', 'annuel']):
        return 'RAPPORT'
    elif any(w in title_lower for w in ['dividende']):
        return 'DIVIDENDE'
    elif any(w in title_lower for w in ['chute', 'hausse', 'baisse', 'recul', 'plonge']):
        return 'ALERTE'
    elif any(w in title_lower for w in ['lancement', 'projet', 'accord', 'signature', 'partenariat']):
        return 'FLASH'
    elif any(w in title_lower for w in ['analyse', 'etude', 'perspective', 'prevision']):
        return 'ANALYSE'
    return 'INFO'

def save_data(stocks, news):
    """Save to JSON files"""
    ensure_data_dir()
    
    with open(STOCKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stocks, f, ensure_ascii=False, indent=2)
    
    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(news, f, ensure_ascii=False, indent=2)
    
    with open(UPDATE_FILE, 'w') as f:
        f.write(datetime.now().isoformat())
    
    log(f"Saved: {len(stocks)} stocks, {len(news)} news")

def main():
    log("=" * 70)
    log("RISK NETWORK GROUP - Market Data Scraper")
    log(f"Total stock definitions: {len(BASE_STOCKS)}")
    log("=" * 70)
    
    # Fetch all 54 stocks
    stocks = get_moroccan_stocks()
    
    # Fetch news
    news = fetch_medias24_news()
    
    # Handle failure
    if stocks is None:
        log("CRITICAL: Stock fetch failed, using fallback", "ERROR")
        if os.path.exists(STOCKS_FILE):
            log("Keeping existing stock data")
            with open(STOCKS_FILE, 'r') as f:
                stocks = json.load(f)
        else:
            # Create placeholder data for all 54
            stocks = [{
                "symbol": s['symbol'],
                "name": s['name'],
                "sector": s['sector'],
                "price": 0.0,
                "change": 0.0,
                "volume": "N/A",
                "trend": [100.0] * 7,
                "has_live_data": False
            } for s in BASE_STOCKS]
    
    # Save everything
    save_data(stocks, news)
    
    # Final summary
    live_count = sum(1 for s in stocks if s.get('has_live_data', False))
    log("=" * 70)
    log(f"SCRAPER FINISHED")
    log(f"Stocks: {len(stocks)} total ({live_count} with live data)")
    log(f"News: {len(news)} items")
    log("=" * 70)

if __name__ == '__main__':
    main()
