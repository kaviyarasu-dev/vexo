import pytest
from core.interfaces import ScreenerFilter

def test_screener_filter_dataclass():
    f = ScreenerFilter(universe="NIFTY50")
    assert f.universe == "NIFTY50"
    assert f.as_of_date is None
