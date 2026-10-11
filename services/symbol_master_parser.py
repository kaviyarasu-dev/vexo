"""Fyers Symbol Master Parser for NSE Capital Market (NSE_CM.csv).
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md and plan/03_SYMBOL_MASTER_AND_UNIVERSE_MANAGER.md.
"""

import csv
import io
import logging
from typing import Dict, Iterable, List, Optional, Tuple, Union
from core.interfaces import SymbolEntity

logger = logging.getLogger(__name__)

# Blacklisted series codes for non-equity instruments
BLACKLIST_SERIES = {
    "GB",  # Sovereign Gold Bonds
    "GS",  # Government Securities
    "TB",  # Treasury Bills
    "SM",  # SME
    "ST",  # SME Trade-to-Trade
    "P1",  # Preference Shares
    "SG",  # State Govt Securities
    "RR",  # REITs
    "IV",  # InvITs
    "MF",  # Mutual Funds
    "BZ",  # Suspended / Z category
}

# Explicitly allowed series codes for standard equity cash
ALLOWED_SERIES = {"EQ", "BE"}


class SymbolMasterParser:
    """Parses raw Fyers NSE_CM.csv data into canonical SymbolEntity instances.
    
    Structure of Fyers NSE_CM.csv (No header row):
    0: fytoken (Fyers security token)
    1: name (Instrument full description)
    2: instrument_type (0 = Equity/Cash)
    3: lot_size (1 for standard equities)
    4: tick_size (e.g. 0.05)
    5: isin (e.g. INE002A01018)
    6: trading_session
    7: last_update_date
    8: reserved / empty
    9: symbol (e.g. NSE:RELIANCE-EQ)
    10: exchange (10 = NSE)
    11: segment (10 = Capital Market)
    12: scrip_code
    13: ticker / short_name (e.g. RELIANCE)
    14: underlying_scrip_code
    15: strike_price (-1.0 for equities)
    16: option_type (XX for equities)
    17: underlying_fytoken
    18: expiry_date
    """

    @classmethod
    def parse_csv_content(
        cls,
        csv_text: str,
        index_classification: Optional[Dict[str, Tuple[str, int, int]]] = None,
    ) -> List[SymbolEntity]:
        """Parses CSV text content into a list of validated SymbolEntity objects.
        
        Args:
            csv_text: Raw CSV string content.
            index_classification: Optional dictionary mapping ticker/ISIN/symbol to
                                  (category, tier, priority_rank).
        """
        f = io.StringIO(csv_text.strip())
        reader = csv.reader(f)
        return cls.parse_rows(reader, index_classification)

    @classmethod
    def parse_rows(
        cls,
        rows: Iterable[List[str]],
        index_classification: Optional[Dict[str, Tuple[str, int, int]]] = None,
    ) -> List[SymbolEntity]:
        """Parses rows into a list of SymbolEntity objects."""
        symbols: List[SymbolEntity] = []
        classification = index_classification or {}

        for row_idx, row in enumerate(rows):
            # Skip empty rows or comment rows
            if not row or not any(row):
                continue

            # Need at least 14 columns to extract ticker and symbol
            if len(row) < 14:
                continue

            # Skip header row if someone passed a CSV with header
            if row[0].strip().lower() in ("fytoken", "token", "security_id", "source:"):
                continue

            entity = cls.parse_single_row(row, classification)
            if entity is not None:
                symbols.append(entity)

        logger.info("Successfully parsed and filtered %d active equity symbols.", len(symbols))
        return symbols

    @classmethod
    def parse_single_row(
        cls,
        row: List[str],
        classification: Optional[Dict[str, Tuple[str, int, int]]] = None,
    ) -> Optional[SymbolEntity]:
        """Parses and validates a single CSV row. Returns None if row fails equity whitelist."""
        try:
            # 1. Column 2: instrument_type must be 0 (Equity Cash)
            raw_inst_type = row[2].strip()
            if raw_inst_type not in ("0", "0.0"):
                return None

            # 2. Column 9: Symbology string (e.g. "NSE:RELIANCE-EQ")
            symbol_str = row[9].strip()
            if not symbol_str.startswith("NSE:"):
                return None

            # Extract series from symbol (e.g. "EQ" from "NSE:RELIANCE-EQ")
            symbol_parts = symbol_str.split(":")[-1].split("-")
            series = symbol_parts[-1].strip().upper() if len(symbol_parts) > 1 else "EQ"

            # 3. Series filtering: must be in ALLOWED_SERIES and not in BLACKLIST_SERIES
            if series not in ALLOWED_SERIES:
                return None
            if series in BLACKLIST_SERIES:
                return None
            # Exclude debenture series like N1..NZ
            if len(series) == 2 and series[0] == "N" and series[1].isdigit():
                return None

            # 4. Extract ticker from Column 13 or symbol
            raw_ticker = row[13].strip() if len(row) > 13 and row[13].strip() else symbol_parts[0]
            ticker = raw_ticker.upper()

            # 5. Extract name, isin, lot_size, tick_size
            name = row[1].strip()
            if not name:
                return None

            isin = row[5].strip() if len(row) > 5 and row[5].strip() else None
            if isin and isin.lower() == "none":
                isin = None

            try:
                lot_size = int(row[3].strip())
            except (ValueError, IndexError):
                lot_size = 1

            try:
                tick_size = float(row[4].strip())
            except (ValueError, IndexError):
                tick_size = 0.05

            # 6. Apply Tier and Category classification
            # Default is Tier 4 ("OTHERS", rank 9999)
            category = "OTHERS"
            tier = 4
            priority_rank = 9999

            if classification:
                # Match priority: full symbol > ticker > isin
                if symbol_str in classification:
                    category, tier, priority_rank = classification[symbol_str]
                elif ticker in classification:
                    category, tier, priority_rank = classification[ticker]
                elif isin and isin in classification:
                    category, tier, priority_rank = classification[isin]

            return SymbolEntity(
                symbol=symbol_str,
                name=name,
                isin=isin,
                exchange="NSE",
                segment="EQUITY",
                series=series,
                lot_size=lot_size,
                tick_size=tick_size,
                category=category,
                tier=tier,
                priority_rank=priority_rank,
                is_active=True,
            )

        except Exception as exc:
            logger.debug("Failed to parse row %s: %s", row[:5] if row else [], exc)
            return None
