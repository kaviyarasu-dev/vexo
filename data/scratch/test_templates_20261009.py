import httpx

client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=30.0)

# Check templates on 2026-10-09
templates = ["volume_surge", "52_week_high", "rsi_oversold", "rsi_momentum", "sma_support"]
for t in templates:
    r = client.post("/api/v1/screener/run", json={"universe": "ALL", "template": t, "as_of_date": "2026-10-09", "min_turnover_cr": 0.0})
    if r.status_code == 200:
        matches = r.json().get("data", [])
        print(f"Template {t} on 2026-10-09: {len(matches)} matches")
        if matches:
            print(f"   Sample: {[m['symbol'] for m in matches[:5]]}")
    else:
        print(f"Template {t}: HTTP {r.status_code}")
