def scrape_tradingview():
    global stocks_cache

    url = "https://scanner.tradingview.com/morocco/scan"

    payload = {
        "filter": [],
        "options": {"lang": "en"},
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": [
            "name",
            "sector",
            "close",
            "change",
            "market_cap_basic",
            "price_earnings_ttm",
            "Recommend.All"
        ]
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json"
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)

        if r.status_code != 200:
            print("TradingView API error:", r.status_code)
            return stocks_cache

        data = r.json()
        stocks = []

        for item in data.get("data", []):
            d = item.get("d", [])

            pe_value = d[5]
            recommendation = d[6]

            stocks.append({
                "symbol": d[0],
                "sector": d[1] if d[1] else "—",
                "capital": f"{round(d[4] / 1_000_000_000, 2)}B MAD" if d[4] else "—",
                "price": float(d[2]) if d[2] else 0,
                "change": float(d[3]) if d[3] else 0,
                "pe": float(pe_value) if pe_value else None,
                "rating": convert_rating(recommendation),
                "has_live_data": True
            })

        stocks_cache = stocks
        return stocks_cache

    except Exception as e:
        print("TradingView fetch error:", e)
        return stocks_cache
