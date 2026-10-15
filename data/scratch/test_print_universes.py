import httpx
import json

client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=30.0)

univ_res = client.get("/api/v1/backtest/portfolio/universes").json()
print("Universes from portfolio API:", json.dumps(univ_res, indent=2))
