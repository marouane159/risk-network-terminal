#!/usr/bin/env python3
"""
RISK NETWORK GROUP - Market Data Scraper
Fetches all 54 tickers + Medias24 news
"""

import requests
import xml.etree.ElementTree as ET
import json
import os
import re
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Configuration
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

STOCKS_FILE = f"{DATA_DIR}/stocks.json"
NEWS_FILE = f"{DATA_DIR}/news.json"

# COMPLETE LIST - All 54 tickers from your targeted list
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
    """Scrape stock data from TradingView"""
    try:
        url = "https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Parse TradingView data
        tv_data = {}
        table = soup.find('table')
        
        if table:
            for row in table.find_all('tr')[1:]:
                try:
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
                                tv_data[symbol] = {'price': price, 'change': change}
                            except:
                                continue
                except:
                    continue
        
        print(f"TradingView returned {len(tv_data)} stocks")
        
        # Merge with complete BASE_STOCKS list
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
                # Include stock even if not found on TradingView (shows 0)
                all_stocks.append({
                    'symbol': symbol,
                    'name': stock['name'],
                    'sector': stock['sector'],
                    'price': 0.0,
                    'change': 0.0,
                    'has_live_data': False
                })
        
        # Sort: live data first, then alphabetically
        all_stocks.sort(key=lambda x: (not x['has_live_data'], x['symbol']))
        
        return all_stocks
        
    except Exception as e:
        print(f"Error scraping TradingView: {e}")
        # Return all stocks with zero data if scrape fails
        return [{
            'symbol': s['symbol'],
            'name': s['name'],
            'sector': s['sector'],
            'price': 0.0,
            'change': 0.0,
            'has_live_data': False
        } for s in BASE_STOCKS]

def scrape_medias24():
    """Scrape news from Medias24 RSS"""
    try:
        url = "https://medias24.com/categorie/leboursier/actus/feed/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        
        root = ET.fromstring(response.content)
        items = root.findall('.//item')
        
        news = []
        for item in items[:15]:
            title = item.find('title').text if item.find('title') is not None else 'N/A'
            link = item.find('link').text if item.find('link') is not None else ''
            pubDate = item.find('pubDate').text if item.find('pubDate') is not None else ''
            category = item.find('category').text if item.find('category') is not None else 'INFO'
            
            # Calculate minutes ago
            time_mins = 0
            if pubDate:
                try:
                    pub_date = datetime.strptime(pubDate, '%a, %d %b %Y %H:%M:%S %z')
                    diff = datetime.now(timezone.utc) - pub_date
                    time_mins = int(diff.total_seconds() / 60)
                except:
                    time_mins = 0
            
            news.append({
                'title': title,
                'link': link,
                'date': pubDate,
                'category': category.upper(),
                'time': time_mins,
                'source': 'Medias24.com'
            })
        
        return news
    except Exception as e:
        print(f"Error scraping news: {e}")
        return []

def main():
    print("Scraping stocks from TradingView...")
    stocks = scrape_tradingview()
    with open(STOCKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stocks, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(stocks)} stocks")
    
    print("Scraping news from Medias24...")
    news = scrape_medias24()
    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(news, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(news)} news items")

if __name__ == '__main__':
    main()
