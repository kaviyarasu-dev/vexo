"""Database schema definitions and idempotent migration runner.
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md Section 4 and plan/02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md Section 5.
"""

import logging
from typing import Optional
from db.connection import get_db, DuckDBConnectionManager

logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = "1.0.0"

# Canonical DDLs for all 9 persistent tables
SCHEMA_TABLES_DDL = {
    "schema_version": """
        CREATE TABLE IF NOT EXISTS schema_version (
            version VARCHAR PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description VARCHAR NOT NULL
        );
    """,
    "symbols": """
        CREATE TABLE IF NOT EXISTS symbols (
            symbol VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            isin VARCHAR,
            exchange VARCHAR DEFAULT 'NSE',
            segment VARCHAR DEFAULT 'EQUITY',
            series VARCHAR DEFAULT 'EQ',
            lot_size INTEGER DEFAULT 1,
            tick_size DOUBLE DEFAULT 0.05,
            category VARCHAR,
            tier INTEGER NOT NULL DEFAULT 4,
            priority_rank INTEGER DEFAULT 9999,
            listing_date DATE,
            is_active BOOLEAN DEFAULT TRUE,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """,
    "candles_1m_raw": """
        CREATE TABLE IF NOT EXISTS candles_1m_raw (
            symbol VARCHAR NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            open DOUBLE NOT NULL,
            high DOUBLE NOT NULL,
            low DOUBLE NOT NULL,
            close DOUBLE NOT NULL,
            volume BIGINT NOT NULL
        );
    """,
    "candles_1d_raw": """
        CREATE TABLE IF NOT EXISTS candles_1d_raw (
            symbol VARCHAR NOT NULL,
            date DATE NOT NULL,
            open DOUBLE NOT NULL,
            high DOUBLE NOT NULL,
            low DOUBLE NOT NULL,
            close DOUBLE NOT NULL,
            volume BIGINT NOT NULL
        );
    """,
    "corporate_actions": """
        CREATE TABLE IF NOT EXISTS corporate_actions (
            id VARCHAR PRIMARY KEY,
            symbol VARCHAR NOT NULL,
            action_type VARCHAR NOT NULL,
            ex_date DATE NOT NULL,
            record_date DATE,
            ratio_from DOUBLE,
            ratio_to DOUBLE,
            dividend_amount DOUBLE,
            description VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """,
    "adjustment_factors": """
        CREATE TABLE IF NOT EXISTS adjustment_factors (
            symbol VARCHAR NOT NULL,
            ex_date DATE NOT NULL,
            factor_price DOUBLE NOT NULL,
            factor_volume DOUBLE NOT NULL,
            PRIMARY KEY (symbol, ex_date)
        );
    """,
    "download_checkpoints": """
        CREATE TABLE IF NOT EXISTS download_checkpoints (
            symbol VARCHAR NOT NULL,
            timeframe VARCHAR NOT NULL,
            earliest_ts TIMESTAMP,
            latest_ts TIMESTAMP,
            total_candles INTEGER DEFAULT 0,
            status VARCHAR DEFAULT 'PENDING',
            consecutive_empty_count INTEGER DEFAULT 0,
            last_attempt_at TIMESTAMP,
            error_message VARCHAR,
            PRIMARY KEY (symbol, timeframe)
        );
    """,
    "market_holidays": """
        CREATE TABLE IF NOT EXISTS market_holidays (
            holiday_date DATE PRIMARY KEY,
            description VARCHAR NOT NULL,
            is_special_session BOOLEAN DEFAULT FALSE,
            trading_start TIME DEFAULT '09:15:00',
            trading_end TIME DEFAULT '15:30:00'
        );
    """,
    "job_logs": """
        CREATE TABLE IF NOT EXISTS job_logs (
            job_id VARCHAR PRIMARY KEY,
            job_type VARCHAR NOT NULL,
            started_at TIMESTAMP NOT NULL,
            completed_at TIMESTAMP,
            symbols_processed INTEGER DEFAULT 0,
            symbols_failed INTEGER DEFAULT 0,
            total_candles_ingested BIGINT DEFAULT 0,
            status VARCHAR NOT NULL,
            details VARCHAR
        );
    """,
    "journal_entries": """
        CREATE TABLE IF NOT EXISTS journal_entries (
            trade_id VARCHAR PRIMARY KEY,
            symbol VARCHAR NOT NULL,
            trade_type VARCHAR NOT NULL,
            direction VARCHAR NOT NULL,
            entry_time TIMESTAMP NOT NULL,
            entry_price DOUBLE NOT NULL,
            exit_time TIMESTAMP,
            exit_price DOUBLE,
            quantity INTEGER NOT NULL,
            stop_loss DOUBLE NOT NULL,
            take_profit DOUBLE,
            pnl_gross DOUBLE,
            total_charges DOUBLE,
            pnl_net DOUBLE,
            r_multiple DOUBLE,
            mistake_tags VARCHAR,
            notes VARCHAR
        );
    """,
    "paper_account": """
        CREATE TABLE IF NOT EXISTS paper_account (
            account_id VARCHAR PRIMARY KEY,
            balance DOUBLE NOT NULL,
            initial_balance DOUBLE DEFAULT 1000000.0,
            realized_pnl DOUBLE DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """,
    "paper_positions": """
        CREATE TABLE IF NOT EXISTS paper_positions (
            symbol VARCHAR PRIMARY KEY,
            quantity INTEGER NOT NULL,
            average_price DOUBLE NOT NULL,
            side VARCHAR DEFAULT 'LONG',
            trade_type VARCHAR DEFAULT 'DELIVERY',
            stop_loss DOUBLE,
            take_profit DOUBLE,
            trailing_sl_pct DOUBLE,
            highest_price DOUBLE,
            lowest_price DOUBLE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """,
    "paper_orders": """
        CREATE TABLE IF NOT EXISTS paper_orders (
            order_id VARCHAR PRIMARY KEY,
            symbol VARCHAR NOT NULL,
            side VARCHAR NOT NULL,
            order_type VARCHAR NOT NULL DEFAULT 'MARKET',
            trade_type VARCHAR NOT NULL DEFAULT 'DELIVERY',
            quantity INTEGER NOT NULL,
            price DOUBLE,
            trigger_price DOUBLE,
            status VARCHAR NOT NULL DEFAULT 'FILLED',
            stop_loss DOUBLE,
            take_profit DOUBLE,
            trailing_sl_pct DOUBLE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            filled_at TIMESTAMP
        );
    """,
    "paper_trades": """
        CREATE TABLE IF NOT EXISTS paper_trades (
            trade_id VARCHAR PRIMARY KEY,
            order_id VARCHAR NOT NULL,
            symbol VARCHAR NOT NULL,
            side VARCHAR NOT NULL,
            quantity INTEGER NOT NULL,
            fill_price DOUBLE NOT NULL,
            brokerage DOUBLE NOT NULL DEFAULT 0.0,
            stt DOUBLE NOT NULL DEFAULT 0.0,
            total_charges DOUBLE NOT NULL DEFAULT 0.0,
            gross_pnl DOUBLE DEFAULT 0.0,
            net_pnl DOUBLE DEFAULT 0.0,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """,
    "paper_auto_strategies": """
        CREATE TABLE IF NOT EXISTS paper_auto_strategies (
            strategy_id VARCHAR PRIMARY KEY,
            strategy_name VARCHAR NOT NULL,
            symbol VARCHAR NOT NULL,
            timeframe VARCHAR NOT NULL DEFAULT '1D',
            parameters JSON NOT NULL,
            trade_type VARCHAR NOT NULL DEFAULT 'DELIVERY',
            allocated_capital DOUBLE NOT NULL DEFAULT 100000.0,
            status VARCHAR NOT NULL DEFAULT 'ACTIVE',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """,
    "chart_drawings": """
        CREATE TABLE IF NOT EXISTS chart_drawings (
            drawing_id VARCHAR PRIMARY KEY,
            symbol VARCHAR NOT NULL,
            tool_type VARCHAR NOT NULL,
            points JSON NOT NULL,
            style JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """,
    "option_chain_snapshots": """
        CREATE TABLE IF NOT EXISTS option_chain_snapshots (
            snapshot_date DATE NOT NULL,
            underlying_symbol VARCHAR NOT NULL,
            expiry_date DATE NOT NULL,
            strike_price DOUBLE NOT NULL,
            option_type VARCHAR NOT NULL,
            ltp DOUBLE,
            oi BIGINT,
            volume BIGINT,
            iv DOUBLE,
            delta DOUBLE,
            gamma DOUBLE,
            theta DOUBLE,
            vega DOUBLE,
            captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (snapshot_date, underlying_symbol, expiry_date, strike_price, option_type)
        );
    """
}

# Dynamic SQL views for split-adjusted candles
SCHEMA_VIEWS_DDL = {
    "candles_1d_adjusted": """
        CREATE OR REPLACE VIEW candles_1d_adjusted AS
        SELECT 
            c.symbol,
            c.date,
            c.open * COALESCE(af.factor_price, 1.0) AS open,
            c.high * COALESCE(af.factor_price, 1.0) AS high,
            c.low * COALESCE(af.factor_price, 1.0) AS low,
            c.close * COALESCE(af.factor_price, 1.0) AS close,
            CAST(c.volume * COALESCE(af.factor_volume, 1.0) AS BIGINT) AS volume
        FROM candles_1d_raw c
        LEFT JOIN adjustment_factors af 
            ON c.symbol = af.symbol AND c.date <= af.ex_date;
    """,
    "candles_1m_adjusted": """
        CREATE OR REPLACE VIEW candles_1m_adjusted AS
        SELECT 
            c.symbol,
            c.timestamp,
            c.open * COALESCE(af.factor_price, 1.0) AS open,
            c.high * COALESCE(af.factor_price, 1.0) AS high,
            c.low * COALESCE(af.factor_price, 1.0) AS low,
            c.close * COALESCE(af.factor_price, 1.0) AS close,
            CAST(c.volume * COALESCE(af.factor_volume, 1.0) AS BIGINT) AS volume
        FROM candles_1m_raw c
        LEFT JOIN adjustment_factors af 
            ON c.symbol = af.symbol AND CAST(c.timestamp AS DATE) <= af.ex_date;
    """,
}


def init_db(db_path: Optional[str] = None, manager: Optional[DuckDBConnectionManager] = None) -> None:
    """Idempotently initialize all canonical tables, dynamic views, and migration record.
    
    Can be run repeatedly without duplicating or corrupting existing data.
    """
    db = manager or get_db(db_path)

    def _apply_migrations(conn):
        # 1. Create canonical tables
        for table_name, ddl in SCHEMA_TABLES_DDL.items():
            conn.execute(ddl)

        # 2. Create dynamic views
        for view_name, ddl in SCHEMA_VIEWS_DDL.items():
            conn.execute(ddl)

        # 3. Check and record schema version
        row = conn.execute(
            "SELECT version FROM schema_version WHERE version = ?",
            [CURRENT_SCHEMA_VERSION]
        ).fetchone()

        if row is None:
            conn.execute(
                """
                INSERT INTO schema_version (version, description)
                VALUES (?, ?)
                """,
                [CURRENT_SCHEMA_VERSION, f"Initial canonical schema v{CURRENT_SCHEMA_VERSION}"]
            )
            logger.info("Applied database migration %s", CURRENT_SCHEMA_VERSION)
        else:
            logger.debug("Database migration %s already applied", CURRENT_SCHEMA_VERSION)

    db.execute_write_batch(_apply_migrations)


def get_current_schema_version(manager: Optional[DuckDBConnectionManager] = None) -> Optional[str]:
    """Returns the latest applied schema version string or None if uninitialized."""
    db = manager or get_db()
    cursor = db.get_read_cursor()
    try:
        res = cursor.execute("SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1").fetchone()
        return res[0] if res else None
    except Exception:
        return None
    finally:
        cursor.close()
