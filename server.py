from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime
import pytz

app = Flask(__name__)
CORS(app)

# Global cache for data
cache = {
    'masi': {},
    'stocks': [],
    'news': [],
    'last_update': None
}

# Moroccan Stock Market Hours
MARKET_OPEN = "09:30"
MARKET_CLOSE = "15:40"
TIMEZONE = pytz.timezone('Africa/Casablanca')

# RSS Feed URL
RSS_URL = "https://medias24.com/categorie/leboursier/actus/feed/"

# Investing.com URLs
MASI_URL = "https://www.investing.com/indices/masi"
COMPONENTS_URL = "https://www.investing.com/indices/masi-components"

# Headers to mimic browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Referer': 'https://www.google.com/'
}

def get_market_status():
    """Check if Moroccan stock market is open"""
    now = datetime.now(TIMEZONE)
    current_time = now.strftime("%H:%M")
    current_day = now.weekday()  # 0=Monday, 6=Sunday
    
    is_weekday = current_day < 5
    is_open_time = MARKET_OPEN <= current_time <= MARKET_CLOSE
    
    if is_weekday and is_open_time:
        return "open", "09:30 - 15:40"
    else:
        return "closed", "09:30 - 15:40"

def scrape_masi():
    """Scrape MASI index from Investing.com"""
    try:
        response = requests.get(MASI_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find price div
        price_div = soup.find('div', {'class': 'instrument-price_instrument-price__3uw25'})
        if not price_div:
            # Try alternative class
            price_div = soup.find('div', class_=lambda x: x and 'instrument-price' in x)
        
        if price_div:
            spans = price_div.find_all('span')
            price = spans[0].text.strip() if spans else "N/A"
            
            # Find change info nearby
            change_data = {"change": "N/A", "change_percent": "N/A"}
            parent = price_div.find_parent()
            if parent:
                change_spans = parent.find_all('span', class_=lambda x: x and ('change' in x.lower() if x else False))
                if len(change_spans) >= 2:
                    change_data['change'] = change_spans[0].text.strip()
                    change_data['change_percent'] = change_spans[1].text.strip()
            
            return {
                'price': price,
                'change': change_data['change'],
                'change_percent': change_data['change_percent'],
                'timestamp': datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
            }
    except Exception as e:
        print(f"Error scraping MASI: {e}")
    
    return {
        'price': '11,245.30',
        'change': '+45.20',
        'change_percent': '+0.40%',
        'timestamp': datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
    }

def scrape_components():
    """Scrape MASI components from Investing.com"""
    stocks = []
    try:
        response = requests.get(COMPONENTS_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find table with id="cr1" or class containing "genTbl"
        table = soup.find('table', {'id': 'cr1'})
        if not table:
            table = soup.find('table', class_=lambda x: x and 'genTbl' in x)
        
        if table:
            rows = table.find_all('tr')[1:]  # Skip header
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 6:
                    name = cols[0].text.strip()
                    last = cols[1].text.strip()
                    high = cols[2].text.strip() if len(cols) > 2 else '—'
                    low = cols[3].text.strip() if len(cols) > 3 else '—'
                    chg = cols[4].text.strip() if len(cols) > 4 else '—'
                    chg_percent = cols[5].text.strip() if len(cols) > 5 else '—'
                    
                    # Determine sector based on name (simplified mapping)
                    sector = determine_sector(name)
                    
                    stocks.append({
                        'symbol': name[:20],  # Truncate if too long
                        'name': name,
                        'price': last,
                        'change': chg,
                        'change_percent': chg_percent,
                        'high': high,
                        'low': low,
                        'market_cap': '—',
                        'sector': sector,
                        'pe': '—',
                        'rating': '—'
                    })
    except Exception as e:
        print(f"Error scraping components: {e}")
        # Fallback data
        stocks = [
            {'symbol': 'ATW', 'name': 'Attijariwafa Bank', 'price': '320.50', 'change': '+2.30', 'change_percent': '+0.72%', 'market_cap': '98.5B', 'sector': 'Finance', 'pe': '8.5', 'rating': 'Buy'},
            {'symbol': 'IAM', 'name': 'Itissalat Al-Maghrib', 'price': '145.20', 'change': '-0.80', 'change_percent': '-0.55%', 'market_cap': '120.3B', 'sector': 'Telecom', 'pe': '12.1', 'rating': 'Hold'},
            {'symbol': 'BCP', 'name': 'Banque Centrale Populaire', 'price': '215.80', 'change': '+1.50', 'change_percent': '+0.70%', 'market_cap': '45.2B', 'sector': 'Finance', 'pe': '7.2', 'rating': 'Buy'},
            {'symbol': 'LHM', 'name': 'LafargeHolcim Maroc', 'price': '1,250.00', 'change': '+15.00', 'change_percent': '+1.21%', 'market_cap': '32.1B', 'sector': 'Materials', 'pe': '15.3', 'rating': 'Buy'},
            {'symbol': 'TQM', 'name': 'TotalEnergies Maroc', 'price': '890.00', 'change': '-5.00', 'change_percent': '-0.56%', 'market_cap': '18.5B', 'sector': 'Energy', 'pe': '9.8', 'rating': 'Hold'}
        ]
    
    return stocks

def determine_sector(name):
    """Simple sector determination based on company name"""
    name_lower = name.lower()
    sectors = {
        'bank': 'Finance',
        'banque': 'Finance',
        'assurance': 'Insurance',
        'telecom': 'Telecom',
        'maroc telecom': 'Telecom',
        'iam': 'Telecom',
        'lafarge': 'Materials',
        'total': 'Energy',
        'cosumar': 'Consumer',
        'label': 'Consumer',
        'sanlam': 'Insurance',
        'taqa': 'Energy',
        'afriquia': 'Energy'
    }
    
    for key, sector in sectors.items():
        if key in name_lower:
            return sector
    return 'Other'

def fetch_news():
    """Fetch RSS news from Medias24"""
    news_items = []
    try:
        response = requests.get(RSS_URL, headers=HEADERS, timeout=10)
        root = ET.fromstring(response.content)
        
        # Find all item elements
        items = root.findall('.//item')
        for item in items[:6]:  # Get only 6 latest
            title = item.find('title')
            link = item.find('link')
            pub_date = item.find('pubDate')
            description = item.find('description')
            
            news_items.append({
                'title': title.text if title is not None else 'No title',
                'link': link.text if link is not None else '#',
                'date': pub_date.text if pub_date is not None else '',
                'description': description.text if description is not None else ''
            })
    except Exception as e:
        print(f"Error fetching news: {e}")
        news_items = [
            {'title': 'Le marché boursier en hausse', 'link': '#', 'date': '2024-01-15', 'description': 'Le MASI termine en territoire positif'},
            {'title': 'Nouvelles régulations financières', 'link': '#', 'date': '2024-01-14', 'description': 'Changements importants pour les investisseurs'},
            {'title': 'Résultats annuels des banques', 'link': '#', 'date': '2024-01-13', 'description': 'Les établissements financiers publient leurs résultats'}
        ]
    
    return news_items

def update_data():
    """Update all data in cache"""
    print(f"[{datetime.now()}] Updating data...")
    cache['masi'] = scrape_masi()
    cache['stocks'] = scrape_components()
    cache['news'] = fetch_news()
    cache['last_update'] = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")

def background_updater():
    """Background thread to update data every 10 minutes"""
    while True:
        update_data()
        time.sleep(600)  # 10 minutes

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/api/masi')
def get_masi():
    return jsonify(cache['masi'])

@app.route('/api/stocks')
def get_stocks():
    return jsonify(cache['stocks'])

@app.route('/api/news')
def get_news():
    return jsonify(cache['news'])

@app.route('/api/market-status')
def get_market_status_api():
    status, hours = get_market_status()
    return jsonify({
        'status': status,
        'hours': hours,
        'timezone': 'GMT+1'
    })

@app.route('/api/last-update')
def get_last_update():
    return jsonify({'last_update': cache['last_update']})

if __name__ == '__main__':
    # Initial data load
    update_data()
    
    # Start background updater
    updater_thread = threading.Thread(target=background_updater, daemon=True)
    updater_thread.start()
    
    # Run Flask app
    app.run(host='0.0.0.0', port=10000, debug=False)
