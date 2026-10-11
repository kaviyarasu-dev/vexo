import core.interfaces as ci
from config.constants import CANONICAL_TIMEFRAMES

def test_canonical_interfaces_exist():
    expected_interfaces = [
        "IAuthService",
        "IMarketDataProvider",
        "ISymbolRepository",
        "ICandleReader",
        "ICandleWriter",
        "ICheckpointRepository",
        "ICorporateActionRepository",
        "IResamplingService",
        "IIndicator",
        "IDataExporter",
        "ICandleService",
        "IScreenerService",
        "IAlertService",
        "IBacktestEngine",
        "IJournalService"
    ]
    
    for interface in expected_interfaces:
        assert hasattr(ci, interface), f"Missing interface: {interface}"
        
def test_canonical_timeframes_exist():
    expected_timeframes = [
        "1m", "3m", "5m", "10m", "15m", "30m", "1h", "2h", "4h", "1D", "1W"
    ]
    
    assert len(CANONICAL_TIMEFRAMES) == 11
    assert set(CANONICAL_TIMEFRAMES) == set(expected_timeframes)
