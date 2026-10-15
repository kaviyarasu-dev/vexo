import httpx

client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=30.0)

# Check all symbols and their categories/tiers
r = client.post("/api/v1/screener/run", json={"universe": "ALL", "as_of_date": "2026-10-09", "min_turnover_cr": 0.0})
stocks = r.json().get("data", [])
categories = set(s.get("category") for s in stocks)
print("Categories in screener result:", categories)

# How many have category='NIFTY50'?
nifty50_stocks = [s for s in stocks if s.get("category") == "NIFTY50"]
print("Stocks with category == 'NIFTY50':", len(nifty50_stocks))
sample_cats = [(s['symbol'], s.get('category')) for s in stocks[:10]]
print("Sample symbol categories:", sample_cats)
