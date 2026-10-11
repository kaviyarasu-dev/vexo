import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_static_index_html_mount():
    """Frontend shell loads successfully from FastAPI static mount."""
    response = client.get("/static/index.html")
    assert response.status_code == 200
    assert 'id="chart-container"' in response.text

def test_root_serves_spa():
    """Root URL serves HTML dashboard with Lightweight Charts script tags embedded."""
    response = client.get("/")
    assert response.status_code == 200
    assert "LightweightCharts" in response.text
