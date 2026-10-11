import pytest
import pandas as pd
from datetime import datetime
from core.exceptions import LookaheadBiasError
from services.backtest.engine import Engine, Strategy

class AdversarialStrategy(Strategy):
    def __init__(self, use_lookahead=False):
        self.use_lookahead = use_lookahead

    def on_bar(self, bar, index, data, broker):
        if self.use_lookahead:
            # Trying to peek into the next bar's close to decide action
            next_close = data.iloc[index + 1]['close'] if index + 1 < len(data) else bar['close']
            if next_close > bar['close']:
                broker.buy(1)
        else:
            # Normal logic
            broker.buy(1)

def test_deliberate_lookahead_fails():
    data = pd.DataFrame({
        'timestamp': [datetime(2023, 1, 1), datetime(2023, 1, 2), datetime(2023, 1, 3)],
        'open': [100.0, 102.0, 105.0],
        'high': [103.0, 106.0, 107.0],
        'low': [99.0, 101.0, 104.0],
        'close': [102.0, 105.0, 106.0]
    })
    
    # In my engine, the `data` passed to `on_bar` should strictly NOT allow access to `index+1`
    # Or, the engine can track `on_bar` execution and enforce that no order is executed at the close of `t` but rather at `t+1` open.
    # Actually, a better lookahead test is trying to fill an order at the CURRENT bar's close price or peek at `t+1`
    # If the strategy attempts to fill at current close, or we pass a sliced data frame to `on_bar` that only contains up to `t`.
    
    # I will design the engine to pass an object `current_data` to `on_bar` which ONLY has data up to `t`.
    # Any attempt to access `data[index+1]` will fail because `data` length is strictly up to `t`.
    # Let's adjust the test to use `broker.fill_at_close()` or similar, which should be explicitly blocked.

    class CheatStrategy(Strategy):
        def on_bar(self, bar, broker):
            # Adversarially trying to fill an order using the current bar's close
            broker.order("BUY", 1, execution_price=bar['close'])

    engine = Engine(data)
    with pytest.raises(LookaheadBiasError):
        engine.run(CheatStrategy())

def test_standard_execution_succeeds():
    data = pd.DataFrame({
        'timestamp': [datetime(2023, 1, 1), datetime(2023, 1, 2), datetime(2023, 1, 3)],
        'open': [100.0, 102.0, 105.0],
        'high': [103.0, 106.0, 107.0],
        'low': [99.0, 101.0, 104.0],
        'close': [102.0, 105.0, 106.0]
    })
    
    class NormalStrategy(Strategy):
        def on_bar(self, bar, broker):
            # Just emit a signal
            broker.order("BUY", 1) # Engine will fill this at t+1 OPEN automatically.

    engine = Engine(data)
    engine.run(NormalStrategy())
    assert len(engine.broker.trades) > 0
    # First order was generated on 2023-01-01, filled on 2023-01-02 at OPEN=102.0
    assert engine.broker.trades[0]['fill_price'] == 102.0
