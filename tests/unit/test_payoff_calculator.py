import pytest
from services.options.payoff_calculator import PayoffCalculator

def test_max_pain():
    p = PayoffCalculator()
    res = p.max_pain(strikes=[2400, 2500, 2600], call_oi=[1000, 5000, 2000], put_oi=[3000, 2000, 500])
    assert res == 2500
