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
        option_type: Literal["CE", "PE"]
    ) -> GreeksResult:
        if spot <= 0 or strike <= 0 or t_days <= 0 or iv <= 0:
            # At expiration, zero vol, or invalid price
            if option_type == "CE":
                delta = 1.0 if spot > strike else 0.0
            else:
                delta = -1.0 if spot < strike else 0.0
            return GreeksResult(delta=delta, gamma=0.0, theta=0.0, vega=0.0)

        T = t_days / 365.0  # Annualized time to expiry
        
        d1 = (math.log(spot / strike) + (r + (iv * iv) / 2.0) * T) / (iv * math.sqrt(T))
        d2 = d1 - iv * math.sqrt(T)

        cdf_d1 = self._norm_cdf(d1)
        pdf_d1 = self._norm_pdf(d1)

        gamma = pdf_d1 / (spot * iv * math.sqrt(T))
        vega = spot * math.sqrt(T) * pdf_d1 / 100.0  # Vega per 1% change

        if option_type == "CE":
            delta = cdf_d1
            cdf_d2 = self._norm_cdf(d2)
            theta = -(spot * pdf_d1 * iv) / (2.0 * math.sqrt(T)) - r * strike * math.exp(-r * T) * cdf_d2
        else:
            delta = cdf_d1 - 1.0
            cdf_minus_d2 = self._norm_cdf(-d2)
            theta = -(spot * pdf_d1 * iv) / (2.0 * math.sqrt(T)) + r * strike * math.exp(-r * T) * cdf_minus_d2

        # Theta per day
        theta = theta / 250.0

        return GreeksResult(delta=delta, gamma=gamma, theta=theta, vega=vega)
