import httpx

client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=30.0)

# Test various as_of_date values
test_dates = [
    "2026-10-15",
    "2024-01-01",
    "2023-12-29",
    "2023-12-28",
    "2023-10-01",
    "2022-12-30"
]

for d in test_dates:
    payload = {
        "universe": "ALL",
        "template": None,
        "as_of_date": d,
        "technical_rules": [],
        "min_turnover_cr": 0.0
    }
    r = client.post("/api/v1/screener/run", json=payload)
    if r.status_code == 200:
        cnt = len(r.json().get("data", []))
        print(f"Date {d}: {cnt} stocks returned")
        if cnt > 0:
            sample = [x['symbol'] for x in r.json().get("data", [])[:10]]
            print(f"   Sample ({cnt} total): {sample}")
    else:
        print(f"Date {d}: HTTP {r.status_code}")
