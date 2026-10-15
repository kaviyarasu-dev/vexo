"""
Unit tests for Strategy Net Greeks Aggregator & Pre-Expiration Payoff Simulator.
Tests multi-leg options Greek aggregation, lot-size INR scaling, Bull Call Spreads,
Iron Condors, Straddles, breakevens, and IV shocks.
"""

import pytest
from api.models.options_models import (
    OptionLeg,
    StrategyGreeksRequest,
    StrategyGreeksResponse,
    PayoffSimulationRequest,
    PayoffSimulationResponse,
)
from services.options.strategy_greeks_service import StrategyGreeksAggregator
from services.options.payoff_simulator import PreExpiryPayoffSimulator


def test_single_long_call_greeks():
    """Validates single long call Greek calculations and INR scaling."""
    aggregator = StrategyGreeksAggregator()
    req = StrategyGreeksRequest(
        symbol="NIFTY",
        spot=25000.0,
        t_days=4.0,
        r=0.065,
        legs=[
            OptionLeg(strike=25000.0, option_type="CE", position="LONG", premium=120.0, quantity=1, iv=0.14)
        ]
    )

    res = aggregator.calculate_greeks(req)
    assert isinstance(res, StrategyGreeksResponse)
    assert res.symbol == "NIFTY"
    assert res.lot_size == 25

    # Long ATM Call has Delta around 0.50
    assert 0.45 < res.net_delta < 0.58
    assert res.net_gamma > 0.0
    assert res.net_theta < 0.0  # Decays with time
    assert res.net_vega > 0.0   # Benefits from IV expansion

    # INR conversions
    assert res.delta_inr == round(res.net_delta * 25, 2)
    assert res.theta_inr == round(res.net_theta * 25, 2)
    assert res.vega_inr == round(res.net_vega * 25, 2)
    assert res.net_premium == -120.0
    assert res.total_cost_inr == -3000.0


def test_bull_call_spread_net_greeks():
    """Validates 2-leg Bull Call Spread Net Greeks and debit cost."""
    aggregator = StrategyGreeksAggregator()
    req = StrategyGreeksRequest(
        symbol="NIFTY",
        spot=25050.0,
        t_days=4.0,
        r=0.065,
        legs=[
            OptionLeg(strike=25000.0, option_type="CE", position="LONG", premium=140.0, quantity=1, iv=0.14),
            OptionLeg(strike=25200.0, option_type="CE", position="SHORT", premium=55.0, quantity=1, iv=0.135)
        ]
    )

    res = aggregator.calculate_greeks(req)
    # Net Delta must be positive but smaller than naked call
    assert 0.15 < res.net_delta < 0.40
    # Net premium paid is 140 - 55 = 85 debit (-85 points)
    assert res.net_premium == -85.0
    # Total cost = -85 * 25 = -2125 INR
    assert res.total_cost_inr == -2125.0
    assert res.delta_inr > 0.0


def test_iron_condor_net_credit_and_theta():
    """Validates 4-leg Iron Condor market neutrality and positive time decay."""
    aggregator = StrategyGreeksAggregator()
    req = StrategyGreeksRequest(
        symbol="BANKNIFTY",
        spot=51200.0,
        t_days=4.0,
        r=0.065,
        legs=[
            OptionLeg(strike=50800.0, option_type="PE", position="SHORT", premium=110.0, quantity=1, iv=0.16),
            OptionLeg(strike=50400.0, option_type="PE", position="LONG", premium=40.0, quantity=1, iv=0.17),
            OptionLeg(strike=51600.0, option_type="CE", position="SHORT", premium=105.0, quantity=1, iv=0.15),
            OptionLeg(strike=52000.0, option_type="CE", position="LONG", premium=35.0, quantity=1, iv=0.155)
        ]
    )

    res = aggregator.calculate_greeks(req)
    assert res.lot_size == 15
    # Iron Condor is delta-neutral near spot
    assert abs(res.net_delta) < 0.20
    # Theta is positive (income from decay)
    assert res.net_theta > 0.0
    assert res.theta_inr > 0.0
    # Net premium is credit: (110 - 40) + (105 - 35) = 70 + 70 = +140 points
    assert res.net_premium == 140.0
    assert res.total_cost_inr == 140.0 * 15  # +2100 INR credit


def test_payoff_simulator_bull_call_spread():
    """Verifies payoff curve math, breakevens, and max profit/loss for Bull Call Spread."""
    simulator = PreExpiryPayoffSimulator()
    req = PayoffSimulationRequest(
        symbol="NIFTY",
        spot=25000.0,
        t_days_remaining=4.0,
        target_days=2.0,
        iv_shock_pct=0.0,
        r=0.065,
        legs=[
            OptionLeg(strike=25000.0, option_type="CE", position="LONG", premium=100.0, quantity=1, iv=0.14),
            OptionLeg(strike=25200.0, option_type="CE", position="SHORT", premium=30.0, quantity=1, iv=0.135)
        ]
    )

    res = simulator.simulate_payoff(req)
    assert isinstance(res, PayoffSimulationResponse)
    assert res.lot_size == 25
    assert len(res.expiration_curve) == 45
    assert len(res.target_date_curve) == 45

    # Debit paid: 100 - 30 = 70 points * 25 = 1750 INR
    assert res.net_debit_credit_inr == -1750.0

    # Max Loss = -1750 INR
    assert abs(res.max_loss - (-1750.0)) < 5.0
    # Max Profit = (200 spread width - 70 debit) * 25 = 130 * 25 = 3250 INR
    assert abs(res.max_profit - 3250.0) < 5.0

    # Breakeven strike: 25000 + 70 = 25070
    assert len(res.breakevens) == 1
    assert abs(res.breakevens[0] - 25070.0) < 5.0

    # Risk-Reward: 3250 / 1750 = 1.86
    assert res.risk_reward_ratio is not None
    assert 1.7 < res.risk_reward_ratio < 2.0


def test_payoff_simulator_iv_shock_behavior():
    """Verifies that positive IV shock expands theoretical value of long straddle."""
    simulator = PreExpiryPayoffSimulator()
    base_req = PayoffSimulationRequest(
        symbol="NIFTY",
        spot=25000.0,
        t_days_remaining=5.0,
        target_days=3.0,
        iv_shock_pct=0.0,
        r=0.065,
        legs=[
            OptionLeg(strike=25000.0, option_type="CE", position="LONG", premium=140.0, quantity=1, iv=0.15),
            OptionLeg(strike=25000.0, option_type="PE", position="LONG", premium=135.0, quantity=1, iv=0.15)
        ]
    )

    shock_up_req = base_req.model_copy(update={"iv_shock_pct": 25.0})
    shock_down_req = base_req.model_copy(update={"iv_shock_pct": -25.0})

    res_base = simulator.simulate_payoff(base_req)
    res_up = simulator.simulate_payoff(shock_up_req)
    res_down = simulator.simulate_payoff(shock_down_req)

    # ATM theoretical P&L for long straddle must be higher with +25% IV shock than -25% IV shock
    # Find ATM point in target curves
    atm_base_pnl = next(p.pnl for p in res_base.target_date_curve if abs(p.spot - 25000) < 150)
    atm_up_pnl = next(p.pnl for p in res_up.target_date_curve if abs(p.spot - 25000) < 150)
    atm_down_pnl = next(p.pnl for p in res_down.target_date_curve if abs(p.spot - 25000) < 150)

    assert atm_up_pnl > atm_base_pnl > atm_down_pnl
