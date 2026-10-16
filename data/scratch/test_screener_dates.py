import httpx

client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=30.0)

# Let's inspect the screener query behavior
# If we test as_of_date = '2026-10-09' vs '2026-10-15':
for d in ['2026-10-15', '2026-10-09', '2026-10-08', '2026-10-07', '2024-01-01']:
    r = client.post("/api/v1/screener/run", json={"universe": "ALL", "as_of_date": d, "min_turnover_cr": 0.0})
    if r.status_code == 200:
        matches = r.json().get("data", [])
        print(f"Date {d}: {len(matches)} stocks returned")
        if matches:
            print(f"   Sample: {[m['symbol'] for m in matches[:5]]}")
    else:
        print(f"Date {d}: HTTP {r.status_code}")
