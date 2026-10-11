"""Script to fetch NSE index constituents and update index caches.
Adheres to plan/03_SYMBOL_MASTER_AND_UNIVERSE_MANAGER.md.
Delegates to scripts/fetch_nse_constituents.py.
"""

from pathlib import Path
import sys

# Ensure project root is in sys.path when script is run directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.fetch_nse_constituents import fetch_all_constituents, main

if __name__ == "__main__":
    main()
