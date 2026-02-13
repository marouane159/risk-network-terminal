from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import requests
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

DATA_DIR = "data"
STOCKS_FILE = f"{DATA_DIR}/stocks.json"
NEWS_FILE = f"{DATA_DIR}/news.json"
RSS_URL = "https://medias24.com/categorie/leboursier/actus/feed/"

def load_json_data():
    """Load local JSON data"""
    stocks = []
    news = []
    
    try:
        if os.path.exists(STOCKS_FILE):
            with open(STOCKS_FILE, 'r', encoding='utf-8') as f:
                stocks = json.load(f)
    except:
        pass
    
    try:
        if os.path.exists(NEWS_FILE):
            with open(NEWS_FILE, 'r', encoding='utf-8') as f:
                news = json.load(f)
    except:
        pass
    
    return stocks, news

def fetch_rss():
    """Fetch and parse Medias24 RSS feed"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(RSS_URL, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        
        root = ET.fromstring(response.content)
        items = root.findall('.//item')
        
        news = []
        for item in items[:15]:  # Get top 15
            title = item.find('title')
            link = item.find('link')
            pubDate = item.find('pubDate')
            category = item.find('category')
            
            title_text = title.text if title is not None else 'Sans titre'
            link_text = link.text if link is not None else '#'
            date_text = pubDate.text if pubDate is not None else ''
            cat_text = category.text if category is not None else 'INFO'
            
            # Calculate minutes ago
            time_mins = 0
            if date_text:
                try:
                    pub_date = datetime.strptime(date_text, '%a, %d %b %Y %H:%M:%S %z')
                    diff = datetime.now(timezone.utc) - pub_date
                    time_mins = int(diff.total_seconds() / 60)
                except:
                    time_mins = 0
            
            news.append({
                'title': title_text,
                'link': link_text,
                'date': date_text,
                'category': cat_text.upper(),
                'time': time_mins,
                'source': 'Medias24.com'
            })
        
        return news
    except Exception as e:
        print(f"RSS Error: {e}")
        return []

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/stocks')
def get_stocks():
    stocks, _ = load_json_data()
    return jsonify(stocks)

@app.route('/api/news')
def get_news():
    # Try to fetch fresh RSS, fallback to file if fails
    fresh_news = fetch_rss()
    if fresh_news:
        return jsonify(fresh_news)
    
    # Fallback to cached news
    _, news = load_json_data()
    return jsonify(news)

@app.route('/api/all')
def get_all():
    stocks, cached_news = load_json_data()
    fresh_news = fetch_rss()
    news = fresh_news if fresh_news else cached_news
    
    return jsonify({
        'stocks': stocks,
        'news': news,
        'updated': datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
