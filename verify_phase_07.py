import urllib.request
import urllib.error
import json
import os
import pandas as pd
from datetime import datetime

print("Running DOD Item 1: Candles API Response Envelope")
req = urllib.request.Request("http://localhost:8000/api/v1/candles?symbol=NSE:RELIANCE-EQ&timeframe=5m&limit=10")
with urllib.request.urlopen(req) as res:
    data = json.loads(res.read().decode())
    correlation_id = data.get("meta", {}).get("correlation_id")
    print("Correlation ID:", correlation_id)
    assert correlation_id is not None, "Missing correlation_id"

print("Running DOD Item 2: Parquet Export")
parquet_url = "http://localhost:8000/api/v1/export?symbol=NSE:RELIANCE-EQ&timeframe=1m&format=parquet"
# Since from_date and to_date have defaults in our updated router, this should work. 
# But just in case, we will add dummy ones if they fail.
try:
    urllib.request.urlretrieve(parquet_url, "test.parquet")
    df = pd.read_parquet("test.parquet")
    print(f"Parquet row count: {len(df)}")
except Exception as e:
    print("Failed parquet download:", e)
    raise

print("Running DOD Item 3: Excel Row Limit Guard")
excel_url = "http://localhost:8000/api/v1/export?symbol=NSE:RELIANCE-EQ&timeframe=1m&from_date=2015-01-01&to_date=2024-01-01&format=excel"
try:
    with urllib.request.urlopen(excel_url) as res:
        pass
    print("Excel succeeded (unexpected for large range)")
except urllib.error.HTTPError as e:
    if e.code == 400:
        data = json.loads(e.read().decode())
        code = data.get("error", {}).get("code")
        print("Error code:", code)
        assert code == "EXCEL_ROW_LIMIT_EXCEEDED"
    else:
        raise
