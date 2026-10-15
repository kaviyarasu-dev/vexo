"""
Strategy Net Greeks Aggregation Service.
Computes aggregated Net Delta, Gamma, Theta, and Vega across multi-leg option strategies,
and calculates lot-size adjusted Indian Rupee (₹) risk exposures.
"""

import math
import logging
from typing import Optional, List

from api.models.options_models import (
    OptionLeg,
    StrategyGreeksRequest,
    StrategyGreeksResponse
)
from services.options.greeks_engine import BlackScholesGreeks
from services.options.oi_engine import FOUniverseRegistry

logger = logging.getLogger(__name__)


class StrategyGreeksAggregator:
    """
    Aggregates Greeks for arbitrary combinations of calls, puts, long, and short legs,
    scaling sensitivity by standardized NSE contract lot sizes.
    """

    def __init__(self):
        self.greeks_engine = BlackScholesGreeks()

    def calculate_greeks(self, request: StrategyGreeksRequest) -> StrategyGreeksResponse:
        """
        Calculates Net Greeks and INR exposures for a multi-leg strategy request.
        """
        lot_size = FOUniverseRegistry.get_lot_size(request.symbol)
        
        net_delta = 0.0
        net_gamma = 0.0
        net_theta = 0.0
        net_vega = 0.0
        net_premium = 0.0  # Positive for credit, negative for debit

        for leg in request.legs:
            is_long = (leg.position.upper() == "LONG")
            w = leg.quantity if is_long else -leg.quantity
            opt_type = leg.option_type.upper()
            if opt_type not in ("CE", "PE"):
                opt_type = "CE"

            # Normalize IV
            if leg.iv is None or leg.iv <= 0:
                moneyness = (leg.strike - request.spot) / max(1.0, request.spot)
                iv = max(0.08, 0.145 + 0.08 * (moneyness ** 2))
            elif leg.iv > 1.0:
                iv = leg.iv / 100.0
            else:
                iv = leg.iv

            # Calculate individual leg Greeks
            greeks = self.greeks_engine.calculate(
                spot=request.spot,
                strike=leg.strike,
                t_days=request.t_days,
                iv=iv,
                r=request.r,
                option_type=opt_type  # type: ignore
            )

            net_delta += w * greeks.delta
            net_gamma += w * greeks.gamma
            net_theta += w * greeks.theta
            net_vega += w * greeks.vega

            # Cashflow premium in points
            if is_long:
                net_premium -= leg.premium * leg.quantity
            else:
                net_premium += leg.premium * leg.quantity

        rounded_delta = round(net_delta, 4)
        rounded_gamma = round(net_gamma, 6)
        rounded_theta = round(net_theta, 2)
        rounded_vega = round(net_vega, 3)

        # Rupee risk exposures:
        # Delta INR = Net Delta * Lot Size (Rupees per 1 point spot move)
        delta_inr = round(rounded_delta * lot_size, 2)
        # Theta INR = Net Theta * Lot Size (Rupees per calendar day decay)
        theta_inr = round(rounded_theta * lot_size, 2)
        # Vega INR = Net Vega * Lot Size (Rupees per 1.0% absolute IV shift, since vega is already per 1%)
        vega_inr = round(rounded_vega * lot_size, 2)

        total_cost_inr = round(net_premium * lot_size, 2)

        return StrategyGreeksResponse(
            symbol=request.symbol,
            lot_size=lot_size,
            net_delta=rounded_delta,
            net_gamma=rounded_gamma,
            net_theta=rounded_theta,
            net_vega=rounded_vega,
            delta_inr=delta_inr,
            theta_inr=theta_inr,
            vega_inr=vega_inr,
            net_premium=round(net_premium, 2),
            total_cost_inr=total_cost_inr
        )

