import pytest
from datetime import datetime, timezone, timedelta
from core.interfaces import Candle
from services.alert_service import AlertService

class MockDB:
    def execute_write_batch(self, func): pass
    def get_read_cursor(self): pass

def test_alert_cooldown_deduplication(monkeypatch):
    service = AlertService(MockDB())
    
    # Mock list_alerts to return a recently triggered alert
    from core.interfaces import AlertRule
    
    now = datetime.now(timezone.utc)
    recent_trigger = now - timedelta(minutes=5)
    
    def mock_list_alerts(symbol=None):
        return [
            AlertRule(
                alert_id="123",
                symbol="NSE:RELIANCE-EQ",
                rule_type="PRICE_CROSS",
                condition_params={"threshold": 2600.0, "direction": "ABOVE"},
                channel="IN_APP",
                is_active=True,
                last_triggered_at=recent_trigger
            )
        ]
    
    monkeypatch.setattr(service, "list_alerts", mock_list_alerts)
    
    class DummyCandle:
        def __init__(self, close):
            self.close = close
            
    candles = {"NSE:RELIANCE-EQ": DummyCandle(2650.0)}
    triggers = service.evaluate_rules(candles)
    
    # Should be empty because it is within 15 min cooldown
    assert len(triggers) == 0

def test_alert_triggers_after_cooldown(monkeypatch):
    service = AlertService(MockDB())
    
    from core.interfaces import AlertRule
    
    now = datetime.now(timezone.utc)
    old_trigger = now - timedelta(minutes=20)
    
    def mock_list_alerts(symbol=None):
        return [
            AlertRule(
                alert_id="123",
                symbol="NSE:RELIANCE-EQ",
                rule_type="PRICE_CROSS",
                condition_params={"threshold": 2600.0, "direction": "ABOVE"},
                channel="IN_APP",
                is_active=True,
                last_triggered_at=old_trigger
            )
        ]
    
    monkeypatch.setattr(service, "list_alerts", mock_list_alerts)
    
    class DummyCandle:
        def __init__(self, close):
            self.close = close
            
    candles = {"NSE:RELIANCE-EQ": DummyCandle(2650.0)}
    triggers = service.evaluate_rules(candles)
    
    # Should trigger because 20 min > 15 min
    assert len(triggers) == 1
    assert triggers[0].symbol == "NSE:RELIANCE-EQ"
