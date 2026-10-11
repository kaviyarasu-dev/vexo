import pytest
from datetime import datetime, timezone
from services.alert_service import AlertService
from core.interfaces import AlertTrigger

class MockDB:
    def execute_write_batch(self, func): pass
    def get_read_cursor(self):
        class MockCursor:
            def execute(self, q, args):
                self.q = q
                return self
            def fetchone(self):
                # Return channel
                return ("TELEGRAM",)
            def close(self): pass
        return MockCursor()

def test_alert_dispatch_quiet_hours():
    service = AlertService(MockDB())
    
    # Force quiet hours
    def mock_is_quiet_hours(hour_ist=None):
        return True
    service.is_quiet_hours = mock_is_quiet_hours
    
    trigger = AlertTrigger(
        alert_id="123",
        symbol="NSE:RELIANCE-EQ",
        rule_type="PRICE_CROSS",
        trigger_price=2650.0,
        trigger_time=datetime.now(timezone.utc),
        message="Crossed above 2600"
    )
    
    # Should return True as it routes to IN_APP fallback
    success = service.dispatch_alert(trigger)
    assert success is True
