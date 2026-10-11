import pytest
from services.backtest.cost_model import IndianEquityCostModel

def test_indian_cost_model_delivery():
    m = IndianEquityCostModel()
    fees = m.compute_fees(buy_val=100000, sell_val=105000, trade_type="DELIVERY")
    assert fees.stt == 205.0
    assert fees.brokerage == 40.0
    # Add assertions for other components if needed

def test_indian_cost_model_intraday():
    m = IndianEquityCostModel()
    fees = m.compute_fees(buy_val=100000, sell_val=105000, trade_type="INTRADAY")
    assert fees.stt == 26.25 # 0.025% on sell only (105000 * 0.00025)
    assert fees.brokerage == 40.0
    assert fees.stamp_duty == 3.0 # 0.003% on buy only (100000 * 0.00003)
