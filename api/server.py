from flask import Flask, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

DATA_DIR = "data"
STOCKS_FILE = os.path.join(DATA_DIR, "stocks.json")
NEWS_FILE = os.path.join(DATA_DIR, "news.json")

def read_json(path):
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
    except:
        pass
    return []

@app.route('/')
def home():
    return "Risk Network API is Live"

@app.route('/api/stocks')
def get_stocks():
    return jsonify(read_json(STOCKS_FILE))

@app.route('/api/news')
def get_news():
    return jsonify(read_json(NEWS_FILE))

@app.route('/api/all')
def get_all():
    return jsonify({
        "stocks": read_json(STOCKS_FILE),
        "news": read_json(NEWS_FILE),
        "lastUpdate": datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
