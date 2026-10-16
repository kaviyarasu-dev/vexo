"""Entry point for full initial historical backfill.
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md and plan/04_HISTORICAL_DOWNLOADER_ENGINE.md.

Runs full universe historical ingestion:
- 1m: Nifty 500 (Tiers 1, 2, 3) for 5 years
- 1D: All Active Equities (Tiers 1, 2, 3, 4) for 15 years
"""

import argparse
import logging
from pathlib import Path
import sys

# Ensure project root is in sys.path when script is run directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_historical_download import main as runner_main

logger = logging.getLogger("run_initial_backfill")


def main() -> None:
    """Executes initial backfill across 1m and 1D timeframes."""
    # If no CLI arguments provided, default to running both 1m and 1D
    if len(sys.argv) == 1:
        sys.argv.extend(["--timeframe", "both"])
    runner_main()


if __name__ == "__main__":
    main()
