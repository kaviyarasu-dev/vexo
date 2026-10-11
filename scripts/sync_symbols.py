"""Master Symbol and Universe Synchronization Script.
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md and plan/03_SYMBOL_MASTER_AND_UNIVERSE_MANAGER.md.

Performs:
1. Database schema verification / initialization.
2. Official NSE index constituent fetching (Nifty 50, Next 50, Midcap 150, Smallcap 250).
3. Fyers Symbol Master streaming ingestion and equity parsing.
4. Mathematically strict Tier Classification:
   - Tier 1: 100 stocks (50 Nifty 50 + 50 Nifty Next 50)
   - Tier 2: 150 stocks (Nifty Midcap 150)
   - Tier 3: 250 stocks (Nifty Smallcap 250)
   - Total Tiers 1-3: Exactly 500 stocks (Exact Nifty 500)
   - Tier 4: All remaining active NSE equities (~1,500 - 1,700 stocks)
5. Upsert into DuckDB symbols table.
6. Checkpoint seeding for 1m (Tiers 1-3) and 1D (Tiers 1-4).
7. Market holidays synchronization into market_holidays table.
"""

import logging
from pathlib import Path
import sys
from typing import Dict, List

# Ensure project root is in sys.path when script is run directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.connection import get_db
from db.migrations import init_db
from scripts.fetch_nse_constituents import fetch_all_constituents
from scripts.fetch_symbol_master import download_fyers_symbol_master
from services.symbol_master_parser import SymbolMasterParser
from services.symbol_service import SymbolService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("sync_symbols")


def sync_all_symbols() -> Dict[str, int]:
    """Orchestrates full symbol master sync, universe sorting, and checkpoint seeding."""
    logger.info("Initializing DuckDB schema and tables...")
    init_db()

    service = SymbolService(get_db())

    # 1. Fetch official NSE index constituents
    logger.info("Step 1/5: Fetching official NSE index constituents...")
    constituents = fetch_all_constituents()

    # 2. Ingest and parse Fyers Symbol Master
    logger.info("Step 2/5: Ingesting Fyers NSE Capital Market symbol master...")
    raw_csv = download_fyers_symbol_master()
    symbols = SymbolMasterParser.parse_csv_content(raw_csv)
    logger.info("Parsed %d active equity symbols from raw master.", len(symbols))

    # 3. Classify into Tiers 1-4 with exact arithmetic
    logger.info("Step 3/5: Sorting universe into Tiers 1 to 4...")
    classified_symbols = service.classify_and_apply_tiers(symbols, constituents)

    # 4. Upsert into database
    logger.info("Step 4/5: Upserting symbols into DuckDB...")
    upserted_count = service.upsert_symbols(classified_symbols)

    # 5. Seed download checkpoints for 1m and 1D
    logger.info("Step 5/5: Seeding download checkpoints...")
    cp_1m, cp_1d = service.seed_download_checkpoints()

    # 6. Synchronize trading holidays
    logger.info("Synchronizing official market holidays...")
    holiday_count = service.sync_market_holidays()

    # 7. Verification of exact arithmetic
    cursor = service.db.get_read_cursor()
    try:
        t1 = cursor.execute("SELECT count(*) FROM symbols WHERE tier = 1;").fetchone()[0]
        t2 = cursor.execute("SELECT count(*) FROM symbols WHERE tier = 2;").fetchone()[0]
        t3 = cursor.execute("SELECT count(*) FROM symbols WHERE tier = 3;").fetchone()[0]
        t4 = cursor.execute("SELECT count(*) FROM symbols WHERE tier = 4;").fetchone()[0]
        total_active = cursor.execute("SELECT count(*) FROM symbols WHERE is_active = TRUE;").fetchone()[0]
    finally:
        cursor.close()

    total_nifty_500 = t1 + t2 + t3

    logger.info("=" * 60)
    logger.info("UNIVERSE & SYMBOL MASTER SYNC SUMMARY")
    logger.info("=" * 60)
    logger.info("Tier 1 (Nifty 100):          %d (Target: 100)", t1)
    logger.info("Tier 2 (Nifty Midcap 150):   %d (Target: 150)", t2)
    logger.info("Tier 3 (Nifty Smallcap 250): %d (Target: 250)", t3)
    logger.info("Total Nifty 500 (Tiers 1-3): %d (Target: 500)", total_nifty_500)
    logger.info("Tier 4 (Broad Market Tail):  %d", t4)
    logger.info("Total Active Equities:       %d", total_active)
    logger.info("Checkpoints Seeded (1m):     %d", cp_1m)
    logger.info("Checkpoints Seeded (1D):     %d", cp_1d)
    logger.info("Market Holidays Synced:      %d", holiday_count)
    logger.info("=" * 60)

    # Enforce strict mathematical contract
    assert t1 == 100, f"Critical: Tier 1 count {t1} != 100"
    assert t2 == 150, f"Critical: Tier 2 count {t2} != 150"
    assert t3 == 250, f"Critical: Tier 3 count {t3} != 250"
    assert total_nifty_500 == 500, f"Critical: Tiers 1-3 sum {total_nifty_500} != 500"

    return {
        "tier_1": t1,
        "tier_2": t2,
        "tier_3": t3,
        "tier_4": t4,
        "total_nifty_500": total_nifty_500,
        "total_active": total_active,
        "checkpoints_1m": cp_1m,
        "checkpoints_1d": cp_1d,
        "holidays": holiday_count,
    }


def main() -> None:
    """Execution entry point."""
    try:
        summary = sync_all_symbols()
        print("\nSUCCESS: Phase 03 Symbol Master and Universe Sorter completed successfully.")
        print(f"Tier 1: {summary['tier_1']} | Tier 2: {summary['tier_2']} | Tier 3: {summary['tier_3']} | Total 500: {summary['total_nifty_500']}")
        print(f"Total Active Instruments: {summary['total_active']}")
    except Exception as exc:
        logger.error("Failed during symbol sync: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
