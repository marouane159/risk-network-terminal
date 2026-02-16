A high-performance, real-time stock market terminal focused on the Casablanca Stock Exchange (MASI). This project scrapes live data from TradingView and BMCE Capital to provide a consolidated dashboard for Moroccan market analysis.

🚀 Features
Live MASI Tracking: Real-time index price and daily variation.

Comprehensive Stock Scanner:

Ticker, Sector, and Market Cap.

Live Volume tracking (Formatted: K/M).

P/E Ratios and algorithmic Sentiment Ratings (Strong Buy to Strong Sell).

Multilingual Support: Fully localized in French (FR), English (EN), and Arabic (AR) (including RTL support).

Dynamic UI:

Toggleable columns (customize your workspace).

Search/Filter functionality.

Dark/Light mode support.

RSS News Feed: Latest Moroccan financial news integrated directly into the terminal.

🛠️ Tech Stack
Frontend: Vanilla JS, CSS3 (JetBrains Mono Typography), HTML5.

Backend: Python, Flask, Flask-CORS.

Data Sources:

TradingView (Scanner API)

BMCE Capital Bourse (MASI Index Scraper)

Risk.ma (RSS News Feed)

📦 Installation & Setup
Clone the repository

Bash
git clone https://github.com/your-username/risk-network-terminal.git
cd risk-network-terminal
Install Dependencies

Bash
pip install flask flask-cors requests beautifulsoup4
Run the Server

Bash
python server.py
Access the Terminal
Open your browser and navigate to http://localhost:5000

⚙️ Configuration
You can adjust the refresh rate in server.py:

Python
REFRESH_INTERVAL = 600  # Default: 10 minutes
⚠️ Disclaimer
Usage Éducatif Uniquement — Pas de Conseil Financier.
This tool is for educational and informational purposes only. Data is scraped from public sources and may be subject to delays. Always verify with official broker platforms before making investment decisions.

👨‍💻 Author
RISK NETWORK GROUP - Website: www.risk.ma
