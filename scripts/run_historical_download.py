"""Historical Data Ingestion Engine CLI runner.
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md and plan/04_HISTORICAL_DOWNLOADER_ENGINE.md.

Usage:
    python scripts/run_historical_download.py --timeframe 1m --tiers 1,2,3
    python scripts/run_historical_download.py --timeframe 1D --tiers 1,2,3,4
    python scripts/run_historical_download.py --symbols NSE:RELIANCE-EQ --timeframe 1m
"""

import argparse
from datetime import datetime
import logging
from pathlib import Path
import sys
import time

# Ensure project root is in sys.path when script is run directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import get_settings
from core.rate_governor import get_rate_governor
from db.connection import get_db
from db.migrations import init_db
from services.downloader_service import HistoricalDownloader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("run_historical_download")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run resilient historical market data ingestion with rate governing."
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        choices=["1m", "1D", "both"],
        default="1m",
        help="Timeframe to download ('1m', '1D', or 'both'). Default: 1m",
    )
    parser.add_argument(
        "--tiers",
        type=str,
        default=None,
        help="Comma-separated tiers to download (e.g. '1', '1,2,3'). Default: 1,2,3 for 1m; 1,2,3,4 for 1D",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated list of symbols (e.g. 'NSE:RELIANCE-EQ,NSE:INFY-EQ')",
    )
    parser.add_argument(
        "--years-1m",
        type=int,
        default=None,
        help="Target history depth in years for 1m (default from settings: 5)",
    )
    parser.add_argument(
        "--years-1d",
        type=int,
        default=None,
        help="Target history depth in years for 1D (default from settings: 15)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force redownload even if marked COMPLETED in checkpoints table",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Download all stocks (Tiers 1, 2, 3, 4) across both timeframes (1m and 1D)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()

    if args.all:
        args.timeframe = "both"
        args.tiers = "1,2,3,4"

    try:
        logger.info("Initializing DuckDB schema and migration checks...")
        init_db()
        downloader = HistoricalDownloader(settings=settings)
        downloader.register_signal_handlers()
    except Exception as exc:
        err_msg = str(exc)
        if "used by another process" in err_msg or "Cannot open file" in err_msg or "DatabaseLockError" in type(exc).__name__:
            logger.error(
                "\n" + "=" * 70 + "\n"
                "[DUCKDB LOCK DETECTED]: The database file is currently locked by 'start_server.bat'.\n"
                "On Windows, DuckDB allows only ONE process to write to data/market_data.duckdb at a time.\n\n"
                "HOW TO PROCEED:\n"
                "  1. Go to your 'start_server.bat' terminal window and press Ctrl+C to stop the server.\n"
                "  2. Re-run this download command to ingest your historical data.\n"
                "  3. Once finished (or paused with Ctrl+C), re-run '.\\start_server.bat' to view the charts!\n"
                + "=" * 70
            )
            sys.exit(1)
        raise

    symbols_list = [s.strip() for s in args.symbols.split(",")] if args.symbols else None

    timeframes_to_run = ["1m", "1D"] if args.timeframe == "both" else [args.timeframe]

    for tf in timeframes_to_run:
        # Determine tiers
        if args.tiers:
            tiers = [int(t.strip()) for t in args.tiers.split(",")]
        elif tf == "1m":
            tiers = [1, 2, 3]  # Nifty 500
        else:
            tiers = [1, 2, 3, 4]  # All active equities

        years = args.years_1m if tf == "1m" else args.years_1d
        if years is None:
            years = settings.DEFAULT_1M_HISTORY_YEARS if tf == "1m" else settings.DEFAULT_1D_HISTORY_YEARS

        logger.info(
            "=== Starting Historical Download: Timeframe=%s, Tiers=%s, Years=%s, Force=%s ===",
            tf, tiers if not symbols_list else f"Custom({len(symbols_list)})", years, args.force
        )

        status = downloader.run_backfill(
            timeframe=tf,
            tiers=tiers if not symbols_list else None,
            symbols=symbols_list,
            target_years=years,
            force=args.force,
        )

        logger.info(
            "=== Finished %s Download: Completed=%d, Failed=%d, Candles Ingested=%d, Elapsed=%.1fs ===",
            tf,
            status["symbols_completed"],
            status["symbols_failed"],
            status["total_candles_ingested"],
            status["elapsed_seconds"],
        )


if __name__ == "__main__":
    main()
