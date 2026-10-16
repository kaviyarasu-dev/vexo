import pytest
import urllib.request
import json

BASE_URL = "http://127.0.0.1:8000/api/v1/screener"

def is_server_online():
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/api/v1/health", timeout=1) as resp:
            return resp.status == 200
    except Exception:
        return False

@pytest.mark.skipif(not is_server_online(), reason="Server not running on port 8000")
def test_custom_template_api_lifecycle():
    # 1. Create custom template
    payload = {
        "name": "Pytest Momentum Scan",
        "description": "RSI <= 45 and 1-Day Change >= 0.5%",
        "universe": "ALL",
        "conditions": [
            {"field": "rsi_14", "operator": "<=", "value": 45.0},
            {"field": "change_pct_1d", "operator": ">=", "value": 0.5}
        ]
    }
    req = urllib.request.Request(
        f"{BASE_URL}/templates",
        data=json.dumps(payload).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode())
        assert res["success"] is True
        template_id = res["data"]["id"]
        assert res["data"]["is_custom"] is True

    # 2. Verify in templates list
    with urllib.request.urlopen(f"{BASE_URL}/templates") as resp:
        res = json.loads(resp.read().decode())
        assert res["success"] is True
        found = [t for t in res["data"] if t["id"] == template_id]
        assert len(found) == 1

    # 3. Run scan with custom template
    run_payload = {
        "universe": "ALL",
        "template": template_id,
        "as_of_date": None,
        "technical_rules": [],
        "min_turnover_cr": 0.0
    }
    req = urllib.request.Request(
        f"{BASE_URL}/run",
        data=json.dumps(run_payload).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        scan_res = json.loads(resp.read().decode())
        assert scan_res["success"] is True
        assert isinstance(scan_res["data"], list)

    # 4. Delete custom template
    req = urllib.request.Request(f"{BASE_URL}/templates/{template_id}", method="DELETE")
    with urllib.request.urlopen(req) as resp:
        del_res = json.loads(resp.read().decode())
        assert del_res["success"] is True

    # 5. Verify template was removed
    with urllib.request.urlopen(f"{BASE_URL}/templates") as resp:
        res = json.loads(resp.read().decode())
        found = [t for t in res["data"] if t["id"] == template_id]
        assert len(found) == 0
