import httpx
import json

client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=30.0)

# Check portfolio universes to see what symbols exist
univ_res = client.get("/api/v1/backtest/portfolio/universes").json()
print("Universes from portfolio API:")
for u in univ_res.get("data", []):
    print(f"  - {u['name']}: {u['symbol_count']} symbols (sample: {u.get('sample_symbols', [])[:5]})")

# Check status of symbols
# Let's see what happens if we query candles for some symbols
test_syms = ["NSE:RELIANCE-EQ", "NSE:TCS-EQ", "NSE:INFY-EQ", "NSE:HDFCBANK-EQ", "NSE:SBIN-EQ"]
for s in test_syms:
    c = client.get(f"/api/v1/candles?symbol={s}&timeframe=1D&limit=5&refresh_live=false").json()
    if c.get("success"):
        candles = c.get("data", {}).get("candles", [])
        last_dt = candles[-1] if candles else "None"
        print(f"Symbol {s}: {len(candles)} candles, latest candle: {last_dt}")
    else:
        print(f"Symbol {s}: FAILED {c}")
