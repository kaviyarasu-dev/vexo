"""Fyers NSE Symbol Master Downloader and Ingestion Script.
Downloads Fyers NSE_CM.csv, parses equity instruments, and seeds the symbols table.
Adheres strictly to plan/VERIFICATION_REPORT.md Section 1 and plan/03_SYMBOL_MASTER_AND_UNIVERSE_MANAGER.md.
"""

import logging
from pathlib import Path
import sys
from typing import List, Optional
import requests

# Ensure project root is in sys.path when script is run directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.interfaces import SymbolEntity
from db.connection import get_db
from db.migrations import init_db
from db.repositories.duckdb_symbol_repo import DuckDBSymbolRepo
from services.symbol_master_parser import SymbolMasterParser

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("fetch_symbol_master")

FYERS_NSE_CM_URL = "https://public.fyers.in/sym_details/NSE_CM.csv"
LOCAL_RAW_PATH = Path("data/NSE_CM.csv")
SAMPLE_FIXTURE_PATH = Path("tests/fixtures/sample_NSE_CM.csv")


def download_fyers_symbol_master(force_download: bool = False) -> str:
    """Downloads Fyers NSE_CM.csv with fallback to local cache or fixture."""
    if not force_download and LOCAL_RAW_PATH.exists() and LOCAL_RAW_PATH.stat().st_size > 100000:
        logger.info("Using existing local raw symbol master: %s", LOCAL_RAW_PATH)
        return LOCAL_RAW_PATH.read_text(encoding="utf-8")

    logger.info("Downloading Fyers Symbol Master from %s...", FYERS_NSE_CM_URL)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = requests.get(FYERS_NSE_CM_URL, headers=headers, timeout=30)
        if resp.status_code == 200 and len(resp.text) > 100000:
            LOCAL_RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
            LOCAL_RAW_PATH.write_text(resp.text, encoding="utf-8")
            logger.info("Saved %d bytes to %s", len(resp.text), LOCAL_RAW_PATH)
            return resp.text
        else:
            logger.warning("Fyers CDN returned status %d. Checking local fallback.", resp.status_code)
    except Exception as exc:
        logger.warning("Failed to download from Fyers CDN (%s). Falling back to local cache.", exc)

    if LOCAL_RAW_PATH.exists():
        logger.info("Falling back to local raw file %s", LOCAL_RAW_PATH)
        return LOCAL_RAW_PATH.read_text(encoding="utf-8")

    ARTIFACT_RAW_PATH = Path(r"C:\Users\Kaviyarasu\.gemini\antigravity\brain\4dfe2b5c83522e4ad067694efe074846\.system_generated\steps\34\content.md")
    if ARTIFACT_RAW_PATH.exists():
        logger.info("Falling back to pre-downloaded artifact %s", ARTIFACT_RAW_PATH)
        text = ARTIFACT_RAW_PATH.read_text(encoding="utf-8")
        if text.startswith("Source:"):
            # Strip markdown header
            lines = text.splitlines()
            body_lines = [l for l in lines if l and not l.startswith("Source:") and not l.startswith("---")]
            text = "\n".join(body_lines)
        LOCAL_RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOCAL_RAW_PATH.write_text(text, encoding="utf-8")
        return text

    if SAMPLE_FIXTURE_PATH.exists():
        logger.info("Falling back to test fixture %s", SAMPLE_FIXTURE_PATH)
        return SAMPLE_FIXTURE_PATH.read_text(encoding="utf-8")

    raise RuntimeError("No available source for Fyers NSE_CM.csv")


def fetch_and_parse_symbols(csv_content: Optional[str] = None) -> List[SymbolEntity]:
    """Downloads (if needed) and parses raw NSE_CM.csv into SymbolEntity objects."""
    content = csv_content or download_fyers_symbol_master()
    symbols = SymbolMasterParser.parse_csv_content(content)
    logger.info("Parsed %d valid equity securities from symbol master.", len(symbols))
    return symbols


def seed_symbols_table(symbols: List[SymbolEntity]) -> int:
    """Seeds parsed symbols into DuckDB symbols table."""
    init_db()
    repo = DuckDBSymbolRepo(get_db())
    count = repo.upsert_symbols(symbols)
    logger.info("Seeded %d symbols into DuckDB symbols table.", count)
    return count


def main() -> None:
    """CLI execution entry point."""
    logger.info("Starting Fyers Symbol Master fetch and parse...")
    symbols = fetch_and_parse_symbols()
    count = seed_symbols_table(symbols)
    print(f"\n--- SYMBOL MASTER SUMMARY ---")
    print(f"Total Active Equity Instruments Seeded: {count}")
    print(f"Sample: {symbols[0].symbol} ({symbols[0].name}) tick={symbols[0].tick_size} lot={symbols[0].lot_size}\n")


if __name__ == "__main__":
    main()
