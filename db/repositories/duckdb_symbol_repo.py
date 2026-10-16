"""DuckDB implementation of ISymbolRepository.
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md and plan/02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md.
"""

import logging
from typing import List, Optional
import duckdb

from core.interfaces import ISymbolRepository, SymbolEntity
from db.connection import DuckDBConnectionManager, get_db

logger = logging.getLogger(__name__)


class DuckDBSymbolRepo(ISymbolRepository):
    """Symbol repository for master instrument persistence and search."""

    def __init__(self, db: Optional[DuckDBConnectionManager] = None) -> None:
        self.db = db or get_db()

    def upsert_symbols(self, symbols: List[SymbolEntity]) -> int:
        """Upsert master instrument definitions using DuckDB ON CONFLICT."""
        if not symbols:
            return 0

        def _do_upsert(conn: duckdb.DuckDBPyConnection) -> int:
            from datetime import datetime, timezone
            now_utc = datetime.now(timezone.utc)
            sql = """
                INSERT INTO symbols (
                    symbol, name, isin, exchange, segment, series,
                    lot_size, tick_size, category, tier, priority_rank,
                    listing_date, is_active, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (symbol) DO UPDATE SET
                    name = EXCLUDED.name,
                    isin = EXCLUDED.isin,
                    exchange = EXCLUDED.exchange,
                    segment = EXCLUDED.segment,
                    series = EXCLUDED.series,
                    lot_size = EXCLUDED.lot_size,
                    tick_size = EXCLUDED.tick_size,
                    category = EXCLUDED.category,
                    tier = EXCLUDED.tier,
                    priority_rank = EXCLUDED.priority_rank,
                    listing_date = EXCLUDED.listing_date,
                    is_active = EXCLUDED.is_active,
                    updated_at = EXCLUDED.updated_at;
            """
            for s in symbols:
                conn.execute(sql, [
                    s.symbol,
                    s.name,
                    s.isin,
                    s.exchange,
                    s.segment,
                    s.series,
                    s.lot_size,
                    s.tick_size,
                    s.category,
                    s.tier,
                    s.priority_rank,
                    s.listing_date,
                    s.is_active,
                    now_utc
                ])
            return len(symbols)

        return self.db.execute_write_batch(_do_upsert)

    def search_symbols(self, query: str, category: Optional[str] = None, limit: int = 20) -> List[SymbolEntity]:
        """Search instruments by symbol or name prefix/substring."""
        cursor = self.db.get_read_cursor()
        try:
            pattern = f"%{query}%"
            if category is not None:
                sql = """
                    SELECT symbol, name, isin, exchange, segment, series,
                           lot_size, tick_size, category, tier, priority_rank,
                           listing_date, is_active, updated_at
                    FROM symbols
                    WHERE (symbol ILIKE ? OR name ILIKE ?)
                      AND category = ?
                    ORDER BY priority_rank ASC, symbol ASC
                    LIMIT ?;
                """
                rows = cursor.execute(sql, [pattern, pattern, category, limit]).fetchall()
            else:
                sql = """
                    SELECT symbol, name, isin, exchange, segment, series,
                           lot_size, tick_size, category, tier, priority_rank,
                           listing_date, is_active, updated_at
                    FROM symbols
                    WHERE symbol ILIKE ? OR name ILIKE ?
                    ORDER BY priority_rank ASC, symbol ASC
                    LIMIT ?;
                """
                rows = cursor.execute(sql, [pattern, pattern, limit]).fetchall()

            return [self._row_to_entity(r) for r in rows]
        finally:
            cursor.close()

    def get_by_symbol(self, symbol: str) -> Optional[SymbolEntity]:
        """Fetch instrument metadata by exact canonical symbol."""
        cursor = self.db.get_read_cursor()
        try:
            sql = """
                SELECT symbol, name, isin, exchange, segment, series,
                       lot_size, tick_size, category, tier, priority_rank,
                       listing_date, is_active, updated_at
                FROM symbols
                WHERE symbol = ?;
            """
            row = cursor.execute(sql, [symbol]).fetchone()
            return self._row_to_entity(row) if row else None
        finally:
            cursor.close()

    def list_active_symbols(self, tier: Optional[int] = None) -> List[SymbolEntity]:
        """Fetch active instruments optionally filtered by index tier."""
        cursor = self.db.get_read_cursor()
        try:
            if tier is not None:
                sql = """
                    SELECT symbol, name, isin, exchange, segment, series,
                           lot_size, tick_size, category, tier, priority_rank,
                           listing_date, is_active, updated_at
                    FROM symbols
                    WHERE is_active = TRUE AND tier = ?
                    ORDER BY priority_rank ASC, symbol ASC;
                """
                rows = cursor.execute(sql, [tier]).fetchall()
            else:
                sql = """
                    SELECT symbol, name, isin, exchange, segment, series,
                           lot_size, tick_size, category, tier, priority_rank,
                           listing_date, is_active, updated_at
                    FROM symbols
                    WHERE is_active = TRUE
                    ORDER BY priority_rank ASC, symbol ASC;
                """
                rows = cursor.execute(sql).fetchall()

            return [self._row_to_entity(r) for r in rows]
        finally:
            cursor.close()

    @staticmethod
    def _row_to_entity(r: tuple) -> SymbolEntity:
        return SymbolEntity(
            symbol=r[0],
            name=r[1],
            isin=r[2],
            exchange=r[3],
            segment=r[4],
            series=r[5],
            lot_size=int(r[6]),
            tick_size=float(r[7]),
            category=r[8],
            tier=int(r[9]),
            priority_rank=int(r[10]),
            listing_date=r[11],
            is_active=bool(r[12]),
            updated_at=r[13],
        )
