import pytest
from fastapi.testclient import TestClient

from main import app
from db.connection import get_db, close_db
from db.migrations import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    db_path = str(tmp_path / "test_chart_drawings_api.db")
    db = get_db(db_path, reset=True)
    init_db(db_path, manager=db)
    yield db
    close_db()


def test_create_and_get_drawing_endpoints():
    # 1. Create drawing via POST
    payload = {
        "tool_type": "FIBONACCI",
        "points": [
            {"time": "2026-01-01", "price": 2000.0},
            {"time": "2026-01-15", "price": 2500.0}
        ],
        "style": {
            "color": "#7C3AED",
            "lineWidth": 2,
            "filled": True
        }
    }
    resp = client.post("/api/v1/chart/drawings/NSE:RELIANCE-EQ", json=payload)
    assert resp.status_code == 201
    res_data = resp.json()
    assert res_data["success"] is True
    data = res_data["data"]
    assert data["symbol"] == "NSE:RELIANCE-EQ"
    assert data["tool_type"] == "FIBONACCI"
    assert len(data["points"]) == 2
    drawing_id = data["drawing_id"]

    # 2. Get drawings for symbol via GET
    get_resp = client.get("/api/v1/chart/drawings/NSE:RELIANCE-EQ")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["success"] is True
    assert get_data["count"] == 1
    assert get_data["data"][0]["drawing_id"] == drawing_id


def test_update_drawing_endpoint():
    # Create initial drawing
    payload = {
        "tool_type": "TRENDLINE",
        "points": [
            {"time": "2026-01-01", "price": 100.0},
            {"time": "2026-01-02", "price": 110.0}
        ]
    }
    post_res = client.post("/api/v1/chart/drawings/NSE:TCS-EQ", json=payload)
    drawing_id = post_res.json()["data"]["drawing_id"]

    # Update via PUT
    update_payload = {
        "points": [
            {"time": "2026-01-01", "price": 100.0},
            {"time": "2026-01-02", "price": 115.0}
        ],
        "style": {"color": "#F59E0B", "lineWidth": 3}
    }
    put_res = client.put(f"/api/v1/chart/drawings/{drawing_id}", json=update_payload)
    assert put_res.status_code == 200
    updated_data = put_res.json()["data"]
    assert updated_data["points"][1]["price"] == 115.0
    assert updated_data["style"]["color"] == "#F59E0B"


def test_delete_and_clear_drawing_endpoints():
    # Create two drawings
    client.post("/api/v1/chart/drawings/NSE:INFY-EQ", json={
        "tool_type": "HORIZONTAL_RAY",
        "points": [{"time": "2026-01-01", "price": 1800.0}]
    })
    r2 = client.post("/api/v1/chart/drawings/NSE:INFY-EQ", json={
        "tool_type": "TRENDLINE",
        "points": [
            {"time": "2026-01-01", "price": 1800.0},
            {"time": "2026-01-05", "price": 1900.0}
        ]
    })
    d2_id = r2.json()["data"]["drawing_id"]

    # Delete single drawing via DELETE
    del_res = client.delete(f"/api/v1/chart/drawings/{d2_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 1 remaining
    get_res = client.get("/api/v1/chart/drawings/NSE:INFY-EQ")
    assert get_res.json()["count"] == 1

    # Clear all via DELETE /all
    clear_res = client.delete("/api/v1/chart/drawings/NSE:INFY-EQ/all")
    assert clear_res.status_code == 200
    assert clear_res.json()["count"] == 1

    # 0 remaining
    get_after = client.get("/api/v1/chart/drawings/NSE:INFY-EQ")
    assert get_after.json()["count"] == 0


def test_error_handling_endpoints():
    # 404 on update non-existent drawing
    put_res = client.put("/api/v1/chart/drawings/non-existent-id", json={"points": []})
    assert put_res.status_code == 404

    # 404 on delete non-existent drawing
    del_res = client.delete("/api/v1/chart/drawings/non-existent-id")
    assert del_res.status_code == 404

    # 422 on invalid creation payload (missing tool_type or empty points)
    bad_post = client.post("/api/v1/chart/drawings/NSE:RELIANCE-EQ", json={
        "tool_type": "TRENDLINE",
        "points": []  # Min length 1
    })
    assert bad_post.status_code == 422
