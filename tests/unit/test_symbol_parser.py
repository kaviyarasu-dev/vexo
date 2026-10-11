"""Unit tests for SymbolMasterParser.
Adheres to plan/00A_CONTRACTS_AND_CONVENTIONS.md and plan/03_SYMBOL_MASTER_AND_UNIVERSE_MANAGER.md.
"""

from pathlib import Path
import pytest

from core.interfaces import SymbolEntity
from services.symbol_master_parser import SymbolMasterParser


@pytest.fixture
def sample_csv_content():
    fixture_path = Path("tests/fixtures/sample_NSE_CM.csv")
    return fixture_path.read_text(encoding="utf-8")


def test_parse_csv_content_equity_filtering(sample_csv_content):
    """Verify that only valid equities are accepted while non-equities are rejected."""
    symbols = SymbolMasterParser.parse_csv_content(sample_csv_content)
    
    # Check that we parsed equities
    assert len(symbols) > 0

    # Whitelist check: all symbols must start with 'NSE:' and have series EQ or BE
    for s in symbols:
        assert s.symbol.startswith("NSE:")
        assert s.series in ("EQ", "BE")
        assert s.exchange == "NSE"
        assert s.segment == "EQUITY"
        assert s.is_active is True

    # Check known stocks
    symbol_names = {s.symbol: s.name for s in symbols}
    assert "NSE:RELIANCE-EQ" in symbol_names
    assert "NSE:TCS-EQ" in symbol_names
    assert "NSE:INFY-EQ" in symbol_names
    assert "NSE:3IINFOLTD-BE" in symbol_names  # Trade-to-trade equity series is included

    # Blacklist check: non-equities must NOT be present
    assert "NSE:SGBAPR28I-GB" not in symbol_names  # Gold bond excluded
    assert "NSE:SCLZC26D-NO" not in symbol_names   # NCD debenture excluded
    assert "NSE:AAKAAR-SM" not in symbol_names    # SME stock excluded
    assert "NSE:AARADHYA-ST" not in symbol_names  # SME trade-to-trade excluded
    assert "NSE:NIFTY50-INDEX" not in symbol_names # Standalone index excluded


def test_parse_single_row_exact_column_mapping():
    """Verify exact column index mapping according to VERIFICATION_REPORT.md Section 1."""
    # 0: token, 1: name, 2: inst_type, 3: lot_size, 4: tick_size, 5: isin, ..., 9: symbol, 13: ticker
    row = [
        "10100000002885",
        "RELIANCE INDUSTRIES LTD",
        "0",
        "1",
        "0.1",
        "INE002A01018",
        "0915-1530|1815-1915:",
        "2026-10-05",
        "",
        "NSE:RELIANCE-EQ",
        "10",
        "10",
        "2885",
        "RELIANCE",
        "2885",
        "-1.0",
        "XX",
        "10100000002885",
        "None",
    ]

    entity = SymbolMasterParser.parse_single_row(row)
    assert entity is not None
    assert entity.symbol == "NSE:RELIANCE-EQ"
    assert entity.name == "RELIANCE INDUSTRIES LTD"
    assert entity.isin == "INE002A01018"
    assert entity.lot_size == 1
    assert entity.tick_size == 0.1
    assert entity.series == "EQ"
    assert entity.exchange == "NSE"
    assert entity.segment == "EQUITY"
    assert entity.tier == 4
    assert entity.category == "OTHERS"


def test_parser_with_classification_mapping():
    """Verify tier and category assignment when classification mapping is supplied."""
    row = [
        "10100000002885",
        "RELIANCE INDUSTRIES LTD",
        "0",
        "1",
        "0.1",
        "INE002A01018",
        "0915-1530|1815-1915:",
        "2026-10-05",
        "",
        "NSE:RELIANCE-EQ",
        "10",
        "10",
        "2885",
        "RELIANCE",
    ]

    classification = {
        "RELIANCE": ("NIFTY50", 1, 1),
    }

    entity = SymbolMasterParser.parse_single_row(row, classification=classification)
    assert entity is not None
    assert entity.category == "NIFTY50"
    assert entity.tier == 1
    assert entity.priority_rank == 1


def test_parser_rejects_non_equity_instrument_types():
    """Verify rejection of rows where instrument_type != 0."""
    row_future = [
        "10100000009999",
        "NIFTY FUT",
        "2",  # Derivative / Futures
        "50",
        "0.05",
        "None",
        "0915-1530:",
        "2026-10-05",
        "",
        "NSE:NIFTY-FUT",
    ]
    assert SymbolMasterParser.parse_single_row(row_future) is None

    row_index = [
        "10100000008888",
        "NIFTY 50",
        "1",  # Index
        "1",
        "0.05",
        "None",
        "0915-1530:",
        "2026-10-05",
        "",
        "NSE:NIFTY50-INDEX",
    ]
    assert SymbolMasterParser.parse_single_row(row_index) is None
