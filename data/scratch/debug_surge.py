import httpx
import json

client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=30.0)

payload = {
    "template": "volume_surge",
    "universe": "ALL",
    "technical_rules": [],
    "min_turnover_cr": 0.0
}
res = client.post("/api/v1/screener/run", json=payload)
data = res.json()
print("Status code:", res.status_code)
print("Meta:", data.get("meta"))
stocks = data.get("data", [])
print(f"Total returned: {len(stocks)}")
for s in stocks:
    print(f"  {s['symbol']}: zscore={s.get('volume_zscore_20')}, turnover_cr={s.get('turnover_cr')}, rules={s.get('matched_rules')}")
