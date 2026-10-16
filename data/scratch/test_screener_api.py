import httpx
import json

BASE_URL = "http://127.0.0.1:8000"

client = httpx.Client(base_url=BASE_URL, timeout=30.0)

# 1. Status
status = client.get("/api/v1/screener/status").json()
print("Screener Status:", json.dumps(status, indent=2))

# 2. Templates
templates_res = client.get("/api/v1/screener/templates").json()
print("Templates Count:", len(templates_res.get("data", [])))
for t in templates_res.get("data", []):
    print(f"  - {t['id']}: {t['name']} (universe={t.get('universe')}) rules={t.get('conditions')}")

# 3. Test running each template
for t in templates_res.get("data", []):
    payload = {
        "universe": t.get("universe") or "ALL",
        "template": t["id"],
        "as_of_date": None,
        "technical_rules": [],
        "min_turnover_cr": 0.0
    }
    r = client.post("/api/v1/screener/run", json=payload)
    if r.status_code == 200:
        data = r.json()
        matches = data.get("data", [])
        print(f"Template {t['id']} -> {len(matches)} matches")
        if matches:
            print(f"   Sample symbols: {[m['symbol'] for m in matches[:5]]}")
    else:
        print(f"Template {t['id']} -> HTTP {r.status_code}: {r.text}")

# 4. Test running with universe='ALL' and NO rules (i.e. all stocks)
all_stocks_payload = {
    "universe": "ALL",
    "template": None,
    "as_of_date": None,
    "technical_rules": [],
    "min_turnover_cr": 0.0
}
r_all = client.post("/api/v1/screener/run", json=all_stocks_payload)
if r_all.status_code == 200:
    data_all = r_all.json()
    matches_all = data_all.get("data", [])
    print(f"\nALL STOCKS (no template, universe='ALL'): {len(matches_all)} total stocks returned!")
    if matches_all:
        print(f"   Sample: {[m['symbol'] for m in matches_all[:5]]}")
else:
    print(f"ALL STOCKS run failed: {r_all.status_code} {r_all.text}")

# 5. Test universe='NIFTY50'
r_n50 = client.post("/api/v1/screener/run", json={"universe": "NIFTY50", "min_turnover_cr": 0.0})
if r_n50.status_code == 200:
    print(f"NIFTY50 count: {len(r_n50.json().get('data', []))}")

# 6. Test universe='NIFTY500'
r_n500 = client.post("/api/v1/screener/run", json={"universe": "NIFTY500", "min_turnover_cr": 0.0})
if r_n500.status_code == 200:
    print(f"NIFTY500 count: {len(r_n500.json().get('data', []))}")
