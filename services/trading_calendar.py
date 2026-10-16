import datetime
from typing import Optional
from db.connection import get_db

class TradingCalendar:
    """Market Calendar Evaluator querying DuckDB market_holidays."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db = get_db(db_path)
        
    def is_trading_day(self, dt: datetime.date | str) -> bool:
        """Check if a given date is a trading day.
        
        Weekends are skipped unless they are explicitly marked as a special session.
        Holidays are skipped.
        """
        if isinstance(dt, str):
            dt = datetime.date.fromisoformat(dt)
            
        # Check holiday table
        query = "SELECT is_special_session FROM market_holidays WHERE holiday_date = ?"
        rows = self.db.execute_read(query, [dt])
        
        if rows:
            is_special = rows[0][0]
            if is_special:
                return True
            return False
            
        # If not in table, check if it's a weekend
        if dt.weekday() >= 5: # 5=Sat, 6=Sun
            return False
            
        return True
        
    def get_previous_trading_day(self, from_date: Optional[datetime.date] = None) -> datetime.date:
        """Get the last completed trading day before the given date."""
        if from_date is None:
            # Note: During the trading day, previous is yesterday (or earlier). 
            # The plan says "LAST_SETTLED_TRADING_DAY".
            from_date = datetime.date.today()
            
        current = from_date - datetime.timedelta(days=1)
        while not self.is_trading_day(current):
            current -= datetime.timedelta(days=1)
        return current
