import pytest
from db.connection import DuckDBConnectionManager
from db.migrations import init_db
from services.integrity_auditor import DataIntegrityAuditor

@pytest.fixture
def test_db():
    manager = DuckDBConnectionManager(":memory:")
    init_db(manager=manager)
    yield manager
    manager.close()

def test_audit_detects_anomalies(test_db):
    test_db.execute_write("INSERT INTO candles_1d_raw (symbol, date, open, high, low, close, volume) VALUES ('RELIANCE', '2023-01-01', 100, 110, 90, 100, 1000)")
    test_db.execute_write("INSERT INTO candles_1d_raw (symbol, date, open, high, low, close, volume) VALUES ('RELIANCE', '2023-01-02', 100, 110, 50, 60, 1000)")
    
    auditor = DataIntegrityAuditor(test_db)
    report = auditor.run_audit()
    
    assert report["anomalies_detected"] is True
    assert report["anomalies_count"] == 1
    assert report["anomalies"][0]["symbol"] == "RELIANCE"

def test_audit_ignores_corporate_actions(test_db):
    test_db.execute_write("INSERT INTO candles_1d_raw (symbol, date, open, high, low, close, volume) VALUES ('TCS', '2023-01-01', 100, 110, 90, 100, 1000)")
    test_db.execute_write("INSERT INTO candles_1d_raw (symbol, date, open, high, low, close, volume) VALUES ('TCS', '2023-01-02', 50, 60, 40, 50, 1000)")
    
    test_db.execute_write("INSERT INTO corporate_actions (id, symbol, action_type, ex_date, ratio_from, ratio_to) VALUES ('ca1', 'TCS', 'SPLIT', '2023-01-02', 1, 2)")
    
    auditor = DataIntegrityAuditor(test_db)
    report = auditor.run_audit()
    
    assert report["anomalies_detected"] is False
