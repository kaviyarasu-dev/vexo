import pytest
from services.journal_service import JournalService

def test_r_multiple_long():
    service = JournalService(None)
    # entry 2500, exit 2600, sl 2450. Risk = 50. Gain = 100. R = 2.0
    r = service.calculate_r_multiple(2500, 2600, 2450, "LONG")
    assert r == 2.0

def test_r_multiple_long_loss():
    service = JournalService(None)
    # entry 2500, exit 2450, sl 2450. Risk = 50. Gain = -50. R = -1.0
    r = service.calculate_r_multiple(2500, 2450, 2450, "LONG")
    assert r == -1.0

def test_r_multiple_short():
    service = JournalService(None)
    # entry 2500, exit 2400, sl 2550. Risk = 50. Gain = 100. R = 2.0
    r = service.calculate_r_multiple(2500, 2400, 2550, "SHORT")
    assert r == 2.0

def test_r_multiple_validation():
    service = JournalService(None)
    with pytest.raises(ValueError, match="Stop Loss must be below Entry for Long"):
        service.calculate_r_multiple(2500, 2600, 2500, "LONG")
        
    with pytest.raises(ValueError, match="Stop Loss must be above Entry for Short"):
        service.calculate_r_multiple(2500, 2400, 2400, "SHORT")
