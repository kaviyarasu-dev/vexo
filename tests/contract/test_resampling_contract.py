import pytest
import pandas as pd
from datetime import datetime
import pytz

from services.resampling_service import ResamplingService
from core.interfaces import IResamplingService
from db.connection import get_db

def test_resampling_service_implements_contract():
    db = get_db(":memory:", reset=True)
    service = ResamplingService(db)
    
    assert isinstance(service, IResamplingService)
    assert hasattr(service, "resample")
    
    # Check method signature
    import inspect
    sig = inspect.signature(service.resample)
    
    assert "symbol" in sig.parameters
    assert "target_timeframe" in sig.parameters
    assert "start" in sig.parameters
    assert "end" in sig.parameters
    assert "adjusted" in sig.parameters
    
    db.close()
