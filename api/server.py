from flask import Flask, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# In-memory cache
cache = {
    'stocks': [],
    'news': [],
    'last_update': None
}

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
                                'volume': 'N/A',  # TradingView hides volume in free view
                                'trend': trend
                            })
                        except:
                            continue
        
        return stocks
    except Exception as e:
        print(f"Error scraping TradingView: {e}")
        return []

def scrape_boursenews():
    """Scrape BourseNews"""
    try:
        url = "https://boursenews.ma/espace-investisseurs"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        news = []
        articles = soup.select('article, .news-item, .post, .entry-title')
        
        for i, article in enumerate(articles[:20]):
            try:
                title_elem = article.select_one('h2, h3, .title, a')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    
                    news.append({
                        'time': i * 5,  # Approximate
                        'title': title,
                        'category': 'INFO',
                        'source': 'BourseNews.ma',
                        'date': datetime.now().strftime('%Y-%m-%d')
                    })
            except:
                continue
        
        return news
    except Exception as e:
        print(f"Error scraping BourseNews: {e}")
        return []

def get_stock_name(symbol):
    """Get full name from symbol"""
    names = {
        'ATW': 'Attijariwafa Bank SA',
        'BCP': 'Banque Centrale Populaire',
        'BOA': 'Bank of Africa SA',
        'CFG': 'CFG Bank SA',
        'CDM': 'Credit du Maroc',
        'CIH': 'CIH Bank SA',
        'BCI': 'BMCI SA',
        'IAM': 'Itissalat Al-Maghrib',
        'WAA': 'Wafa Assurance',
        'SAH': 'Sanlam Maroc',
        'ATL': 'AtlantaSanad',
        'ADH': 'Douja Promotion Addoha',
        'ADI': 'Alliances Dev Immobilier',
        'RDS': 'Residences Dar Saada',
        'LHM': 'LafargeHolcim Maroc',
        'CMA': 'Ciments du Maroc',
        'SID': 'SONASID SA',
        'TGC': 'Travaux Generaux Const',
        'JET': 'Jet Contractors',
        'GTM': 'SGTM SA',
        'MNG': 'Managem SA',
        'SMI': 'Societe Metallurgique Imiter',
        'CMT': 'Compagnie Miniere Touissit',
        'ZDJ': 'Zellidja SA',
        'TQM': 'TAQA Morocco SA',
        'GAZ': 'Afriquia Gaz SA',
        'TMA': 'TotalEnergies Marketing',
        'MSA': 'Marsa Maroc SA',
        'CTM': 'Compagnie Transport Maroc',
        'SOT': 'Sothema SA',
        'AKT': 'Akdital SA',
        'CSR': 'Cosumar SA',
        'LES': 'Lesieur Cristal SA',
        'SBM': 'Sté Boissons du Maroc',
        'DWY': 'Disway SA',
        'HPS': 'Hightech Payment Systems',
        'MIC': 'Microdata SA',
        'S2M': 'Sté Maghrébine Monétique',
        'LBV': 'Label Vie SA',
        'ATH': 'Auto Hall SA',
        'NAKL': 'Ennakl Automobiles',
        'CMG': 'CMGP Group',
        'MUT': 'Mutandis SCA',
        'EQD': 'EQDOM SA',
        'SLF': 'Salafin SA',
    }
    return names.get(symbol, symbol)

def get_sector(symbol):
    """Get sector from symbol"""
    sectors = {
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
    return sectors.get(symbol, 'DIVERS')

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
    # Initial scrape
    print("Initial scrape...")
    cache['stocks'] = scrape_tradingview()
    cache['news'] = scrape_boursenews()
    cache['last_update'] = datetime.now()
    print(f"Loaded {len(cache['stocks'])} stocks and {len(cache['news'])} news items")
    
    # Run server
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
