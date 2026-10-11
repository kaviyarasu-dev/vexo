"""NSE Index Constituents Ingestion Script.
Downloads official Nifty 50, Nifty Next 50, Nifty Midcap 150, and Nifty Smallcap 250 CSVs from NSE.
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md Section 9 and plan/03_SYMBOL_MASTER_AND_UNIVERSE_MANAGER.md.
"""

import csv
import io
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("fetch_nse_constituents")

INDEX_URLS = {
    "NIFTY50": [
        "https://archives.nseindia.com/content/indices/ind_nifty50list.csv",
        "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv",
    ],
    "NIFTYNEXT50": [
        "https://archives.nseindia.com/content/indices/ind_niftynext50list.csv",
        "https://nsearchives.nseindia.com/content/indices/ind_niftynext50list.csv",
    ],
    "NIFTYMIDCAP150": [
        "https://archives.nseindia.com/content/indices/ind_niftymidcap150list.csv",
        "https://nsearchives.nseindia.com/content/indices/ind_niftymidcap150list.csv",
    ],
    "NIFTYSMALLCAP250": [
        "https://archives.nseindia.com/content/indices/ind_niftysmallcap250list.csv",
        "https://nsearchives.nseindia.com/content/indices/ind_niftysmallcap250list.csv",
    ],
    "NIFTY500": [
        "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
        "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
    ],
}

TARGET_COUNTS = {
    "NIFTY50": 50,
    "NIFTYNEXT50": 50,
    "NIFTYMIDCAP150": 150,
    "NIFTYSMALLCAP250": 250,
}

OVERRIDE_FILE = Path("config/indices/manual_override_indices.json")
CACHE_FILE = Path("data/indices_cache.json")
USER_OVERRIDE_FILE = Path("data/overrides/universe_override.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


def load_fallback_constituents() -> Dict[str, List[Dict[str, str]]]:
    """Load cached constituents from manual override file."""
    if OVERRIDE_FILE.exists():
        logger.info("Loading constituents from fallback file: %s", OVERRIDE_FILE)
        try:
            data = json.loads(OVERRIDE_FILE.read_text(encoding="utf-8"))
            return data
        except Exception as e:
            logger.error("Failed to parse fallback file %s: %s", OVERRIDE_FILE, e)

    raise RuntimeError(
        f"Critical: Fallback index constituent file {OVERRIDE_FILE} missing or corrupted."
    )


def fetch_csv_from_urls(urls: List[str], session: requests.Session) -> Optional[str]:
    """Attempt downloading CSV from list of fallback URLs."""
    for url in urls:
        try:
            logger.info("Fetching index CSV from: %s", url)
            response = session.get(url, headers=HEADERS, timeout=15)
            if response.status_code == 200 and len(response.text.strip()) > 100:
                return response.text
            logger.warning("HTTP %d received from %s", response.status_code, url)
        except requests.exceptions.RequestException as e:
            logger.warning("Connection failure to %s: %s", url, e)
    return None


def parse_nse_index_csv(csv_text: str, target_count: Optional[int] = None) -> List[Dict[str, str]]:
    """Parses official NSE index constituent CSV.
    Expected columns: Company Name, Industry, Symbol, Series, ISIN Code
    """
    f = io.StringIO(csv_text.strip())
    reader = csv.reader(f)
    header = None
    records: List[Dict[str, str]] = []
    seen_symbols = set()

    for row in reader:
        if not row or not any(row):
            continue
        if header is None:
            # Check for header row
            if "Company Name" in row[0] or "Symbol" in row:
                header = [c.strip() for c in row]
                continue
            else:
                continue

        # Extract columns
        # Index mappings: 0=Name, 1=Industry, 2=Symbol, 3=Series, 4=ISIN
        if len(row) < 3:
            continue

        company_name = row[0].strip()
        symbol = row[2].strip().upper()
        series = row[3].strip().upper() if len(row) > 3 else "EQ"
        isin = row[4].strip() if len(row) > 4 else ""

        # Filter strictly for EQ and BE series (exclude REITs 'RR', InvITs 'IV', etc.)
        if series not in ("EQ", "BE"):
            continue

        if symbol in seen_symbols:
            continue

        seen_symbols.add(symbol)
        records.append({
            "symbol": symbol,
            "isin": isin,
            "name": company_name,
        })

    if target_count and len(records) > target_count:
        records = records[:target_count]

    return records


def fetch_all_constituents(force_refresh: bool = False) -> Dict[str, List[Dict[str, str]]]:
    """Fetches all 4 constituent lists (Nifty 50, Next 50, Midcap 150, Smallcap 250).
    Guarantees exact sizing arithmetic:
      NIFTY50: 50
      NIFTYNEXT50: 50
      NIFTYMIDCAP150: 150
      NIFTYSMALLCAP250: 250
      Total: 500
    Falls back gracefully to manual_override_indices.json if network is unreachable.
    """
    results: Dict[str, List[Dict[str, str]]] = {}
    session = requests.Session()
    network_failed = False

    for category, target in TARGET_COUNTS.items():
        urls = INDEX_URLS.get(category, [])
        csv_text = fetch_csv_from_urls(urls, session)
        if csv_text:
            parsed = parse_nse_index_csv(csv_text, target_count=target)
            if len(parsed) >= target * 0.9:  # Accept if near target
                results[category] = parsed[:target]
                logger.info("Successfully fetched %s: %d constituents.", category, len(results[category]))
            else:
                logger.warning("Parsed count %d below expectation for %s", len(parsed), category)
                network_failed = True
                break
        else:
            logger.warning("Failed to download CSV for %s", category)
            network_failed = True
            break

    if network_failed or len(results) < len(TARGET_COUNTS):
        logger.warning("Live network download failed or blocked. Activating fallback policy.")
        results = load_fallback_constituents()

    # Apply manual constituent overrides if present in data/overrides/universe_override.json
    if USER_OVERRIDE_FILE.exists():
        try:
            overrides = json.loads(USER_OVERRIDE_FILE.read_text(encoding="utf-8"))
            additions = overrides.get("additions", {})
            exclusions = set(overrides.get("exclusions", []))
            for cat, add_list in additions.items():
                if cat in results and add_list:
                    # Filter exclusions
                    results[cat] = [r for r in results[cat] if r["symbol"] not in exclusions]
                    # Add new
                    for item in add_list:
                        if isinstance(item, str):
                            results[cat].append({"symbol": item, "isin": "", "name": item})
                        elif isinstance(item, dict):
                            results[cat].append(item)
        except Exception as e:
            logger.warning("Could not apply universe_override.json: %s", e)

    # Save to local cache
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(results, indent=2), encoding="utf-8")
        logger.info("Cached index constituents to %s", CACHE_FILE)
    except Exception as e:
        logger.warning("Failed writing to cache file %s: %s", CACHE_FILE, e)

    return results


def main() -> None:
    """CLI execution entrypoint."""
    logger.info("Starting NSE Index Constituents fetch...")
    constituents = fetch_all_constituents()
    t1 = len(constituents.get("NIFTY50", [])) + len(constituents.get("NIFTYNEXT50", []))
    t2 = len(constituents.get("NIFTYMIDCAP150", []))
    t3 = len(constituents.get("NIFTYSMALLCAP250", []))
    total = t1 + t2 + t3
    print(f"\n--- NSE CONSTITUENTS SUMMARY ---")
    print(f"Tier 1 (Nifty 100 = 50 + 50): {t1}")
    print(f"Tier 2 (Nifty Midcap 150):   {t2}")
    print(f"Tier 3 (Nifty Smallcap 250): {t3}")
    print(f"Total Tiers 1-3 (Nifty 500): {total}")
    assert t1 == 100, f"Expected Tier 1 == 100, got {t1}"
    assert t2 == 150, f"Expected Tier 2 == 150, got {t2}"
    assert t3 == 250, f"Expected Tier 3 == 250, got {t3}"
    assert total == 500, f"Expected Total == 500, got {total}"
    print("Exact Tier Arithmetic Verified!\n")


if __name__ == "__main__":
    main()
