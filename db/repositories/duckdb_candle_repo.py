"""DuckDB implementation of ICandleReader and ICandleWriter.
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md and plan/02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md.
"""

from datetime import date, datetime
import logging
from typing import Any, List, Optional, Union
import duckdb
import pandas as pd
import pyarrow as pa

from core.interfaces import Candle, ICandleReader, ICandleWriter
from db.connection import DuckDBConnectionManager, get_db

logger = logging.getLogger(__name__)


class DuckDBCandleRepo(ICandleReader, ICandleWriter):
    """High-performance columnar candle repository for DuckDB.
    
    Implements:
    - ICandleReader: Independent cursors for concurrent non-blocking reads.
    - ICandleWriter: Staging table + anti-join deduplication under single-writer lock.
    """

    def __init__(self, db: Optional[DuckDBConnectionManager] = None) -> None:
        self.db = db or get_db()

    # ---------------------------------------------------------
    # ICandleWriter Implementation (Write Lock Protected)
    # ---------------------------------------------------------

    def batch_insert_1m(self, candles: Union[List[dict], pa.Table, pd.DataFrame]) -> int:
        """Batch insert 1-minute raw candles with staging + anti-join deduplication."""
        if candles is None:
            return 0
        if isinstance(candles, list) and len(candles) == 0:
            return 0
        if isinstance(candles, (pd.DataFrame, pa.Table)) and len(candles) == 0:
            return 0

        # Normalize to Arrow table or DataFrame
        if isinstance(candles, list):
            arrow_table = pa.Table.from_pylist(candles)
        elif isinstance(candles, pd.DataFrame):
            arrow_table = pa.Table.from_pandas(candles)
        else:
            arrow_table = candles

        def _do_insert(conn: duckdb.DuckDBPyConnection) -> int:
            conn.register("_arrow_stage_1m", arrow_table)
            try:
                # Physical ordering by (symbol, timestamp) for DuckDB columnar Zone Maps
                conn.execute("""
                    CREATE TEMP TABLE _staging_1m_batch AS
                    SELECT 
                        CAST(symbol AS VARCHAR) AS symbol,
                        CAST(timestamp AS TIMESTAMP) AS timestamp,
                        CAST(open AS DOUBLE) AS open,
                        CAST(high AS DOUBLE) AS high,
                        CAST(low AS DOUBLE) AS low,
                        CAST(close AS DOUBLE) AS close,
                        CAST(volume AS BIGINT) AS volume
                    FROM _arrow_stage_1m
                    ORDER BY symbol, timestamp;
                """)

                # Stage + Anti-join deduplication
                conn.execute("""
                    CREATE TEMP TABLE _dedup_1m AS
                    SELECT s.* FROM _staging_1m_batch s
                    WHERE NOT EXISTS (
                        SELECT 1 FROM candles_1m_raw c
                        WHERE c.symbol = s.symbol 
                          AND c.timestamp = s.timestamp
                    );
                """)

                res = conn.execute("SELECT count(*) FROM _dedup_1m;").fetchone()
                count = res[0] if res else 0

                if count > 0:
                    conn.execute("""
                        INSERT INTO candles_1m_raw (symbol, timestamp, open, high, low, close, volume)
                        SELECT symbol, timestamp, open, high, low, close, volume FROM _dedup_1m;
                    """)

                conn.execute("DROP TABLE IF EXISTS _dedup_1m;")
                conn.execute("DROP TABLE IF EXISTS _staging_1m_batch;")
                return count
            finally:
                conn.unregister("_arrow_stage_1m")

        return self.db.execute_write_batch(_do_insert)

    def batch_insert_1d(self, candles: Union[List[dict], pa.Table, pd.DataFrame]) -> int:
        """Batch insert daily EOD raw candles with staging + anti-join deduplication."""
        if candles is None:
            return 0
        if isinstance(candles, list) and len(candles) == 0:
            return 0
        if isinstance(candles, (pd.DataFrame, pa.Table)) and len(candles) == 0:
            return 0

        if isinstance(candles, list):
            arrow_table = pa.Table.from_pylist(candles)
        elif isinstance(candles, pd.DataFrame):
            arrow_table = pa.Table.from_pandas(candles)
        else:
            arrow_table = candles

        def _do_insert(conn: duckdb.DuckDBPyConnection) -> int:
            conn.register("_arrow_stage_1d", arrow_table)
            try:
                conn.execute("""
                    CREATE TEMP TABLE _staging_1d_batch AS
                    SELECT 
                        CAST(symbol AS VARCHAR) AS symbol,
                        CAST(date AS DATE) AS date,
                        CAST(open AS DOUBLE) AS open,
                        CAST(high AS DOUBLE) AS high,
                        CAST(low AS DOUBLE) AS low,
                        CAST(close AS DOUBLE) AS close,
                        CAST(volume AS BIGINT) AS volume
                    FROM _arrow_stage_1d
                    ORDER BY symbol, date;
                """)

                conn.execute("""
                    CREATE TEMP TABLE _dedup_1d AS
                    SELECT s.* FROM _staging_1d_batch s
                    WHERE NOT EXISTS (
                        SELECT 1 FROM candles_1d_raw c
                        WHERE c.symbol = s.symbol 
                          AND c.date = s.date
                    );
                """)

                res = conn.execute("SELECT count(*) FROM _dedup_1d;").fetchone()
                count = res[0] if res else 0

                if count > 0:
                    conn.execute("""
                        INSERT INTO candles_1d_raw (symbol, date, open, high, low, close, volume)
                        SELECT symbol, date, open, high, low, close, volume FROM _dedup_1d;
                    """)

                conn.execute("DROP TABLE IF EXISTS _dedup_1d;")
                conn.execute("DROP TABLE IF EXISTS _staging_1d_batch;")
                return count
            finally:
                conn.unregister("_arrow_stage_1d")

        return self.db.execute_write_batch(_do_insert)

    def upsert_1d(self, candles: Union[List[dict], pa.Table, pd.DataFrame]) -> int:
        """Upsert daily raw candles (e.g. updating forming/live session candles) via staging."""
        if not candles:
            return 0
        if isinstance(candles, list):
            arrow_table = pa.Table.from_pylist(candles)
        elif isinstance(candles, pd.DataFrame):
            arrow_table = pa.Table.from_pandas(candles)
        else:
            arrow_table = candles

        def _do_upsert(conn: duckdb.DuckDBPyConnection) -> int:
            conn.register("_arrow_upsert_1d", arrow_table)
            try:
                conn.execute("""
                    CREATE TEMP TABLE _staging_upsert_1d AS
                    SELECT 
                        CAST(symbol AS VARCHAR) AS symbol,
                        CAST(date AS DATE) AS date,
                        CAST(open AS DOUBLE) AS open,
                        CAST(high AS DOUBLE) AS high,
                        CAST(low AS DOUBLE) AS low,
                        CAST(close AS DOUBLE) AS close,
                        CAST(volume AS BIGINT) AS volume
                    FROM _arrow_upsert_1d
                    ORDER BY symbol, date;
                """)

                conn.execute("""
                    DELETE FROM candles_1d_raw
                    WHERE EXISTS (
                        SELECT 1 FROM _staging_upsert_1d s
                        WHERE candles_1d_raw.symbol = s.symbol AND candles_1d_raw.date = s.date
                    );
                """)

                conn.execute("""
                    INSERT INTO candles_1d_raw (symbol, date, open, high, low, close, volume)
                    SELECT symbol, date, open, high, low, close, volume FROM _staging_upsert_1d;
                """)

                res = conn.execute("SELECT count(*) FROM _staging_upsert_1d;").fetchone()
                count = res[0] if res else 0

                conn.execute("DROP TABLE IF EXISTS _staging_upsert_1d;")
                return count
            finally:
                conn.unregister("_arrow_upsert_1d")

        return self.db.execute_write_batch(_do_upsert)

    def stage_and_merge_1m(self, staging_table: str) -> int:
        """Merge records from an existing temporary staging table into candles_1m_raw."""
        def _do_merge(conn: duckdb.DuckDBPyConnection) -> int:
            conn.execute(f"""
                CREATE TEMP TABLE _stage_to_merge AS
                SELECT 
                    CAST(s.symbol AS VARCHAR) AS symbol,
                    CAST(s.timestamp AS TIMESTAMP) AS timestamp,
                    CAST(s.open AS DOUBLE) AS open,
                    CAST(s.high AS DOUBLE) AS high,
                    CAST(s.low AS DOUBLE) AS low,
                    CAST(s.close AS DOUBLE) AS close,
                    CAST(s.volume AS BIGINT) AS volume
                FROM {staging_table} s
                WHERE NOT EXISTS (
                    SELECT 1 FROM candles_1m_raw c
                    WHERE c.symbol = s.symbol 
                      AND c.timestamp = CAST(s.timestamp AS TIMESTAMP)
                );
            """)

            res = conn.execute("SELECT count(*) FROM _stage_to_merge;").fetchone()
            count = res[0] if res else 0

            if count > 0:
                conn.execute("""
                    INSERT INTO candles_1m_raw (symbol, timestamp, open, high, low, close, volume)
                    SELECT symbol, timestamp, open, high, low, close, volume FROM _stage_to_merge;
                """)

            conn.execute("DROP TABLE IF EXISTS _stage_to_merge;")
            conn.execute(f"DROP TABLE IF EXISTS {staging_table};")
            return count

        return self.db.execute_write_batch(_do_merge)

    # ---------------------------------------------------------
    # ICandleReader Implementation (Non-blocking Independent Cursors)
    # ---------------------------------------------------------

    def get_raw_candles(
        self,
        symbol: str,
        timeframe: str,
        start: Union[datetime, date],
        end: Union[datetime, date],
        limit: int = 1000,
        cursor: Optional[str] = None,
    ) -> List[Candle]:
        """Query raw persisted candles ordered by timestamp/date ascending."""
        read_cursor = self.db.get_read_cursor()
        try:
            if timeframe == "1m":
                params: List[Any] = [symbol, start, end]
                cursor_clause = ""
                if cursor:
                    cursor_clause = "AND timestamp > ?"
                    params.append(cursor)
                params.append(limit)

                sql = f"""
                    SELECT symbol, timestamp, open, high, low, close, volume
                    FROM candles_1m_raw
                    WHERE symbol = ? 
                      AND timestamp >= ? 
                      AND timestamp <= ?
                      {cursor_clause}
                    ORDER BY timestamp ASC
                    LIMIT ?;
                """
                rows = read_cursor.execute(sql, params).fetchall()
            elif timeframe == "1D":
                params = [symbol, start, end]
                cursor_clause = ""
                if cursor:
                    cursor_clause = "AND date > CAST(? AS DATE)"
                    params.append(cursor)
                params.append(limit)

                sql = f"""
                    SELECT symbol, date, open, high, low, close, volume
                    FROM candles_1d_raw
                    WHERE symbol = ? 
                      AND date >= CAST(? AS DATE) 
                      AND date <= CAST(? AS DATE)
                      {cursor_clause}
                    ORDER BY date ASC
                    LIMIT ?;
                """
                rows = read_cursor.execute(sql, params).fetchall()
            else:
                raise ValueError(f"Raw candle query only supports base timeframes ('1m', '1D'), got: {timeframe}")

            return [
                Candle(
                    symbol=r[0],
                    timestamp=r[1],
                    open=float(r[2]),
                    high=float(r[3]),
                    low=float(r[4]),
                    close=float(r[5]),
                    volume=int(r[6]),
                )
                for r in rows
            ]
        finally:
            read_cursor.close()

    def get_adjusted_candles(
        self,
        symbol: str,
        timeframe: str,
        start: Union[datetime, date],
        end: Union[datetime, date],
        limit: int = 1000,
    ) -> List[Candle]:
        """Query split-adjusted candles derived from corporate action factors view."""
        read_cursor = self.db.get_read_cursor()
        try:
            if timeframe == "1m":
                sql = """
                    SELECT symbol, timestamp, open, high, low, close, volume
                    FROM candles_1m_adjusted
                    WHERE symbol = ? 
                      AND timestamp >= ? 
                      AND timestamp <= ?
                    ORDER BY timestamp ASC
                    LIMIT ?;
                """
                rows = read_cursor.execute(sql, [symbol, start, end, limit]).fetchall()
            elif timeframe == "1D":
                sql = """
                    SELECT symbol, date, open, high, low, close, volume
                    FROM candles_1d_adjusted
                    WHERE symbol = ? 
                      AND date >= CAST(? AS DATE) 
                      AND date <= CAST(? AS DATE)
                    ORDER BY date ASC
                    LIMIT ?;
                """
                rows = read_cursor.execute(sql, [symbol, start, end, limit]).fetchall()
            else:
                raise ValueError(f"Adjusted candle query only supports base timeframes ('1m', '1D'), got: {timeframe}")

            return [
                Candle(
                    symbol=r[0],
                    timestamp=r[1],
                    open=float(r[2]),
                    high=float(r[3]),
                    low=float(r[4]),
                    close=float(r[5]),
                    volume=int(r[6]),
                )
                for r in rows
            ]
        finally:
            read_cursor.close()

    def get_latest_candle(self, symbol: str, timeframe: str) -> Optional[Candle]:
        """Fetch the single most recent candle for the given symbol and timeframe."""
        read_cursor = self.db.get_read_cursor()
        try:
            if timeframe == "1m":
                sql = """
                    SELECT symbol, timestamp, open, high, low, close, volume
                    FROM candles_1m_raw
                    WHERE symbol = ?
                    ORDER BY timestamp DESC
                    LIMIT 1;
                """
            elif timeframe == "1D":
                sql = """
                    SELECT symbol, date, open, high, low, close, volume
                    FROM candles_1d_raw
                    WHERE symbol = ?
                    ORDER BY date DESC
                    LIMIT 1;
                """
            else:
                raise ValueError(f"get_latest_candle only supports base timeframes ('1m', '1D'), got: {timeframe}")

            row = read_cursor.execute(sql, [symbol]).fetchone()
            if row is None:
                return None

            return Candle(
                symbol=row[0],
                timestamp=row[1],
                open=float(row[2]),
                high=float(row[3]),
                low=float(row[4]),
                close=float(row[5]),
                volume=int(row[6]),
            )
        finally:
            read_cursor.close()
