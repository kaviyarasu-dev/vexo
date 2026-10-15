# Plan 02-001: Portfolio Universes Service, Presets & FastAPI Endpoints

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "01-001"
  reads:
    - "services/backtest/portfolio_engine.py"
    - "services/backtest/portfolio_broker.py"
    - "services/backtest/allocation.py"
    - "db/connection.py"
    - "api/routers/backtest.py"
  produces:
    - "services/portfolio_universe_service.py"
    - "api/models/portfolio_backtest_models.py"
    - "tests/integration/test_portfolio_backtest_api.py"
  exposes:
    - "services.portfolio_universe_service.PortfolioUniverseService"
    - "api.models.portfolio_backtest_models.PortfolioBacktestRequest"
    - "api.models.portfolio_backtest_models.PortfolioBacktestResponse"
    - "api.routers.backtest.run_portfolio_backtest_endpoint"
    - "api.routers.backtest.get_portfolio_universes_endpoint"
  must_not_modify:
    - "core/interfaces.py"
    - "db/connection.py"
  test_plan:
    - "pytest tests/integration/test_portfolio_backtest_api.py -v"
  definition_of_done:
    - "PortfolioUniverseService provides official NSE constituent lists (NIFTY 50, NIFTY NEXT 50, NIFTY MIDCAP 150) and validates symbol coverage against historical_candles"
    - "Pydantic models strictly validate all portfolio sizing parameters, universe selections, slippage, and date ranges"
    - "POST /api/v1/backtest/portfolio/run endpoint executes multi-asset backtest with zero-lock DuckDB read cursors and returns complete portfolio metrics, equity curve, asset contributions, and trade ledger"
    - "GET /api/v1/backtest/portfolio/universes endpoint returns available presets and constituent metadata"
    - "Integration test suite passes 100% with robust error handling for unknown symbols, invalid date ranges, and zero-signal runs"
  failure_modes_and_recovery:
    - "DuckDB reader lock contention during batch candle fetch -> use get_read_cursor() for concurrent read isolation"
    - "Candidate stock has insufficient historical bars in requested window -> filter or log warning without aborting entire basket"
  handoff:
    - "Exposes live REST API endpoints and data models for Plan 03-001 (Studio UI & Analytics)"
```

---

## 1. Goal & Scope / User Jobs Served
Expose the multi-asset quantitative simulation engine over a high-throughput, type-safe FastAPI REST API. Provide traders with instant access to curated NSE index universes (NIFTY 50, NIFTY NEXT 50, NIFTY MIDCAP 150) and custom multi-stock baskets, validating parameter inputs, fetching multi-symbol candle data concurrently via DuckDB read cursors, and returning institutional-grade performance analytics.

---

## 2. Architecture & Design

### 2.1 Component Structure
1. **`services/portfolio_universe_service.py`**:
   - Manages predefined index universes:
     - `NIFTY_50`: Top 50 bluechip equities (RELIANCE, HDFCBANK, ICICIBANK, INFOSYS, TCS, etc.).
     - `NIFTY_NEXT_50`: Large-cap emerging bluechips.
     - `NIFTY_MIDCAP_150`: High-beta midcap universe.
   - Provides `validate_universe(symbols, db)` querying `historical_candles` to check data availability dates and candle counts without locking the writer process.
2. **`api/models/portfolio_backtest_models.py`**:
   - Strict Pydantic models for validation and serialization.
3. **`api/routers/backtest.py`**:
   - Mounts `POST /api/v1/backtest/portfolio/run` and `GET /api/v1/backtest/portfolio/universes`.

---

## 3. Data Flow & Concurrency
```
Client Request (POST /api/v1/backtest/portfolio/run)
       │
       ▼
[PortfolioBacktestRequest Validation]
       │
       ▼
[PortfolioUniverseService] ──► Resolve Universe (e.g. NIFTY_50)
       │
       ▼
[DuckDB get_read_cursor()] ──► Fetch Historical OHLCV for all N symbols
       │
       ▼
[PortfolioEngine.run()] ──► Bar-by-bar chronological simulation
       │
       ▼
[PortfolioMetrics & AssetContributions] ──► JSON Serialization
       │
       ▼
Client Response (200 OK)
```

---

## 4. Domain Contracts & API Specifications

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class PortfolioBacktestRequest(BaseModel):
    strategy: str = Field(..., description="Strategy identifier, e.g. SMA_CROSS, RSI_REVERSION")
    universe_type: str = Field(default="PREDEFINED", description="PREDEFINED or CUSTOM")
    universe_name: Optional[str] = Field(default="NIFTY_50", description="NIFTY_50, NIFTY_NEXT_50, NIFTY_MIDCAP_150")
    symbols: Optional[List[str]] = Field(default=None, description="Custom symbols list if universe_type is CUSTOM")
    timeframe: str = Field(default="1D", description="Bar timeframe: 1D, 1h, 15m, 5m")
    start_date: str = Field(default="2020-01-01")
    end_date: str = Field(default="2023-12-31")
    initial_capital: float = Field(default=1000000.0, ge=10000.0)
    max_open_positions: int = Field(default=10, ge=1, le=50)
    sizing_model: str = Field(default="EQUAL_WEIGHT", description="EQUAL_WEIGHT, INVERSE_ATR, FIXED_AMOUNT")
    sizing_val: float = Field(default=10.0, description="% weight or fixed rupee amount per slot")
    ranking_metric: str = Field(default="AUTO", description="AUTO, RSI_OVERSOLD, ROC_MOMENTUM, VOLUME_SURGE")
    slippage_bps: float = Field(default=5.0, ge=0.0)
    stop_loss_pct: Optional[float] = Field(default=None, ge=0.0)
    take_profit_pct: Optional[float] = Field(default=None, ge=0.0)
    parameters: Dict[str, Any] = Field(default_factory=dict)

class DailyEquityPoint(BaseModel):
    date: str
    portfolio_value: float
    cash: float
    invested: float
    benchmark_value: float
    drawdown_pct: float

class AssetContribution(BaseModel):
    symbol: str
    trade_count: int
    win_rate: float
    net_pnl: float
    alpha_contribution_pct: float

class PortfolioMetrics(BaseModel):
    initial_capital: float
    final_equity: float
    net_profit: float
    return_pct: float
    cagr: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_statutory_costs: float
    avg_exposure_ratio: float
    benchmark_cagr: float
    benchmark_return_pct: float

class PortfolioBacktestResponse(BaseModel):
    backtest_id: str
    status: str = "COMPLETED"
    strategy: str
    universe_name: str
    symbols_tested: List[str]
    metrics: PortfolioMetrics
    equity_curve: List[DailyEquityPoint]
    asset_contributions: List[AssetContribution]
    monthly_returns: Dict[str, Dict[str, float]]
    trades: List[Dict[str, Any]]
```

---

## 5. Implementation Steps
1. Create `services/portfolio_universe_service.py` with standard NSE index constituent maps (`NIFTY_50`, `NIFTY_NEXT_50`, `NIFTY_MIDCAP_150`) and database symbol coverage query.
2. Create `api/models/portfolio_backtest_models.py` defining Pydantic schemas.
3. Update `api/routers/backtest.py` mounting `/portfolio/run` and `/portfolio/universes` endpoints.
4. Integrate `PortfolioService` with DuckDB read cursors (`get_read_cursor()`) for batch candle retrieval.
5. Create `tests/integration/test_portfolio_backtest_api.py` covering:
   - Valid NIFTY 50 basket simulation.
   - Custom 3-stock basket simulation.
   - Sizing models: Equal Weight, Inverse ATR, Fixed Amount.
   - Error handling: unknown symbols, invalid dates, insufficient capital.
   - Benchmark alignment verification.

---

## 6. Verification & Acceptance Criteria
- Run `pytest tests/integration/test_portfolio_backtest_api.py -v` (100% pass).
- API response adheres strictly to `PortfolioBacktestResponse` contract.
- Read queries never lock or block the primary DuckDB database writer process.
- 50-stock 4-year backtest completes in $< 2.5$ seconds.
