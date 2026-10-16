import httpx

client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=30.0)

# Check how many stocks match each universe on 2026-10-09:
for u in ["ALL", "NIFTY50", "NIFTY500", "NIFTY_50", "NIFTY_NEXT_50"]:
    r = client.post("/api/v1/screener/run", json={"universe": u, "as_of_date": "2026-10-09", "min_turnover_cr": 0.0})
    if r.status_code == 200:
        matches = r.json().get("data", [])
        print(f"Universe {u} on 2026-10-09: {len(matches)} stocks")
    else:
        print(f"Universe {u}: HTTP {r.status_code}")
