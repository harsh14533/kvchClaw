# plugins/financial_terminal.py
# Real Financial Intelligence Terminal
# Live markets, crypto, news, geopolitical events
# Bloomberg-style experience for personal use

import os
import requests
import time
import threading
from datetime import datetime
from plugins.base import Plugin

try:
    import yfinance as yf
except:
    yf = None

# Cache for real-time data
market_cache = {
    "last_update": 0,
    "indices": {},
    "crypto": {},
    "news": [],
    "alerts": []
}

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")

# Major indices to track
INDICES = {
    "^GSPC": "S&P 500",
    "^IXIC": "NASDAQ",
    "^DJI": "DOW",
    "GC=F": "GOLD",
    "CL=F": "OIL"
}

# Top crypto to track
CRYPTO_IDS = ["bitcoin", "ethereum", "binancecoin", "solana", "cardano"]

def get_market_data():
    """Fetch real-time market data"""
    try:
        if not yf:
            return {}
        
        data = {}
        for symbol, name in INDICES.items():
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            current = info.get("last_price", 0)
            prev_close = info.get("previous_close", current)
            change = ((current - prev_close) / prev_close * 100) if prev_close else 0
            
            data[name] = {
                "price": current,
                "change": change,
                "symbol": symbol
            }
        
        return data
    except Exception as e:
        print("Market data error:", e)
        return {}

def get_crypto_data():
    """Fetch real-time crypto prices from CoinGecko"""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": ",".join(CRYPTO_IDS),
            "vs_currencies": "usd",
            "include_24hr_change": "true"
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        crypto = {}
        for coin_id, coin_data in data.items():
            crypto[coin_id] = {
                "price": coin_data.get("usd", 0),
                "change": coin_data.get("usd_24h_change", 0)
            }
        
        return crypto
    except Exception as e:
        print("Crypto data error:", e)
        return {}

def get_financial_news():
    """Fetch real-time financial news"""
    try:
        news = []
        
        # Try NewsAPI if key available
        if NEWSAPI_KEY:
            url = "https://newsapi.org/v2/top-headlines"
            params = {
                "apiKey": NEWSAPI_KEY,
                "category": "business",
                "language": "en",
                "pageSize": 10
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                articles = response.json().get("articles", [])
                for article in articles[:5]:
                    news.append({
                        "title": article.get("title", ""),
                        "source": article.get("source", {}).get("name", ""),
                        "time": article.get("publishedAt", "")[:10]
                    })
        
        # Fallback to RSS feeds
        if not news:
            import feedparser
            feeds = [
                "https://feeds.bloomberg.com/markets/news.rss",
                "https://www.cnbc.com/id/100003114/device/rss/rss.html"
            ]
            for feed_url in feeds:
                try:
                    feed = feedparser.parse(feed_url)
                    for entry in feed.entries[:3]:
                        news.append({
                            "title": entry.title,
                            "source": feed.feed.title,
                            "time": entry.get("published", "")[:10]
                        })
                    if news:
                        break
                except:
                    continue
        
        return news[:10]
    except Exception as e:
        print("News error:", e)
        return []

def detect_geopolitical_alerts(news):
    """Detect geopolitical events from news"""
    alerts = []
    keywords = {
        "war": "Military Conflict",
        "sanctions": "Economic Sanctions",
        "election": "Political Event",
        "fed": "Monetary Policy",
        "china": "US-China Relations",
        "russia": "Russia-related",
        "oil": "Energy Sector",
        "trade": "Trade Policy"
    }
    
    for item in news:
        title_lower = item["title"].lower()
        for keyword, alert_type in keywords.items():
            if keyword in title_lower:
                alerts.append({
                    "type": alert_type,
                    "headline": item["title"][:80],
                    "source": item["source"]
                })
                break
    
    return alerts[:5]

def update_market_cache():
    """Background thread to update market data"""
    while True:
        try:
            current_time = time.time()
            
            # Update every 30 seconds
            if current_time - market_cache["last_update"] > 30:
                market_cache["indices"] = get_market_data()
                market_cache["crypto"] = get_crypto_data()
                market_cache["news"] = get_financial_news()
                market_cache["alerts"] = detect_geopolitical_alerts(market_cache["news"])
                market_cache["last_update"] = current_time
            
            time.sleep(30)
        except:
            time.sleep(60)

# Start background updater
updater_thread = threading.Thread(target=update_market_cache, daemon=True)
updater_thread.start()

def format_terminal_display():
    """Generate Bloomberg-style terminal display"""
    now = datetime.now().strftime("%H:%M:%S EST    %b %d, %Y")
    
    output = "━" * 60 + "\n"
    output += "FINANCIAL TERMINAL          " + now + "\n"
    output += "━" * 60 + "\n\n"
    
    # Markets section
    output += "MARKETS\n"
    indices = market_cache.get("indices", {})
    if indices:
        for name, data in indices.items():
            price = data["price"]
            change = data["change"]
            arrow = "▲" if change >= 0 else "▼"
            sign = "+" if change >= 0 else ""
            output += name.ljust(12) + str(round(price, 2)).rjust(10) + "  "
            output += arrow + " " + sign + str(round(change, 2)) + "%\n"
    else:
        output += "Loading market data...\n"
    
    # Crypto section
    output += "\nCRYPTO\n"
    crypto = market_cache.get("crypto", {})
    if crypto:
        for coin_id, data in crypto.items():
            name = coin_id.upper()[:3]
            price = data["price"]
            change = data["change"]
            arrow = "▲" if change >= 0 else "▼"
            sign = "+" if change >= 0 else ""
            output += name.ljust(12) + "$" + str(round(price, 2)).rjust(10) + "  "
            output += arrow + " " + sign + str(round(change, 2)) + "%\n"
    else:
        output += "Loading crypto data...\n"
    
    # News section
    output += "\n" + "━" * 60 + "\n"
    output += "LIVE FINANCIAL NEWS\n"
    output += "━" * 60 + "\n"
    news = market_cache.get("news", [])
    if news:
        for item in news[:5]:
            output += "• " + item["title"][:75] + "\n"
            output += "  [" + item["source"] + "]\n"
    else:
        output += "Loading news feed...\n"
    
    # Geopolitical alerts
    alerts = market_cache.get("alerts", [])
    if alerts:
        output += "\n" + "━" * 60 + "\n"
        output += "GEOPOLITICAL ALERTS\n"
        output += "━" * 60 + "\n"
        for alert in alerts:
            output += "⚠ [" + alert["type"] + "] " + alert["headline"] + "\n"
    
    output += "\n" + "━" * 60 + "\n"
    output += "Last updated: " + datetime.fromtimestamp(market_cache["last_update"]).strftime("%H:%M:%S")
    output += "\nNext update in: " + str(30 - int(time.time() - market_cache["last_update"])) + "s"
    
    return output

def get_stock_quote(symbol):
    """Get detailed quote for a specific stock"""
    try:
        if not yf:
            return "yfinance not available"
        
        ticker = yf.Ticker(symbol.upper())
        info = ticker.fast_info
        
        current = info.get("last_price", 0)
        prev_close = info.get("previous_close", current)
        change = current - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0
        
        output = symbol.upper() + " Quote\n"
        output += "Price: $" + str(round(current, 2)) + "\n"
        output += "Change: " + ("+" if change >= 0 else "") + str(round(change, 2))
        output += " (" + ("+" if change_pct >= 0 else "") + str(round(change_pct, 2)) + "%)\n"
        output += "Previous Close: $" + str(round(prev_close, 2))
        
        return output
    except Exception as e:
        return "Error fetching " + symbol + ": " + str(e)

class FinancialTerminalPlugin(Plugin):
    name = "FINANCIAL_TERMINAL"
    description = (
        "Real-time financial intelligence terminal. "
        "Live markets, crypto prices, financial news, geopolitical alerts. "
        "Bloomberg-style experience with real data."
    )
    triggers = [
        "terminal", "markets", "market summary", "financial terminal",
        "stock market", "crypto prices", "financial news",
        "market update", "live markets", "show terminal",
        "stock", "quote", "ticker", "btc", "eth", "crypto"
    ]
    
    def execute(self, value: str) -> tuple:
        try:
            val = value.lower().strip()
            
            # Specific stock quote
            words = val.split()
            for word in words:
                if len(word) <= 5 and word.isupper():
                    return get_stock_quote(word), None
            
            # Check for crypto symbols
            if "btc" in val or "bitcoin" in val:
                crypto = market_cache.get("crypto", {})
                if "bitcoin" in crypto:
                    btc = crypto["bitcoin"]
                    return "Bitcoin: $" + str(round(btc["price"], 2)) + " (" + ("+" if btc["change"] >= 0 else "") + str(round(btc["change"], 2)) + "%)", None
            
            # Default - show full terminal
            return format_terminal_display(), None
        
        except Exception as e:
            return "Terminal error: " + str(e), None
