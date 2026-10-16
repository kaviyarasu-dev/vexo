import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_frontend_api_bindings():
    """ApiClient correctly parses 00A ApiResponse envelopes."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "success" in data


def test_auth_status_endpoint():
    """Frontend auth badge queries /api/v1/auth/status."""
    response = client.get("/api/v1/auth/status")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "is_authenticated" in data["data"]
    assert "token_expires_at" in data["data"]


def test_glossary_and_translation_static_bindings():
    """Frontend tooltips and mode toggles successfully load glossary and translations."""
    assert client.get("/config/glossary.json").status_code == 200
    assert client.get("/data/glossary.json").status_code == 200
    assert client.get("/static/config/glossary.json").status_code == 200
    assert client.get("/static/config/ux_translations.json").status_code == 200
    assert client.get("/favicon.ico").status_code == 204
