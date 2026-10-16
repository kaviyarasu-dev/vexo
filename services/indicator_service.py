import pandas as pd
from typing import List
from core.interfaces import IIndicator

class IndicatorService:
    """Chains multiple indicators and computes them over a dataframe in one pass."""
    
    def __init__(self, indicators: List[IIndicator]):
        self.indicators = indicators
        
    def compute_all(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
            
        result = df.copy()
        for indicator in self.indicators:
            # Check required columns
            missing_cols = [col for col in indicator.required_columns() if col not in result.columns]
            if missing_cols:
                raise ValueError(f"Indicator {indicator.name()} requires columns {missing_cols} which are missing from dataframe.")
                
            result = indicator.compute(result)
            
        return result
