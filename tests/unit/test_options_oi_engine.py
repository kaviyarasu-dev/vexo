"""
Unit tests for Open Interest (ΔOI) Calculation Engine and F&O Universe Registry.
Verifies strike-by-strike OI aggregation, Put/Call Ratios, market sentiment,
support/resistance walls, and max pain calculation.
"""

import pytest
from services.options.oi_engine import OpenInterestEngine, FOUniverseRegistry
from api.models.options_models import OpenInterestAnalysisResponse, FOUnderlyingListResponse


def test_fo_universe_registry_lot_sizes():
    """Validates standardized lot size lookup for major indices and equities."""
    assert FOUniverseRegistry.get_lot_size("NIFTY") == 25
    assert FOUniverseRegistry.get_lot_size("NSE:NIFTY-INDEX") == 25
    assert FOUniverseRegistry.get_lot_size("BANKNIFTY") == 15
    assert FOUniverseRegistry.get_lot_size("NSE:BANKNIFTY-INDEX") == 15
    assert FOUniverseRegistry.get_lot_size("FINNIFTY") == 25
    assert FOUniverseRegistry.get_lot_size("MIDCPNIFTY") == 50

    # Key equities
    assert FOUniverseRegistry.get_lot_size("RELIANCE") == 250
    assert FOUniverseRegistry.get_lot_size("NSE:RELIANCE-EQ") == 250
    assert FOUniverseRegistry.get_lot_size("SBIN") == 750
    assert FOUniverseRegistry.get_lot_size("TCS") == 175
    assert FOUniverseRegistry.get_lot_size("INFY") == 400
    assert FOUniverseRegistry.get_lot_size("TATAMOTORS") == 1425


def test_fo_universe_registry_strike_steps():
    """Validates strike step assignment across index types and equity price bands."""
    assert FOUniverseRegistry.get_strike_step("NIFTY", 25000.0) == 50.0
    assert FOUniverseRegistry.get_strike_step("BANKNIFTY", 51000.0) == 100.0
    assert FOUniverseRegistry.get_strike_step("MIDCPNIFTY", 13000.0) == 25.0

    # Equity steps based on price brackets
    assert FOUniverseRegistry.get_strike_step("RELIANCE", 2800.0) == 50.0
    assert FOUniverseRegistry.get_strike_step("SBIN", 820.0) == 10.0
    assert FOUniverseRegistry.get_strike_step("TATASTEEL", 160.0) == 2.5


def test_fo_universe_registry_catalog():
    """Verifies that the catalog lists all indices and 180+ equities."""
    catalog = FOUniverseRegistry.get_all_underlyings(db=None)
    assert isinstance(catalog, FOUnderlyingListResponse)
    assert len(catalog.indices) == 4
    assert len(catalog.equities) >= 180
    assert catalog.total_count == len(catalog.indices) + len(catalog.equities)

    # Validate index details
    idx_symbols = [idx.symbol for idx in catalog.indices]
    assert "NIFTY" in idx_symbols
    assert "BANKNIFTY" in idx_symbols
    assert "FINNIFTY" in idx_symbols
    assert "MIDCPNIFTY" in idx_symbols

    for item in catalog.indices:
        assert item.lot_size > 0
        assert item.spot_price > 0
        assert item.strike_step > 0


def test_oi_engine_real_data_rejection_without_source():
    """Verifies that analyze_open_interest strictly rejects execution when real data is missing."""
    engine = OpenInterestEngine(db=None, fyers_client=None)
    with pytest.raises(ValueError) as exc_info:
        engine.analyze_open_interest(symbol="NIFTY")
    assert "No verified real option chain data available" in str(exc_info.value)


def test_oi_engine_live_fyers_enrichment():
    """Tests end-to-end real Open Interest and sentiment analysis using Fyers market data."""
    class MockFyersClient:
        def fetch_option_chain(self, symbol, strikes=50):
            return {
                "s": "ok",
                "data": {
                    "expiryData": [{"date": "2026-10-22"}],
                    "optionsChain": [
                        {"strike_price": -1, "ltp": 25050.0, "symbol": "NSE:NIFTY50-INDEX"},
                        {"strike_price": 24900, "option_type": "CE", "oi": 20000, "oich": 2000, "volume": 5000, "ltp": 210.0, "iv": 14.0},
                        {"strike_price": 24900, "option_type": "PE", "oi": 50000, "oich": 4000, "volume": 12000, "ltp": 60.0, "iv": 14.5},
                        {"strike_price": 25000, "option_type": "CE", "oi": 45000, "oich": 5000, "volume": 15000, "ltp": 130.0, "iv": 13.8},
                        {"strike_price": 25000, "option_type": "PE", "oi": 35000, "oich": 3000, "volume": 10000, "ltp": 125.0, "iv": 14.2},
                        {"strike_price": 25100, "option_type": "CE", "oi": 60000, "oich": 8000, "volume": 20000, "ltp": 70.0, "iv": 13.5},
                        {"strike_price": 25100, "option_type": "PE", "oi": 15000, "oich": -1000, "volume": 3000, "ltp": 220.0, "iv": 15.0},
                    ]
                }
            }

    mock_fyers = MockFyersClient()
    engine = OpenInterestEngine(db=None, fyers_client=mock_fyers)
    analysis = engine.analyze_open_interest(symbol="NSE:NIFTY50-INDEX")

    assert isinstance(analysis, OpenInterestAnalysisResponse)
    assert analysis.symbol == "NSE:NIFTY50-INDEX"
    assert analysis.spot == 25050.0
    assert len(analysis.strikes_data) == 3

    # Strikes must be sorted strictly ascending
    strikes = [s.strike for s in analysis.strikes_data]
    assert strikes == [24900.0, 25000.0, 25100.0]

    # Verify totals match strike sums
    total_calls = 20000 + 45000 + 60000
    total_puts = 50000 + 35000 + 15000
    assert analysis.total_call_oi == total_calls
    assert analysis.total_put_oi == total_puts

    # Verify PCR calculation
    expected_pcr = round(total_puts / total_calls, 3)
    assert analysis.pcr_oi == expected_pcr

    # Wall checks: Major Resistance at 25100 (60k Call OI), Support at 24900 (50k Put OI)
    assert analysis.major_resistance_strike == 25100.0
    assert analysis.major_support_strike == 24900.0



def test_oi_engine_custom_records_aggregation():
    """Validates math aggregation logic against controlled option records."""
    engine = OpenInterestEngine(db=None, fyers_client=None)

    # Controlled records with known values:
    # 24000: CE OI=10,000, PE OI=40,000 (Put wall)
    # 24500: CE OI=25,000, PE OI=25,000
    # 25000: CE OI=50,000, PE OI=10,000 (Call wall)
    records = [
        {"strike_price": 24000, "option_type": "CE", "oi": 10000, "oi_change": 1000, "volume": 500, "ltp": 550.0, "iv": 14.0},
        {"strike_price": 24000, "option_type": "PE", "oi": 40000, "oi_change": 4000, "volume": 2000, "ltp": 30.0, "iv": 15.0},
        {"strike_price": 24500, "option_type": "CE", "oi": 25000, "oi_change": 2500, "volume": 1200, "ltp": 200.0, "iv": 13.5},
        {"strike_price": 24500, "option_type": "PE", "oi": 25000, "oi_change": 2000, "volume": 1100, "ltp": 120.0, "iv": 14.0},
        {"strike_price": 25000, "option_type": "CE", "oi": 50000, "oi_change": 8000, "volume": 3500, "ltp": 45.0, "iv": 13.0},
        {"strike_price": 25000, "option_type": "PE", "oi": 10000, "oi_change": -500, "volume": 400, "ltp": 450.0, "iv": 16.0},
    ]

    res = engine._compile_analysis_from_records(
        symbol="NIFTY",
        spot=24500.0,
        expiry_date="2026-10-15",
        records=records
    )

    assert res.total_call_oi == 85000
    assert res.total_put_oi == 75000
    assert res.pcr_oi == round(75000 / 85000, 3)

    # Positive changes:
    # calls: 1000 + 2500 + 8000 = 11500
    # puts: 4000 + 2000 + 0 = 6000
    assert res.pcr_oi_change == round(6000 / 11500, 3)

    # Major resistance is 25000 (Call OI=50,000)
    assert res.major_resistance_strike == 25000.0
    # Major support is 24000 (Put OI=40,000)
    assert res.major_support_strike == 24000.0

    # Max Call battleground is 25000 (+8000 ΔOI)
    assert res.active_call_battleground == 25000.0
    # Max Put battleground is 24000 (+4000 ΔOI)
    assert res.active_put_battleground == 24000.0
