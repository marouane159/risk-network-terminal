from flask import Flask, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Complete expanded stock list (your new tickers)
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
    print("LATEST NEWS FROM BOURSE NEWS (boursenews.ma/espace-investisseurs)")
    print("="*80)
    
    for i, item in enumerate(news_items[:10], 1):  # Show top 10
        print(f"\n{i}. {item.get('title', 'N/A')}")
        print(f"   Date: {item.get('date', 'N/A')}")
        print(f"   Source: {item.get('source', 'N/A')}")
        if item.get('summary'):
            print(f"   Summary: {item['summary'][:150]}...")
        print("-" * 80)
    
    print(f"\nTotal news items fetched: {len(news_items)}")
    print("="*80 + "\n")

def scrape_tradingview():
    """Scrape TradingView Morocco"""
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
        
        response = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        stocks = []
        table = soup.find('table')
        
        if table:
            rows = table.find_all('tr')[1:]  # Skip header
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 4:
                    symbol_elem = cells[0].find('a')
                    if symbol_elem:
                        symbol = symbol_elem.text.strip()
                        price_text = cells[1].text.strip().replace('MAD', '').replace(',', '')
                        change_text = cells[2].text.strip().replace('%', '')
                        
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
                        except:
                            continue
        
        return stocks
    except Exception as e:
        print(f"Error scraping TradingView: {e}")
        return []

def scrape_boursenews():
    """Scrape BourseNews from espace-investisseurs"""
    try:
        url = "https://boursenews.ma/espace-investisseurs"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        
        print(f"Fetching news from {url}...")
        response = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        news = []
        
        # Try multiple selectors to find articles
        selectors = [
            'article.news-item',
            '.news-item',
            'article',
            '.post',
            '.entry',
            '[class*="news"]',
            '.item'
        ]
        
        articles = []
        for selector in selectors:
            articles = soup.select(selector)
            if articles:
                print(f"Found {len(articles)} articles with selector: {selector}")
                break
        
        if not articles:
            # Fallback: look for any link with news-like structure
            articles = soup.find_all('a', href=lambda x: x and ('actualite' in x or 'news' in x or 'article' in x))
            print(f"Fallback found {len(articles)} articles")
        
        for i, article in enumerate(articles[:20]):
            try:
                # Extract title
                title_elem = article.find(['h1', 'h2', 'h3', 'h4', '.title', '.entry-title'])
                if not title_elem:
                    title_elem = article
                
                title = title_elem.get_text(strip=True)
                if not title or len(title) < 10:
                    continue
                
                # Extract link
                link = article.get('href', '')
                if not link:
                    link_elem = article.find('a')
                    if link_elem:
                        link = link_elem.get('href', '')
                
                if link and not link.startswith('http'):
                    link = 'https://boursenews.ma' + link
                
                # Extract date
                date_elem = article.find(['time', '.date', '.entry-date', '[class*="date"]'])
                date = date_elem.get_text(strip=True) if date_elem else datetime.now().strftime('%Y-%m-%d')
                
                # Extract summary
                summary_elem = article.find(['p', '.summary', '.excerpt', '.description'])
                summary = summary_elem.get_text(strip=True) if summary_elem else None
                
                news.append({
                    'time': i * 5,
                    'title': title,
                    'link': link,
                    'category': 'INFO',
                    'source': 'BourseNews.ma',
                    'date': date,
                    'summary': summary
                })
            except Exception as e:
                print(f"Error parsing article {i}: {e}")
                continue
        
        # Print news to terminal
        print_news_to_terminal(news)
        
        return news
    except Exception as e:
        print(f"Error scraping BourseNews: {e}")
        return []

def get_stock_name(symbol):
    """Get full name from symbol - uses BASE_STOCKS first, then fallback"""
    # First check our expanded list
    if symbol in STOCK_NAMES:
        return STOCK_NAMES[symbol]
    
    # Fallback to old hardcoded names
    fallback_names = {
        'ATW': 'Attijariwafa Bank SA',
        'BCP': 'Banque Centrale Populaire',
        'BOA': 'Bank of Africa SA',
        'BCI': 'BMCI SA',
        'BCE': 'Banque Marocaine du Commerce Extérieur',
        'AXC': 'AXA Credit',
        'MAB': 'Maghrebail',
        'MLE': 'Maroc Leasing',
        'SAH': 'Sanlam Maroc',
        'AGM': 'AGMA Lahlou-Tazi',
        'TSF': 'Taslif',
        'CMA': 'Ciments du Maroc',
        'GTM': 'SGTM SA',
        'VCN': 'Vicenne',
        'FBR': 'Fenie Brossette',
        'SRM': 'Sté Realisations Mecaniques',
        'ALM': 'Aluminium du Maroc',
        'GAZ': 'Afriquia Gaz SA',
        'NEJ': 'Nouvelles Energies de Jorf',
        'SBM': 'Sté Boissons du Maroc',
        'OUL': 'Oulmes',
        'CDA': 'Centrale Danone',
        'M2M': 'M2M Group',
        'IBC': 'IBC Corp',
        'CAP': 'Cap Radio',
        'DIS': 'Dislog Group',
        'PRO': 'Promopharm',
        'SLF': 'Salafin',
        'NAKL': 'Ennakl Automobiles',
    }
    return fallback_names.get(symbol, symbol)

def get_sector(symbol):
    """Get sector from symbol - uses BASE_STOCKS first, then fallback"""
    # First check our expanded list
    if symbol in STOCK_SECTORS:
        return STOCK_SECTORS[symbol]
    
    # Fallback to old hardcoded sectors
    fallback_sectors = {
        'ATW': 'BANK', 'BCP': 'BANK', 'BOA': 'BANK', 'CFG': 'BANK', 'CDM': 'BANK',
        'CIH': 'BANK', 'BCI': 'BANK', 'BCE': 'BANK', 'AXC': 'BANK', 'MAB': 'BANK', 'MLE': 'BANK',
        'IAM': 'TELECOM',
        'WAA': 'ASSUR', 'SAH': 'ASSUR', 'ATL': 'ASSUR', 'AFM': 'ASSUR', 'AGM': 'ASSUR', 'TSF': 'ASSUR',
        'ADH': 'IMMO', 'ADI': 'IMMO', 'RDS': 'IMMO', 'ARD': 'IMMO', 'IMO': 'IMMO', 'BAL': 'IMMO',
        'LHM': 'INDUS', 'CMA': 'INDUS', 'SID': 'INDUS', 'TGC': 'INDUS', 'JET': 'INDUS', 'GTM': 'INDUS',
        'VCN': 'INDUS', 'FBR': 'INDUS', 'SRM': 'INDUS', 'STR': 'INDUS', 'ALM': 'INDUS', 'DHO': 'INDUS',
        'MNG': 'MINES', 'SMI': 'MINES', 'CMT': 'MINES', 'ZDJ': 'MINES', 'COL': 'MINES', 'MDP': 'MINES',
        'TQM': 'ENERGY', 'GAZ': 'ENERGY', 'TMA': 'ENERGY', 'SNP': 'ENERGY', 'SAM': 'ENERGY',
        'MSA': 'TRANSPORT', 'CTM': 'TRANSPORT', 'NEJ': 'TRANSPORT',
        'SOT': 'SANTE', 'AKT': 'SANTE', 'PRO': 'SANTE',
        'CSR': 'AGRO', 'LES': 'AGRO', 'SBM': 'AGRO', 'OUL': 'AGRO', 'UMR': 'AGRO', 'CRS': 'AGRO', 'DRI': 'AGRO', 'CDA': 'AGRO',
        'DWY': 'TECH', 'HPS': 'TECH', 'MIC': 'TECH', 'S2M': 'TECH', 'DYT': 'TECH', 'M2M': 'TECH', 'INV': 'TECH', 'IBC': 'TECH',
        'LBV': 'RETAIL', 'ATH': 'RETAIL', 'NAKL': 'RETAIL', 'RIS': 'RETAIL', 'CAP': 'RETAIL',
        'CMG': 'HOLDING', 'MUT': 'HOLDING', 'SNA': 'HOLDING',
        'EQD': 'FINANCE', 'SLF': 'FINANCE', 'DIS': 'FINANCE',
    }
    return fallback_sectors.get(symbol, 'DIVERS')

@app.route('/')
def home():
    return "RISK NETWORK GROUP API - Use /api/stocks or /api/news"

@app.route('/api/stocks')
def get_stocks():
    """Get stocks (fresh or cached)"""
    global cache
    
    # Refresh if cache is old (30 seconds)
    if (not cache['last_update'] or 
        (datetime.now() - cache['last_update']).seconds > 30):
        
        print("Refreshing cache...")
        cache['stocks'] = scrape_tradingview()
        cache['news'] = scrape_boursenews()
        cache['last_update'] = datetime.now()
    
    return jsonify(cache['stocks'])

@app.route('/api/news')
def get_news():
    """Get news (fresh or cached)"""
    global cache
    
    if (not cache['last_update'] or 
        (datetime.now() - cache['last_update']).seconds > 30):
        
        cache['stocks'] = scrape_tradingview()
        cache['news'] = scrape_boursenews()
        cache['last_update'] = datetime.now()
    
    return jsonify(cache['news'])

@app.route('/api/all')
def get_all():
    """Get everything"""
    global cache
    
    if (not cache['last_update'] or 
        (datetime.now() - cache['last_update']).seconds > 30):
        
        cache['stocks'] = scrape_tradingview()
        cache['news'] = scrape_boursenews()
        cache['last_update'] = datetime.now()
    
    return jsonify({
        'stocks': cache['stocks'],
        'news': cache['news'],
        'lastUpdate': cache['last_update'].isoformat() if cache['last_update'] else None
    })

if __name__ == '__main__':
    # Print loaded stocks at startup
    print("\n" + "="*80)
    print(f"LOADED STOCKS ({len(BASE_STOCKS)} total)")
    print("="*80)
    for stock in BASE_STOCKS:
        print(f"  {stock['symbol']:<6} | {stock['name']:<35} | {stock['sector']}")
    print("="*80 + "\n")
    
    # Initial scrape
    print("Initial scrape...")
    cache['stocks'] = scrape_tradingview()
    cache['news'] = scrape_boursenews()
    cache['last_update'] = datetime.now()
    print(f"Loaded {len(cache['stocks'])} stocks and {len(cache['news'])} news items")
    
    # Run server
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
