import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
from dataclasses import dataclass, asdict
from typing import List, Optional
import logging

# Configure logging to show in terminal
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # This ensures output goes to terminal
    ]
)
logger = logging.getLogger(__name__)

# Complete expanded stock list
BASE_STOCKS = [
    {"symbol": "TGC", "name": "TRAVAUX GENERAUX DE CONSTRUCTIONS", "sector": "Construction"},
    {"symbol": "TMA", "name": "TOTALENERGIES MARKETING ", "sector": "Énergie"},
    {"symbol": "TQM", "name": "TAQA MOROCCO", "sector": "Énergie"},
    {"symbol": "NKL", "name": "ENNAKL SA", "sector": "Transport"},
    {"symbol": "LHM", "name": "LAFARGEHOLCIM", "sector": "Construction"},
    {"symbol": "UMR", "name": "UNIMER", "sector": "Agroalimentaire"},
    {"symbol": "WAA", "name": "WAFA ASSURANCE", "sector": "Assurance"},
    {"symbol": "ZDJ", "name": "ZELLIDJA S.A", "sector": "Mines"},
    {"symbol": "MSA", "name": "SODEP MARSA ", "sector": "Transport"},
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
    {"symbol": "ALM", "name": "ALUMINIUM DU ", "sector": "Matériaux"},
    {"symbol": "ARD", "name": "ARADEI CAPITAL", "sector": "Immobilier"},
    {"symbol": "ATH", "name": "AUTO HALL", "sector": "Automobile"},
    {"symbol": "ATL", "name": "ATLANTASANAD", "sector": "Distribution"},
    {"symbol": "ATW", "name": "ATTIJARIWAFA BANK", "sector": "Banque"},
    {"symbol": "BAL", "name": "BALIMA", "sector": "Distribution"},
    {"symbol": "BCP", "name": "BANQUE CENTRALE POPULAIRE", "sector": "Banque"},
    {"symbol": "CRS", "name": "CARTIER SAADA", "sector": "Distribution"},
    {"symbol": "CIH", "name": "CREDIT IMMOBILIER ET HOTELIER", "sector": "Banque"},
    {"symbol": "CMT", "name": "CIMENTS DU ", "sector": "Matériaux"},
    {"symbol": "COL", "name": "COLORADO", "sector": "Distribution"},
    {"symbol": "CTM", "name": "COMPAGNIE DE TRANSPORTS AU ", "sector": "Transport"},
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

@dataclass
class StockPrice:
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int
    timestamp: str

@dataclass
class NewsItem:
    title: str
    link: str
    source: str
    date: str
    summary: Optional[str] = None

class BourseNewsScraper:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_news(self) -> List[NewsItem]:
        """Fetch news from boursenews.ma/espace-investisseurs"""
        url = "https://boursenews.ma/espace-investisseurs"
        
        try:
            logger.info(f"Fetching news from {url}...")
            async with self.session.get(url, timeout=30) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch news: HTTP {response.status}")
                    return []
                
                html = await response.text()
                logger.info(f"Successfully fetched {len(html)} bytes of HTML")
                
                news_items = self._parse_news(html)
                logger.info(f"Parsed {len(news_items)} news items")
                
                # Print news to terminal
                self._print_news_to_terminal(news_items)
                
                return news_items
                
        except Exception as e:
            logger.error(f"Error fetching news: {str(e)}")
            return []
    
    def _parse_news(self, html: str) -> List[NewsItem]:
        """Parse HTML to extract news items"""
        soup = BeautifulSoup(html, 'html.parser')
        news_items = []
        
        # Common selectors for news articles on boursenews.ma
        # Try multiple possible selectors
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
                logger.info(f"Found {len(articles)} articles with selector: {selector}")
                break
        
        if not articles:
            # Fallback: look for any link with news-like structure
            articles = soup.find_all('a', href=re.compile(r'/(actualite|news|article)/'))
            logger.info(f"Fallback found {len(articles)} articles")
        
        for article in articles[:20]:  # Limit to 20 most recent
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
                date = date_elem.get_text(strip=True) if date_elem else datetime.now().strftime("%Y-%m-%d")
                
                # Extract summary
                summary_elem = article.find(['p', '.summary', '.excerpt', '.description'])
                summary = summary_elem.get_text(strip=True) if summary_elem else None
                
                if title and link:
                    news_items.append(NewsItem(
                        title=title,
                        link=link,
                        source="Bourse News",
                        date=date,
                        summary=summary
                    ))
                    
            except Exception as e:
                logger.warning(f"Error parsing article: {e}")
                continue
        
        return news_items
    
    def _print_news_to_terminal(self, news_items: List[NewsItem]):
        """Print fetched news to terminal"""
        if not news_items:
            logger.warning("No news items to display")
            return
        
        print("\n" + "="*80)
        print("LATEST NEWS FROM BOURSE NEWS (boursenews.ma/espace-investisseurs)")
        print("="*80)
        
        for i, item in enumerate(news_items[:10], 1):  # Show top 10
            print(f"\n{i}. {item.title}")
            print(f"   Date: {item.date}")
            print(f"   Link: {item.link}")
            if item.summary:
                print(f"   Summary: {item.summary[:150]}...")
            print("-" * 80)
        
        print(f"\nTotal news items fetched: {len(news_items)}")
        print("="*80 + "\n")

class StockDataFetcher:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_stock_data(self, symbol: str) -> Optional[StockPrice]:
        """Fetch stock data for a given symbol"""
        # This is a placeholder - implement actual API call
        # You might need to use Casablanca Stock Exchange API or scrape data
        
        try:
            # Example implementation - replace with actual data source
            logger.info(f"Fetching data for {symbol}...")
            
            # Simulate API call or implement actual scraping
            # For now, returning mock data structure
            return StockPrice(
                symbol=symbol,
                price=0.0,
                change=0.0,
                change_percent=0.0,
                volume=0,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            return None

class Server:
    def __init__(self):
        self.stocks = BASE_STOCKS
        self.news_scraper = BourseNewsScraper()
        self.stock_fetcher = StockDataFetcher()
        self.cache = {
            'news': [],
            'stocks': [],
            'last_update': None
        }
    
    async def initialize(self):
        """Initialize server and fetch initial data"""
        logger.info("Initializing server...")
        logger.info(f"Loaded {len(self.stocks)} stocks")
        
        # Print stock list to terminal
        self._print_stock_list()
        
        # Fetch initial news
        async with self.news_scraper as scraper:
            self.cache['news'] = await scraper.fetch_news()
        
        self.cache['last_update'] = datetime.now()
        logger.info("Server initialization complete")
    
    def _print_stock_list(self):
        """Print loaded stocks to terminal"""
        print("\n" + "="*80)
        print(f"LOADED STOCKS ({len(self.stocks)} total)")
        print("="*80)
        
        for stock in self.stocks:
            print(f"  {stock['symbol']:<6} | {stock['name']:<35} | {stock['sector']}")
        
        print("="*80 + "\n")
    
    async def update_data(self):
        """Update all data (news and stocks)"""
        logger.info("Starting data update cycle...")
        
        # Update news
        async with self.news_scraper as scraper:
            self.cache['news'] = await scraper.fetch_news()
        
        # Update stock prices
        async with self.stock_fetcher as fetcher:
            stock_data = []
            for stock in self.stocks:
                data = await fetcher.fetch_stock_data(stock['symbol'])
                if data:
                    stock_data.append(asdict(data))
            self.cache['stocks'] = stock_data
        
        self.cache['last_update'] = datetime.now()
        logger.info("Data update cycle complete")
    
    def get_data(self):
        """Get current cached data"""
        return {
            'stocks': self.cache['stocks'],
            'news': [asdict(item) for item in self.cache['news']],
            'last_update': self.cache['last_update'].isoformat() if self.cache['last_update'] else None
        }

# Global server instance
server = Server()

async def main():
    """Main entry point"""
    await server.initialize()
    
    # Keep running and update periodically
    while True:
        try:
            await asyncio.sleep(300)  # Update every 5 minutes
            await server.update_data()
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
