# RISK Network Terminal

A professional Bloomberg Terminal-style dashboard for the Casablanca Stock Exchange (Bourse de Casablanca).

## Features

- **Real-time Stock Data**: Scrapes all Moroccan stocks from TradingView with columns: Symbol, Market Cap, Sector, Price, Change %, P/E, Analyst Rating
- **MASI Index**: Live MASI index price and change percentage
- **Market Hours**: Displays Moroccan stock market status (Open: 09:30-15:40, Monday-Friday)
- **RSS News Feed**: Latest headlines from Medias24 Le Boursier
- **Language Selector**: Full support for French, English, and Arabic (RTL)
- **Theme Switcher**: Dark/Light mode toggle
- **Auto-refresh**: Data updates every 10 minutes automatically
- **Bloomberg Terminal Styling**: Professional financial terminal interface

## Tech Stack

- **Frontend**: React + TypeScript + Vite + Tailwind CSS + shadcn/ui
- **Backend**: Flask + Python
- **Data Sources**: TradingView (scraping), Medias24 RSS

## Deployment

### Frontend (Static)

The frontend is built as a static site in the `dist/` folder.

### Backend (Render)

To deploy the backend on Render:

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set the following:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python server.py`
   - **Environment**: Python 3
4. Add environment variable:
   - `PORT`: 5000 (or let Render assign one)

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt
npm install

# Run backend
python server.py

# Run frontend (in another terminal)
npm run dev
```

## API Endpoints

- `GET /api/stocks` - Get all stocks data
- `GET /api/news` - Get RSS news feed
- `GET /api/masi` - Get MASI index data
- `GET /api/market-status` - Get market open/closed status
- `GET /api/all` - Get all data in one request
- `POST /api/refresh` - Force refresh all data

## Stock List

Complete list of 60+ Moroccan stocks including:
- ATW (Attijariwafa Bank)
- IAM (Maroc Telecom)
- BCP (Banque Centrale Populaire)
- CIH (Crédit Immobilier et Hôtelier)
- LHM (LafargeHolcim)
- And many more...

## License

© 2024 RISK Network Group. All rights reserved.
