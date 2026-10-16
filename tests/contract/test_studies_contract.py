from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_get_studies_catalog_endpoint():
    response = client.get("/api/v1/studies/catalog")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert len(data["data"]) >= 25


def test_get_studies_catalog_profiles_filter():
    response = client.get("/api/v1/studies/catalog?sub_category=profiles")
    assert response.status_code == 200
    data = response.json()
    items = data["data"]
    ids = [item["id"] for item in items]
    assert "visible_range_vp" in ids
    assert "session_vp" in ids
    assert "tpo" in ids


def test_get_studies_catalog_search_endpoint():
    response = client.get("/api/v1/studies/catalog?query=rsi")
    assert response.status_code == 200
    data = response.json()
    items = data["data"]
    assert any("rsi" in item["id"] for item in items)


def test_get_study_details_endpoint():
    response = client.get("/api/v1/studies/visible_range_vp")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == "visible_range_vp"
    assert data["data"]["overlay"] is True
