from typing import List

class PayoffCalculator:
    def max_pain(self, strikes: List[float], call_oi: List[int], put_oi: List[int]) -> float:
        """
        Calculate Max Pain strike based on OI distribution.
        """
        if not strikes or not call_oi or not put_oi:
            return 0.0
            
        min_payout = float('inf')
        max_pain_strike = strikes[0]
        
        for candidate_strike in strikes:
            total_payout = 0.0
            for i, strike in enumerate(strikes):
                # Call writers pay out if candidate spot > strike
                if candidate_strike > strike:
                    total_payout += call_oi[i] * (candidate_strike - strike)
                # Put writers pay out if candidate spot < strike
                if candidate_strike < strike:
                    total_payout += put_oi[i] * (strike - candidate_strike)
                    
            if total_payout < min_payout:
                min_payout = total_payout
                max_pain_strike = candidate_strike
                
        return max_pain_strike
