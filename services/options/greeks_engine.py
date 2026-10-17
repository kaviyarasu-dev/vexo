import math
from dataclasses import dataclass
from typing import Literal

@dataclass
class GreeksResult:
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float = 0.0

class BlackScholesGreeks:
    def _norm_cdf(self, x: float) -> float:
        return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

    def _norm_pdf(self, x: float) -> float:
        return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

    def calculate(
        self,
        spot: float,
        strike: float,
        t_days: float,
        iv: float,
        r: float,
        option_type: Literal["CE", "PE"],
        dividend_yield: float = 0.0
    ) -> GreeksResult:
        if spot <= 0 or strike <= 0 or t_days <= 0 or iv <= 0:
            # At expiration, zero vol, or invalid price
            if option_type == "CE":
                delta = 1.0 if spot > strike else 0.0
            else:
                delta = -1.0 if spot < strike else 0.0
            return GreeksResult(delta=delta, gamma=0.0, theta=0.0, vega=0.0)

        T = t_days / 250.0  # Annualized trading days convention matching daily Theta decay
        q = dividend_yield
        
        d1 = (math.log(spot / strike) + (r - q + (iv * iv) / 2.0) * T) / (iv * math.sqrt(T))
        d2 = d1 - iv * math.sqrt(T)

        cdf_d1 = self._norm_cdf(d1)
        pdf_d1 = self._norm_pdf(d1)
        exp_neg_qT = math.exp(-q * T)
        exp_neg_rT = math.exp(-r * T)

        gamma = (exp_neg_qT * pdf_d1) / (spot * iv * math.sqrt(T))
        vega = spot * exp_neg_qT * math.sqrt(T) * pdf_d1 / 100.0  # Vega per 1% change

        if option_type == "CE":
            delta = exp_neg_qT * cdf_d1
            cdf_d2 = self._norm_cdf(d2)
            theta = (
                -(spot * exp_neg_qT * pdf_d1 * iv) / (2.0 * math.sqrt(T))
                - r * strike * exp_neg_rT * cdf_d2
                + q * spot * exp_neg_qT * cdf_d1
            )
        else:
            delta = exp_neg_qT * (cdf_d1 - 1.0)
            cdf_minus_d2 = self._norm_cdf(-d2)
            cdf_minus_d1 = self._norm_cdf(-d1)
            theta = (
                -(spot * exp_neg_qT * pdf_d1 * iv) / (2.0 * math.sqrt(T))
                + r * strike * exp_neg_rT * cdf_minus_d2
                - q * spot * exp_neg_qT * cdf_minus_d1
            )

        # Theta per trading day
        theta = theta / 250.0

        return GreeksResult(delta=delta, gamma=gamma, theta=theta, vega=vega)
