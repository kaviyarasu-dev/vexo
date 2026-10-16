"""
Integration tests for Multi-Broker Tradebook Import REST API.
Tests POST /api/v1/journal/import across FYERS, Zerodha Console, and Groww formats.
Validates auto-detection, parsing, FIFO reconciliation, and error handling.
"""

import os
import pytest
from fastapi.testclient import TestClient
from main import app
from db.connection import get_db, close_db
from db.migrations import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Sets up an isolated DuckDB instance for integration test execution."""
    db_path = str(tmp_path / "test_multi_broker_import_api.db")
    db = get_db(db_path, reset=True)
    init_db(db_path, manager=db)
    yield db
    close_db()


def load_fixture_bytes(filename: str) -> bytes:
    path = os.path.join(os.path.dirname(__file__), "..", "fixtures", filename)
    with open(path, "rb") as f:
        return f.read()


def test_api_import_fyers_tradebook():
    """Verifies importing FYERS tradebook via POST /api/v1/journal/import."""
    file_bytes = load_fixture_bytes("sample_fyers_tradebook.csv")
    files = {"file": ("fyers_tradebook.csv", file_bytes, "text/csv")}

    response = client.post("/api/v1/journal/import", files=files)
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "success"
    assert payload["imported_trades"] == 2
    assert payload["broker_detected"] == "FYERS"


def test_api_import_zerodha_tradebook():
    """Verifies auto-detection and importing Zerodha Console tradebook via POST /api/v1/journal/import."""
    file_bytes = load_fixture_bytes("sample_zerodha_tradebook.csv")
    files = {"file": ("zerodha_tradebook.csv", file_bytes, "text/csv")}

    response = client.post("/api/v1/journal/import", files=files)
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "success"
    assert payload["imported_trades"] == 2
    assert payload["broker_detected"] == "ZERODHA"


def test_api_import_groww_tradebook():
    """Verifies auto-detection and importing Groww trade report via POST /api/v1/journal/import."""
    file_bytes = load_fixture_bytes("sample_groww_tradebook.csv")
    files = {"file": ("groww_tradebook.csv", file_bytes, "text/csv")}

    response = client.post("/api/v1/journal/import", files=files)
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "success"
    assert payload["imported_trades"] == 2
    assert payload["broker_detected"] == "GROWW"


def test_api_import_with_explicit_broker_param():
    """Verifies importing when client provides explicit broker parameter in form data."""
    file_bytes = load_fixture_bytes("sample_zerodha_tradebook.csv")
    files = {"file": ("zerodha.csv", file_bytes, "text/csv")}
    data = {"broker": "ZERODHA"}

    response = client.post("/api/v1/journal/import", files=files, data=data)
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "success"
    assert payload["imported_trades"] == 2
    assert payload["broker_detected"] == "ZERODHA"


def test_api_import_invalid_csv_returns_400():
    """Verifies that unidentifiable or corrupt CSVs return HTTP 400 with descriptive error."""
    invalid_content = b"random_col1,random_col2,random_col3\n1,2,3"
    files = {"file": ("bad_format.csv", invalid_content, "text/csv")}

    response = client.post("/api/v1/journal/import", files=files)
    assert response.status_code == 400
    error_data = response.json()
    msg = error_data.get("error", {}).get("message", "") or str(error_data.get("detail", ""))
    assert "Unable to identify broker tradebook format" in msg

