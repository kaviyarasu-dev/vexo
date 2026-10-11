import pytest
from db.connection import DuckDBConnectionManager
from db.migrations import init_db
from scripts.run_backup_drill import run_drill

@pytest.fixture
def isolated_db(tmp_path):
    db_path = tmp_path / "test.duckdb"
    manager = DuckDBConnectionManager(str(db_path))
    init_db(manager=manager)
    manager.execute_write("INSERT INTO symbols (symbol, name) VALUES ('TEST', 'Test Symbol')")
    yield manager
    manager.close()

def test_backup_restore_drill_integration(isolated_db, tmp_path):
    snapshot_dir = tmp_path / "snapshot"
    scratch_db = tmp_path / "scratch.duckdb"
    
    run_drill(snapshot_dir=str(snapshot_dir), scratch_db_path=str(scratch_db), db=isolated_db)
    
    # Assert scratch is deleted
    assert not scratch_db.exists()
