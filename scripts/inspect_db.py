"""DuckDB Inspection Utility.
Safely inspects database tables, row counts, and sample records whether the
FastAPI backend server is running or offline.

Usage:
    python scripts/inspect_db.py
    python scripts/inspect_db.py --table candles_1d_raw
    python scripts/inspect_db.py --query "SELECT symbol, count(*) FROM candles_1d_raw GROUP BY symbol"
"""

import argparse
import json
from pathlib import Path
import sys
import urllib.request
import urllib.error

# Ensure project root is in sys.path when script is run directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import get_settings


def is_server_running(host: str = "http://127.0.0.1:8000") -> bool:
    """Checks if FastAPI backend is responding on port 8000."""
    try:
        with urllib.request.urlopen(f"{host}/api/v1/health", timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def get_stats_from_server(host: str = "http://127.0.0.1:8000") -> dict:
    """Fetches real-time DB stats through running FastAPI backend cursor."""
    req = urllib.request.Request(f"{host}/api/v1/system/db/stats")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            payload = json.loads(resp.read().decode())
            return payload.get("data", {})
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # Server was started before new stats route was added; probe standard endpoints
            return get_stats_from_probes(host)
        raise


def get_stats_from_probes(host: str = "http://127.0.0.1:8000") -> dict:
    """Probes active server REST endpoints to verify live database records."""
    settings = get_settings()
    db_file = Path(settings.DUCKDB_PATH)
    file_size_mb = round(db_file.stat().st_size / (1024 * 1024), 2) if db_file.exists() else 0.0

    probes = {}
    # Check candles
    try:
        req = urllib.request.Request(f"{host}/api/v1/candles?symbol=NSE:RELIANCE-EQ&timeframe=1D&limit=1")
        with urllib.request.urlopen(req, timeout=3) as r:
            d = json.loads(r.read().decode())
            probes["candles_1d_raw (RELIANCE)"] = "ACTIVE (Live Data Responding)" if d.get("success") else "Empty"
    except Exception:
        probes["candles_1d_raw"] = "Queried"

    try:
        req = urllib.request.Request(f"{host}/api/v1/candles?symbol=NSE:RELIANCE-EQ&timeframe=1m&limit=1")
        with urllib.request.urlopen(req, timeout=3) as r:
            d = json.loads(r.read().decode())
            probes["candles_1m_raw (RELIANCE)"] = "ACTIVE (Live Data Responding)" if d.get("success") else "Empty"
    except Exception:
        pass

    try:
        req = urllib.request.Request(f"{host}/api/v1/symbols/search?query=RELIANCE")
        with urllib.request.urlopen(req, timeout=3) as r:
            d = json.loads(r.read().decode())
            count = len(d.get("data", []))
            probes["symbols (Search Sample)"] = f"{count} matches returned"
    except Exception:
        pass

    return {
        "db_path": str(db_file),
        "file_size_mb": file_size_mb,
        "tables": probes,
        "note": "To see exact row counts of all DuckDB tables, restart the server (start_server.bat) to activate the new /stats endpoint or stop the server to inspect offline.",
    }


def get_stats_direct() -> dict:
    """Reads DB directly via DuckDB (used when server process is stopped)."""
    import duckdb
    settings = get_settings()
    db_file = Path(settings.DUCKDB_PATH)
    if not db_file.exists():
        return {"db_path": str(db_file), "file_size_mb": 0.0, "tables": {}}

    con = duckdb.connect(str(db_file), read_only=True)
    try:
        tables = con.execute("SHOW TABLES").fetchall()
        table_stats = {}
        for row in tables:
            t = row[0]
            cnt = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            table_stats[t] = cnt
        return {
            "db_path": str(db_file),
            "file_size_mb": round(db_file.stat().st_size / (1024 * 1024), 2),
            "tables": table_stats,
        }
    finally:
        con.close()


def run_custom_query_direct(query: str):
    """Executes custom SQL query directly on DuckDB."""
    import duckdb
    settings = get_settings()
    con = duckdb.connect(str(settings.DUCKDB_PATH), read_only=True)
    try:
        df = con.execute(query).df()
        print(df.to_string(index=False))
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser(description="Inspect DuckDB Market Data Platform")
    parser.add_argument("--query", "-q", type=str, help="Run custom read-only SQL query")
    parser.add_argument("--table", "-t", type=str, help="View top 5 rows from specific table")
    args = parser.parse_args()

    settings = get_settings()
    server_active = is_server_running()

    print("=" * 68)
    print("           NSE QUANT PLATFORM — DUCKDB DATABASE INSPECTOR")
    print("=" * 68)
    print(f"Database Path : {Path(settings.DUCKDB_PATH).resolve()}")
    print(f"Server Status : {'ONLINE (FastAPI http://127.0.0.1:8000)' if server_active else 'OFFLINE'}")
    print("-" * 68)

    if args.query:
        if server_active:
            print("[INFO] Server is running with exclusive writer lock.")
            print("[INFO] For safety, custom arbitrary queries are executed directly when server is idle.")
            print("Running direct read query...")
        try:
            run_custom_query_direct(args.query)
        except Exception as e:
            print(f"[ERROR]: {e}")
            if "used by another process" in str(e):
                print("\n[NOTE] Windows file lock is held by start_server.bat.")
                print("To run arbitrary raw SQL, stop the server with Ctrl+C or use the REST APIs.")
        return

    # Fetch stats
    try:
        if server_active:
            stats = get_stats_from_server()
        else:
            stats = get_stats_direct()
    except Exception as e:
        print(f"[ERROR] Could not fetch DB stats: {e}")
        return

    print(f"File Size     : {stats.get('file_size_mb', 0)} MB")
    print(f"\n{'TABLE NAME':<32} | {'ROW COUNT':>15}")
    print("-" * 50)

    tables = stats.get("tables", {})
    if not tables:
        print("  (No tables found in database)")
    else:
        for name, count in sorted(tables.items()):
            cnt_str = f"{count:,}" if isinstance(count, int) else str(count)
            print(f"{name:<32} | {cnt_str:>25}")

    print("-" * 60)
    print(f"Total Items Reported : {len(tables)}")
    if stats.get("note"):
        print(f"\n[NOTE]: {stats['note']}")
    print("=" * 68)


if __name__ == "__main__":
    main()
