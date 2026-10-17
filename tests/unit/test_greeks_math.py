import pytest
from services.options.greeks_engine import BlackScholesGreeks

def test_atm_call_delta():
    g = BlackScholesGreeks()
    res = g.calculate(spot=2500, strike=2500, t_days=30, iv=0.20, r=0.065, option_type="CE")
    assert 0.48 <= res.delta <= 0.58
