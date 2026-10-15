# Plan 02-001: FastAPI Optimization Router, Strategy Ranges & Pydantic Contracts

## 1. Execution Contract
```yaml
execution_contract:
  plan_id: "02-001"
  name: "FastAPI Optimization Router, Strategy Ranges & Pydantic Contracts"
  feature: "strategy-parameter-optimization"
  depends_on:
    - "01-001"
  reads:
    - "services/backtest/optimization_engine.py"
    - "services/backtest_service.py"
    - "api/routers/backtest.py"
  produces:
    - "api/models/optimization_models.py"
    - "services/backtest/optimization_preset_registry.py"
    - "tests/integration/test_parameter_optimization_api.py"
  exposes:
    - "POST /api/v1/backtest/optimize"
    - "GET /api/v1/backtest/optimize/presets"
  must_not_modify:
    - "services/backtest/portfolio_engine.py"
    - "api/models/portfolio_backtest_models.py"
  test_plan:
    integration_tests: "pytest tests/integration/test_parameter_optimization_api.py -v"
    command: "pytest tests/integration/test_parameter_optimization_api.py -v"
  definition_of_done:
    - "POST /api/v1/backtest/optimize handles grid evaluation, 3x3 stability scoring, and walk-forward validation"
    - "GET /api/v1/backtest/optimize/presets returns curated parameter ranges for SMA_CROSS, RSI_REVERSION, BOLLINGER_BANDS, SUPERTREND, and MACD"
    - "Validation rejects grids exceeding 400 cells with HTTP 400 and helpful error message"
    - "Full test suite passes with zero regressions"
  failure_modes_and_recovery:
    - "Invalid date range or symbol not found: Returns HTTP 400 or HTTP 404 with standard ApiResponse envelope"
    - "DuckDB read lock error: Uses db.get_read_cursor() to avoid blocking single-writer"
  handoff:
    next_plan: "03-001"
    requires: "tests/integration/test_parameter_optimization_api.py passing"
```

---

## 2. Goal & Scope / User Jobs Served
This phase exposes the optimization engine and stability mathematics via clean REST API endpoints:
- Exposes `POST /api/v1/backtest/optimize` executing the end-to-end grid search, plateau stability index, and walk-forward validation.
- Exposes `GET /api/v1/backtest/optimize/presets` supplying standard quant search ranges for all 5 pre-built strategies.
- Enforces strict Pydantic models with input sanitization and descriptive error responses.

---

## 3. Architecture & SOLID Principles Application
- **Controller-Service-Repository Pattern**:
  - `api/routers/backtest.py` delegates optimization workloads to `OptimizationEngine` and `BacktestService`.
  - Database access relies on `DuckDBConnectionManager.get_read_cursor()` to prevent write lock contention.
- **Single Responsibility Principle (SRP)**:
  - `api/models/optimization_models.py`: Centralizes all serialization and validation schemas.
  - `services/backtest/optimization_preset_registry.py`: Centralizes default strategy search parameter ranges.

---

## 4. Domain Contracts & API Endpoints

### 4.1 Pydantic Request & Response Models (`api/models/optimization_models.py`)
```python
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional

class ParamRangeSpec(BaseModel):
    name: str
    min_val: float
    max_val: float
    step: float

class OptimizationRequest(BaseModel):
    strategy: str
    symbol: str
    timeframe: str = "1D"
    start_date: str = "2020-01-01"
    end_date: str = "2023-12-31"
    initial_capital: float = 1000000.0
    slippage_bps: float = 5.0
    trade_type: str = "DELIVERY"
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    param1: ParamRangeSpec
    param2: ParamRangeSpec
    walk_forward_split_pct: float = Field(default=70.0, ge=50.0, le=90.0)
    target_metric: str = "sharpe_ratio" # 'sharpe_ratio' | 'net_pnl' | 'max_drawdown' | 'win_rate'

class HeatmapCellDto(BaseModel):
    param1_val: float
    param2_val: float
    sharpe_ratio: float
    net_pnl: float
    net_pnl_pct: float
    max_drawdown_pct: float
    win_rate: float
    total_trades: int
    profit_factor: float

class StabilityDto(BaseModel):
    optimal_param1: float
    optimal_param2: float
    optimal_metric_val: float
    stability_score: float
    classification: str # 'ROBUST_PLATEAU' | 'MODERATE_SENSITIVITY' | 'FRAGILE_CLIFF'
    neighbor_avg_val: float
    cliff_drop_pct: float

class WalkForwardDto(BaseModel):
    in_sample_net_pnl: float
    in_sample_sharpe: float
    out_of_sample_net_pnl: float
    out_of_sample_sharpe: float
    walk_forward_efficiency: float
    split_date: str
    is_split_pct: float

class OptimizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    success: bool = True
    strategy: str
    symbol: str
    param1_name: str
    param2_name: str
    param1_ticks: List[float]
    param2_ticks: List[float]
    total_combinations: int
    execution_time_ms: float
    best_params: Dict[str, Any]
    stability: StabilityDto
    walk_forward: WalkForwardDto
    matrix: List[HeatmapCellDto]

class StrategyOptimizationPreset(BaseModel):
    strategy: str
    label: str
    param1: ParamRangeSpec
    param2: ParamRangeSpec

class PresetsResponse(BaseModel):
    success: bool = True
    presets: List[StrategyOptimizationPreset]
```

### 4.2 Endpoint 1: `POST /api/v1/backtest/optimize`
Runs the grid search, calculates stability, runs walk-forward validation, and returns the matrix.

### 4.3 Endpoint 2: `GET /api/v1/backtest/optimize/presets`
Returns curated parameter ranges:
- `SMA_CROSS`: `short_window` (5 to 30, step 5) $\times$ `long_window` (30 to 100, step 10).
- `RSI_REVERSION`: `rsi_period` (7 to 21, step 2) $\times$ `oversold` (20 to 40, step 5).
- `BOLLINGER_BANDS`: `period` (10 to 30, step 5) $\times$ `std_dev` (1.5 to 3.0, step 0.25).
- `SUPERTREND`: `period` (7 to 14, step 1) $\times$ `multiplier` (1.5 to 4.0, step 0.5).
- `MACD`: `fast_period` (8 to 16, step 2) $\times$ `slow_period` (20 to 34, step 2).

---

## 5. Implementation Steps
1. Create `api/models/optimization_models.py` with Pydantic schemas.
2. Create `services/backtest/optimization_preset_registry.py` defining standard ranges for all 5 strategies.
3. Update `api/routers/backtest.py`:
   - Add `POST /api/v1/backtest/optimize`.
   - Add `GET /api/v1/backtest/optimize/presets`.
4. Create integration tests `tests/integration/test_parameter_optimization_api.py`:
   - Test presets endpoint returns all 5 pre-built strategy configurations.
   - Test optimize endpoint with valid payload returns 200 and schema.
   - Test grid size limit (>400 combinations) returns 400 error.
   - Test walk-forward split date and efficiency calculation.

---

## 6. Verification & Acceptance Criteria
- `pytest tests/integration/test_parameter_optimization_api.py -v` passes 100%.
- API returns execution time and full matrix with zero NaN values.
- Seamless compatibility with existing DuckDB connection manager.
