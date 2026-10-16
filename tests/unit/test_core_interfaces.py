import inspect
import core.interfaces as ci

def test_interfaces_are_abstract():
    """Verify that all canonical interfaces are abstract base classes."""
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
    
    for name in expected_interfaces:
        cls = getattr(ci, name)
        assert inspect.isabstract(cls)
