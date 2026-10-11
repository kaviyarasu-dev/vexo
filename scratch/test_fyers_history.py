import urllib.request
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.auth_service import AuthService

auth = AuthService()
token = auth.get_valid_token()
headers = {
    "Authorization": f"{auth.settings.FYERS_APP_ID}:{token}",
    "version": "3",
    "User-Agent": "python-requests/2.31.0"
}

test_ranges = [
    ("2026-08-01", "2026-09-01", "1"),
    ("2025-08-01", "2025-09-01", "1"),
    ("2024-08-01", "2024-09-01", "1"),
    ("2023-08-01", "2023-09-01", "1"),
    ("2022-08-01", "2022-09-01", "1"),
    ("2021-08-01", "2021-09-01", "1"),
]

print("=== Testing 1-Minute Historical Availability ===")
for f, t, res in test_ranges:
    url = f"https://api-t1.fyers.in/data/history?symbol=NSE:RELIANCE-EQ&resolution={res}&date_format=1&range_from={f}&range_to={t}&cont_flag=1"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            cnt = len(data.get("candles", []))
            print(f"1m: {f} to {t} -> status: {data.get('s')}, count: {cnt}")
    except Exception as e:
        print(f"1m: {f} to {t} -> Error: {e}")

print("\n=== Testing 5-Minute Historical Availability ===")
for f, t, _ in test_ranges:
    url = f"https://api-t1.fyers.in/data/history?symbol=NSE:RELIANCE-EQ&resolution=5&date_format=1&range_from={f}&range_to={t}&cont_flag=1"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            cnt = len(data.get("candles", []))
            print(f"5m: {f} to {t} -> status: {data.get('s')}, count: {cnt}")
    except Exception as e:
        print(f"5m: {f} to {t} -> Error: {e}")
