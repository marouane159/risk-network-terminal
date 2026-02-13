#!/usr/bin/env python3
"""
RISK NETWORK GROUP - Market Data Scraper
Uses your working TradingView scraping method
"""

import requests
import xml.etree.ElementTree as ET
import json
import random
import os
import sys
from datetime import datetime
from bs4 import BeautifulSoup

# Configuration
DATA_DIR = "data"
STOCKS_FILE = f"{DATA_DIR}/stocks.json"
NEWS_FILE = f"{DATA_DIR}/news.json"
UPDATE_FILE = f"{DATA_DIR}/last_update.txt"

# Base stock info for matching symbols to names/sectors
BASE_STOCKS = [
    {"symbol": "ATW", "name": "Attijariwafa Bank SA", "sector": "BANK"},
    {"symbol": "BCP", "name": "Banque Centrale Populaire", "sector": "BANK"},
    {"symbol": "BOA", "name": "Bank of Africa SA", "sector": "BANK"},
    {"symbol": "CFG", "name": "CFG Bank SA", "sector": "BANK"},
    {"symbol": "CDM", "name": "Credit du Maroc", "sector": "BANK"},
    {"symbol": "CIH", "name": "CIH Bank SA", "sector": "BANK"},
    {"symbol": "BCI", "name": "BMCI SA", "sector": "BANK"},
    {"symbol": "IAM", "name": "Itissalat Al-Maghrib", "sector": "TELECOM"},
    {"symbol": "WAA", "name": "Wafa Assurance", "sector": "ASSUR"},
    {"symbol": "SAH", "name": "Sanlam Maroc", "sector": "ASSUR"},
    {"symbol": "ATL", "name": "AtlantaSanad", "sector": "ASSUR"},
    {"symbol": "ADH", "name": "Douja Promotion Addoha", "sector": "IMMO"},
    {"symbol": "ADI", "name": "Alliances Dev Immobilier", "sector": "IMMO"},
    {"symbol": "RDS", "name": "Residences Dar Saada", "sector": "IMMO"},
    {"symbol": "LHM", "name": "LafargeHolcim Maroc", "sector": "INDUS"},
    {"symbol": "CMA", "name": "Ciments du Maroc", "sector": "INDUS"},
    {"symbol": "SID", "name": "SONASID SA", "sector": "INDUS"},
    {"symbol": "TGC", "name": "Travaux Generaux Const", "sector": "INDUS"},
    {"symbol": "JET", "name": "Jet Contractors", "sector": "INDUS"},
    {"symbol": "GTM", "name": "SGTM SA", "sector": "INDUS"},
    {"symbol": "MNG", "name": "Managem SA", "sector": "MINES"},
    {"symbol": "SMI", "name": "Societe Metallurgique Imiter", "sector": "MINES"},
    {"symbol": "CMT", "name": "Compagnie Miniere Touissit", "sector": "MINES"},
    {"symbol": "ZDJ", "name": "Zellidja SA", "sector": "MINES"},
    {"symbol": "TQM", "name": "TAQA Morocco SA", "sector": "ENERGY"},
    {"symbol": "GAZ", "name": "Afriquia Gaz SA", "sector": "ENERGY"},
    {"symbol": "TMA", "name": "TotalEnergies Marketing", "sector": "ENERGY"},
    {"symbol": "MSA", "name": "Marsa Maroc SA", "sector": "TRANSPORT"},
    {"symbol": "CTM", "name": "Compagnie Transport Maroc", "sector": "TRANSPORT"},
    {"symbol": "SOT", "name": "Sothema SA", "sector": "SANTE"},
    {"symbol": "AKT", "name": "Akdital SA", "sector": "SANTE"},
    {"symbol": "CSR", "name": "Cosumar SA", "sector": "AGRO"},
    {"symbol": "LES", "name": "Lesieur Cristal SA", "sector": "AGRO"},
    {"symbol": "SBM", "name": "Sté Boissons du Maroc", "sector": "AGRO"},
    {"symbol": "DWY", "name": "Disway SA", "sector": "TECH"},
    {"symbol": "HPS", "name": "Hightech Payment Systems", "sector": "TECH"},
    {"symbol": "MIC", "name": "Microdata SA", "sector": "TECH"},
    {"symbol": "S2M", "name": "Sté Maghrébine Monétique", "sector": "TECH"},
    {"symbol": "LBV", "name": "Label Vie SA", "sector": "RETAIL"},
    {"symbol": "ATH", "name": "Auto Hall SA", "sector": "RETAIL"},
    {"symbol": "NAKL", "name": "Ennakl Automobiles", "sector": "RETAIL"},
    {"symbol": "CMG", "name": "CMGP Group", "sector": "HOLDING"},
    {"symbol": "MUT", "name": "Mutandis SCA", "sector": "HOLDING"},
    {"symbol": "EQD", "name": "EQDOM SA", "sector": "FINANCE"},
    {"symbol": "SLF", "name": "Salafin SA", "sector": "FINANCE"},
]

def log(message, level="INFO"):
    """Print log messages"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def get_moroccan_stocks():
    """
    YOUR WORKING METHOD - Scrapes TradingView HTML table
    """
    try:
        # Set up headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # Make the request
        url = "https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/"
        log(f"Fetching from: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            log(f"Failed to fetch data. Status code: {response.status_code}", "ERROR")
            return None
            
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the table
        table = soup.find('table')
        if not table:
            log("Could not find stock table on the page", "ERROR")
            return None
            
        # Extract data from table rows
        stocks_data = []
        log("Parsing table rows...")
        
        for row in table.find_all('tr')[1:]:  # Skip header row
            try:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    # Extract symbol and price
                    symbol_cell = cells[0].find('a')
                    if symbol_cell:
                        symbol = symbol_cell.text.strip()
                        price_text = cells[1].text.strip()
                        
                        # Clean and convert price
                        try:
                            price = float(price_text.replace('MAD', '').replace(',', '').strip())
                            
                            # Find matching stock in BASE_STOCKS
                            stock_info = next((s for s in BASE_STOCKS if s["symbol"] == symbol), None)
                            if stock_info:
                                # Calculate change (we need to get this from another cell)
                                change_text = cells[2].text.strip() if len(cells) > 2 else "0%"
                                change = parse_change(change_text)
                                
                                # Get volume if available
                                volume_text = cells[3].text.strip() if len(cells) > 3 else "0"
                                volume = format_volume(volume_text)
                                
                                # Generate trend
                                trend = generate_trend(price, change)
                                
                                stocks_data.append({
                                    "symbol": symbol,
                                    "name": stock_info["name"],
                                    "sector": stock_info["sector"],
                                    "price": price,
                                    "change": change,
                                    "volume": volume,
                                    "trend": trend
                                })
                                log(f"Got {symbol}: {price} MAD ({change:+.2f}%)")
                        except ValueError as e:
                            log(f"Could not parse price for {symbol}: {price_text} - {e}", "WARNING")
                            continue
            except Exception as e:
                log(f"Error processing row: {str(e)}", "WARNING")
                continue
        
        if not stocks_data:
            log("No valid stock data could be retrieved from TradingView", "ERROR")
            return None
            
        log(f"Successfully retrieved {len(stocks_data)} stocks")
        return stocks_data
        
    except Exception as e:
        log(f"Error while fetching stock data: {str(e)}", "ERROR")
        return None

def parse_change(change_text):
    """Parse change percentage from text"""
    try:
        # Remove % and + signs, handle parentheses
        clean = change_text.replace('%', '').replace('+', '').replace('(', '-').replace(')', '').strip()
        return float(clean)
    except:
        return 0.0

def format_volume(vol_text):
    """Format volume text"""
    try:
        # Handle K, M, B suffixes
        vol_text = vol_text.upper().replace(',', '')
        if 'K' in vol_text:
            return vol_text
        elif 'M' in vol_text:
            return vol_text
        elif 'B' in vol_text:
            return vol_text
        else:
            # Raw number, format it
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
    Fetch news from Medias24 RSS feed (Le Boursier)
    """
    log("Fetching Medias24 RSS...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        url = "https://medias24.com/categorie/leboursier/actus/feed/"
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            log(f"Medias24 RSS failed: {response.status_code}", "WARNING")
            return []
        
        # Parse XML
        root = ET.fromstring(response.content)
        news = []
        
        # Find all items
        items = root.findall('.//item')
        log(f"Found {len(items)} items in RSS feed")
        
        for i, item in enumerate(items[:15]):
            try:
                # Extract title
                title_elem = item.find('title')
                title = title_elem.text if title_elem is not None else 'N/A'
                
                # Extract link
                link_elem = item.find('link')
                link = link_elem.text if link_elem is not None else ''
                
                # Extract pub date
                date_elem = item.find('pubDate')
                if date_elem is not None:
                    date_str = date_elem.text
                    try:
                        # Parse RSS date format: Mon, 13 Feb 2025 10:30:00 +0000
                        from datetime import timezone
                        date_obj = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
                        date = date_obj.strftime('%Y-%m-%d %H:%M')
                        # Calculate minutes ago
                        now = datetime.now(timezone.utc)
                        diff = (now - date_obj).total_seconds() / 60
                        time_mins = int(diff) if diff > 0 else 0
                    except:
                        date = datetime.now().strftime('%Y-%m-%d')
                        time_mins = i * 5
                else:
                    date = datetime.now().strftime('%Y-%m-%d')
                    time_mins = i * 5
                
                # Extract description/summary
                desc_elem = item.find('description')
                summary = ''
                if desc_elem is not None and desc_elem.text:
                    # Clean HTML from description
                    soup = BeautifulSoup(desc_elem.text, 'html.parser')
                    summary = soup.get_text(strip=True)[:200]  # Limit to 200 chars
                
                # Extract category if available
                cat_elem = item.find('category')
                category = cat_elem.text if cat_elem is not None else detect_category(title)
                
                news.append({
                    'time': time_mins,
                    'title': title,
                    'link': link,
                    'category': category.upper(),
                    'source': 'Medias24.com',
                    'date': date,
                    'summary': summary
                })
                
                log(f"News: {title[:50]}... [{category}]")
                
            except Exception as e:
                log(f"Error parsing RSS item {i}: {e}", "WARNING")
                continue
        
        log(f"Got {len(news)} news items from Medias24")
        return news
        
    except Exception as e:
        log(f"Medias24 RSS error: {e}", "ERROR")
        return []

def parse_time(time_str):
    """Parse relative time"""
    try:
        if 'min' in time_str.lower():
            import re
            match = re.search(r'(\d+)', time_str)
            return int(match.group(1)) if match else 0
        if 'h' in time_str.lower():
            import re
            match = re.search(r'(\d+)', time_str)
            return int(match.group(1)) * 60 if match else 0
        return random.randint(10, 120)
    except:
        return random.randint(10, 120)

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
    log("=" * 60)
    log("RISK NETWORK GROUP - Market Data Scraper")
    log("=" * 60)
    
    # Fetch stocks using YOUR working method
    stocks = get_moroccan_stocks()
    
    # Fetch news
    news = fetch_medias24_news()
    
    # If stocks failed, we can't proceed
    if stocks is None:
        log("CRITICAL: Stock fetch failed, using fallback", "ERROR")
        # Try to keep old data
        if os.path.exists(STOCKS_FILE):
            log("Keeping existing stock data")
            with open(STOCKS_FILE, 'r') as f:
                stocks = json.load(f)
        else:
            stocks = []
    
    # Save everything
    save_data(stocks, news)
    
    log("=" * 60)
    log("Scraper finished")
    log("=" * 60)

if __name__ == '__main__':
    main()
