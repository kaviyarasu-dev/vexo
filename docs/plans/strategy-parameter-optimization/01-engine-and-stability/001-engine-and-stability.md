# Plan 01-001: Grid Search Engine, Plateau Stability Index (3x3 Neighborhood) & Walk-Forward Splitter

## 1. Execution Contract
```yaml
execution_contract:
  plan_id: "01-001"
  name: "Grid Search Engine, Plateau Stability Index & Walk-Forward Splitter"
  feature: "strategy-parameter-optimization"
  depends_on: []
  reads:
    - "services/backtest/engine.py"
    - "services/backtest/cost_model.py"
    - "services/backtest/metrics.py"
    - "services/backtest_service.py"
    - "core/interfaces.py"
  produces:
    - "services/backtest/optimization_engine.py"
    - "tests/unit/test_parameter_optimization_engine.py"
  exposes:
    - "OptimizationEngine (grid search over 2 parameters with thread pool parallelism)"
    - "StabilityAnalyzer (computes 3x3 Plateau Stability Index, cliff degradation, and robustness classification)"
    - "WalkForwardSplitter (chronological IS/OOS splitter and Walk-Forward Efficiency calculation)"
  must_not_modify:
    - "services/backtest/portfolio_engine.py"
    - "services/backtest/allocation.py"
  test_plan:
    unit_tests: "pytest tests/unit/test_parameter_optimization_engine.py -v"
    command: "pytest tests/unit/test_parameter_optimization_engine.py -v"
  definition_of_done:
    - "OptimizationEngine evaluates 2D parameter ranges in-memory with ThreadPoolExecutor under 3 seconds for 10x10 combinations"
    - "StabilityAnalyzer inspects 8 adjacent neighbor cells and classifies into ROBUST_PLATEAU, MODERATE_SENSITIVITY, or FRAGILE_CLIFF"
    - "WalkForwardSplitter partitions historical data chronologically into In-Sample and Out-of-Sample segments and calculates WFE ratio"
    - "All unit tests pass 100% with zero lookahead bias and accurate Indian equity statutory cost model calculations"
  failure_modes_and_recovery:
    - "Combination count > 400: Raises ValueError with suggestion to increase parameter step size"
    - "Zero trades across grid: Gracefully returns zeroed metrics without ZeroDivisionError"
  handoff:
    next_plan: "02-001"
    requires: "tests/unit/test_parameter_optimization_engine.py passing"
```

---

## 2. Goal & Scope / User Jobs Served
This phase builds the analytical, mathematical, and algorithmic backbone of parameter optimization:
- **Fast In-Memory Grid Search**: Eliminates disk-bound queries by caching the base OHLCV dataset in memory and parallelizing parameter evaluations.
- **Plateau Stability Index ($PSI$)**: Mathematically flags whether an optimal parameter setting is a robust plateau or an isolated, overfit spike.
- **Walk-Forward Validation**: Validates the top strategy parameters on unseen Out-of-Sample data to measure real alpha persistence ($WFE$).

---

## 3. Architecture & SOLID Principles Application
- **Single Responsibility Principle (SRP)**:
  - `OptimizationEngine`: Manages the Cartesian parameter matrix generation and parallel execution loop.
  - `StabilityAnalyzer`: Analyzes matrix topology, 3x3 neighborhoods, and cliff degradation.
  - `WalkForwardSplitter`: Manages chronological date partitioning and out-of-sample performance validation.
- **Dependency Inversion Principle (DIP)**:
  - Leverages existing `Engine`, `Broker`, `Strategy`, and `IndianEquityCostModel` abstractions from `services/backtest/`.
- **Open-Closed Principle (OCP)**:
  - Designed to optimize any strategy registered in `compute_indicators` without modifying the core execution loop.

---

## 4. Domain & Mathematical Specifications

### 4.1 Cartesian Grid Generation
Given Parameter 1 $P_1 \in [a_1, b_1]$ with step $s_1$ and Parameter 2 $P_2 \in [a_2, b_2]$ with step $s_2$:
$$\text{Grid} = \{(p_1, p_2) \mid p_1 \in \text{range}(a_1, b_1, s_1), p_2 \in \text{range}(a_2, b_2, s_2)\}$$
Constraint: $|\text{Grid}| \le 400$.

### 4.2 3x3 Plateau Stability Index ($PSI$)
Let $(x^*, y^*)$ be the cell with the highest optimization score (e.g., Sharpe Ratio $M^*$). The 8 adjacent neighbors $N(x^*, y^*)$ are evaluated:
$$N(x^*, y^*) = \{(x^* + \Delta x, y^* + \Delta y) \mid \Delta x, \Delta y \in \{-1, 0, 1\}, (\Delta x, \Delta y) \ne (0,0)\}$$
For valid neighbor cells within grid boundaries:
$$PSI = \frac{1}{|N|} \sum_{(i,j) \in N} \max\left(0, \frac{M_{i,j}}{M^*}\right)$$
- If $PSI \ge 0.75 \implies \text{Classification: } \mathbf{ROBUST\_PLATEAU}$
- If $0.50 \le PSI < 0.75 \implies \text{Classification: } \mathbf{MODERATE\_SENSITIVITY}$
- If $PSI < 0.50 \implies \text{Classification: } \mathbf{FRAGILE\_CLIFF}$ (Overfitting Warning)

### 4.3 Walk-Forward Efficiency ($WFE$)
Given In-Sample (IS) annualized return $R_{\text{IS}}$ and Out-of-Sample (OOS) annualized return $R_{\text{OOS}}$:
$$WFE = \frac{R_{\text{OOS}}}{R_{\text{IS}}}$$
- If $R_{\text{IS}} \le 0$, $WFE = 0.0$.
- $WFE \ge 0.50$ represents acceptable institutional persistence.

---

## 5. Domain Contracts & Service Interfaces

```python
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

@dataclass
class ParamSpec:
    name: str
    min_val: float
    max_val: float
    step: float

@dataclass
class OptimizationCell:
    param1_val: float
    param2_val: float
    sharpe_ratio: float
    net_pnl: float
    net_pnl_pct: float
    max_drawdown_pct: float
    win_rate: float
    total_trades: int
    profit_factor: float

@dataclass
class StabilityResult:
    optimal_param1: float
    optimal_param2: float
    optimal_sharpe: float
    stability_score: float # 0.0 to 1.0
    classification: str     # 'ROBUST_PLATEAU' | 'MODERATE_SENSITIVITY' | 'FRAGILE_CLIFF'
    neighbor_avg_sharpe: float
    cliff_drop_pct: float

@dataclass
class WalkForwardResult:
    in_sample_net_pnl: float
    in_sample_sharpe: float
    out_of_sample_net_pnl: float
    out_of_sample_sharpe: float
    walk_forward_efficiency: float
    is_split_date: str
```

---

## 6. Implementation Steps
1. Create `services/backtest/optimization_engine.py`:
   - Implement `ParamSpec`, `OptimizationCell`, `StabilityResult`, and `WalkForwardResult` dataclasses.
   - Implement `WalkForwardSplitter.split(df, split_pct)` returning `(is_df, oos_df, split_date)`.
   - Implement `OptimizationEngine.run_grid(df, strategy_name, param1, param2, base_config)` using `ThreadPoolExecutor`.
   - Implement `StabilityAnalyzer.evaluate(matrix, param1_ticks, param2_ticks, target_metric)` computing 3x3 neighbor retention and cliff score.
   - Implement `OptimizationEngine.evaluate_walk_forward(is_df, oos_df, strategy_name, best_params, base_config)`.
2. Create unit tests `tests/unit/test_parameter_optimization_engine.py`:
   - Test parameter range Cartesian expansion & 400 combination cap.
   - Test grid evaluation with synthetic OHLCV bars.
   - Test Plateau Stability score calculation with flat vs cliff matrices.
   - Test Walk-Forward splitting and WFE calculation.

---

## 7. Verification & Acceptance Criteria
- `pytest tests/unit/test_parameter_optimization_engine.py -v` passes 100%.
- Grid execution of 100 combinations completes in $< 2.5$ seconds.
- Zero lookahead bias verified (IS optimization has zero knowledge of OOS bars).
