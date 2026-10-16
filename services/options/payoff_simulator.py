"""
Pre-Expiration Black-Scholes Payoff Simulation Engine.
Computes dual payoff curves: Expiration Hockey-Stick P&L (T=0) and
Theoretical Target Date Black-Scholes P&L (T+x) with dynamic IV shock adjustments.
"""

import math
import logging
from typing import List, Optional

from api.models.options_models import (
    OptionLeg,
    PayoffPoint,
    PayoffSimulationRequest,
    PayoffSimulationResponse,
)
from services.options.oi_engine import FOUniverseRegistry

logger = logging.getLogger(__name__)


class PreExpiryPayoffSimulator:
    """
    Simulates multi-leg option strategies across spot price spectrum,
    generating both expiration payoff and theoretical pre-expiration curves.
    """

    @staticmethod
    def _norm_cdf(x: float) -> float:
        return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

    def _bsm_price(
        self,
        spot: float,
        strike: float,
        t_years: float,
        iv: float,
        r: float,
        option_type: str
    ) -> float:
        """Computes Black-Scholes option price."""
        if spot <= 0 or strike <= 0:
            return 0.0

        if t_years <= 0.0001:
            if option_type == "CE":
                return max(0.0, spot - strike)
            return max(0.0, strike - spot)

        d1 = (math.log(spot / strike) + (r + (iv * iv) / 2.0) * t_years) / (iv * math.sqrt(t_years))
        d2 = d1 - iv * math.sqrt(t_years)

        cdf_d1 = self._norm_cdf(d1)
        cdf_d2 = self._norm_cdf(d2)

        if option_type == "CE":
            price = spot * cdf_d1 - strike * math.exp(-r * t_years) * cdf_d2
        else:
            cdf_minus_d1 = self._norm_cdf(-d1)
            cdf_minus_d2 = self._norm_cdf(-d2)
            price = strike * math.exp(-r * t_years) * cdf_minus_d2 - spot * cdf_minus_d1

        return max(0.0, price)

    def simulate_payoff(self, request: PayoffSimulationRequest) -> PayoffSimulationResponse:
        """
        Simulates both Expiration and Target Date theoretical curves with IV shock adjustments.
        """
        lot_size = FOUniverseRegistry.get_lot_size(request.symbol)
        spot = request.spot

        if not request.legs:
            return PayoffSimulationResponse(
                symbol=request.symbol,
                lot_size=lot_size,
                spot=spot,
                max_profit=0.0,
                max_loss=0.0,
                risk_reward_ratio=None,
                breakevens=[],
                net_debit_credit_inr=0.0,
                expiration_curve=[],
                target_date_curve=[]
            )

        # Clamp target evaluation days between 0.001 and total remaining days
        t_target_days = max(0.001, min(request.target_days, request.t_days_remaining))
        t_target_years = t_target_days / 365.0

        # Calculate net debit / credit in Indian Rupees
        net_debit_credit = 0.0
        for leg in request.legs:
            is_long = (leg.position.upper() == "LONG")
            if is_long:
                net_debit_credit -= leg.premium * leg.quantity
            else:
                net_debit_credit += leg.premium * leg.quantity
        net_debit_credit_inr = round(net_debit_credit * lot_size, 2)

        # Dynamic spot price grid
        strikes = [leg.strike for leg in request.legs if leg.strike > 0]
        if not strikes:
            strikes = [spot]
        min_strike = min(strikes)
        max_strike = max(strikes)

        low_bound = min(spot * 0.90, min_strike * 0.94)
        high_bound = max(spot * 1.10, max_strike * 1.06)

        num_points = 45
        step = (high_bound - low_bound) / float(num_points - 1)
        spot_grid = [round(low_bound + i * step, 1) for i in range(num_points)]

        # Prepare IVs with IV shock factor
        iv_shock = request.iv_shock_pct / 100.0
        leg_params = []
        for leg in request.legs:
            is_long = (leg.position.upper() == "LONG")
            w = leg.quantity if is_long else -leg.quantity
            opt_type = leg.option_type.upper() if leg.option_type.upper() in ("CE", "PE") else "CE"

            if leg.iv is None or leg.iv <= 0:
                moneyness = (leg.strike - spot) / max(1.0, spot)
                base_iv = max(0.08, 0.145 + 0.08 * (moneyness ** 2))
            elif leg.iv > 1.0:
                base_iv = leg.iv / 100.0
            else:
                base_iv = leg.iv

            adj_iv = max(0.02, base_iv * (1.0 + iv_shock))
            leg_params.append({
                "strike": leg.strike,
                "premium": leg.premium,
                "opt_type": opt_type,
                "weight": w,
                "adj_iv": adj_iv
            })

        expiration_curve: List[PayoffPoint] = []
        target_date_curve: List[PayoffPoint] = []

        for s in spot_grid:
            pnl_exp = 0.0
            pnl_target = 0.0

            for lp in leg_params:
                k = lp["strike"]
                prem = lp["premium"]
                opt_type = lp["opt_type"]
                w = lp["weight"]
                iv = lp["adj_iv"]

                # Expiration intrinsic
                if opt_type == "CE":
                    intrinsic = max(0.0, s - k)
                else:
                    intrinsic = max(0.0, k - s)

                leg_exp_pnl = w * (intrinsic - prem) * lot_size
                pnl_exp += leg_exp_pnl

                # Theoretical Black-Scholes price at target date
                theo_price = self._bsm_price(
                    spot=s,
                    strike=k,
                    t_years=t_target_years,
                    iv=iv,
                    r=request.r,
                    option_type=opt_type
                )
                leg_target_pnl = w * (theo_price - prem) * lot_size
                pnl_target += leg_target_pnl

            expiration_curve.append(PayoffPoint(spot=round(s, 2), pnl=round(pnl_exp, 2)))
            target_date_curve.append(PayoffPoint(spot=round(s, 2), pnl=round(pnl_target, 2)))

        # Compute Max Profit & Max Loss from expiration curve
        max_profit = max(pt.pnl for pt in expiration_curve)
        max_loss = min(pt.pnl for pt in expiration_curve)

        # Risk-to-reward ratio
        risk_reward_ratio = None
        if max_profit > 0 and max_loss < 0:
            risk_reward_ratio = round(max_profit / abs(max_loss), 2)

        # Find zero crossings for breakeven points
        breakevens: List[float] = []
        for i in range(len(expiration_curve) - 1):
            p1 = expiration_curve[i].pnl
            p2 = expiration_curve[i + 1].pnl
            s1 = expiration_curve[i].spot
            s2 = expiration_curve[i + 1].spot

            if p1 == 0:
                breakevens.append(round(s1, 1))
            elif (p1 < 0 < p2) or (p2 < 0 < p1):
                # Linear interpolation for zero crossing
                be = s1 - p1 * (s2 - s1) / (p2 - p1)
                breakevens.append(round(be, 1))

        # Deduplicate breakevens within 2 points
        unique_breakevens: List[float] = []
        for be in breakevens:
            if not any(abs(be - u) < 2.0 for u in unique_breakevens):
                unique_breakevens.append(be)

        return PayoffSimulationResponse(
            symbol=request.symbol,
            lot_size=lot_size,
            spot=spot,
            max_profit=round(max_profit, 2),
            max_loss=round(max_loss, 2),
            risk_reward_ratio=risk_reward_ratio,
            breakevens=sorted(unique_breakevens),
            net_debit_credit_inr=net_debit_credit_inr,
            expiration_curve=expiration_curve,
            target_date_curve=target_date_curve
        )
