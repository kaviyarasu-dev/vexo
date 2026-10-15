# Plan 01-001: Calendar Engine & Quantitative Diagnostics API

## 1. Execution Contract
```yaml
execution_contract:
  plan_id: "01-001"
  name: "Calendar Engine & Quantitative Diagnostics API"
  feature: "journal-calendar-and-analytics"
  depends_on: []
  reads:
    - "services/journal_service.py"
    - "api/routers/journal.py"
    - "core/interfaces.py"
    - "db/migrations.py"
  produces:
    - "services/journal/calendar_service.py"
    - "services/journal/diagnostics_service.py"
    - "api/models/journal_models.py"
    - "tests/unit/test_journal_calendar_engine.py"
    - "tests/integration/test_journal_calendar_api.py"
  exposes:
    - "GET /api/v1/journal/calendar"
    - "GET /api/v1/journal/diagnostics"
  must_not_modify:
    - "db/connection.py"
    - "core/rate_governor.py"
    - "services/backtest/engine.py"
  test_plan:
    unit_tests: "pytest tests/unit/test_journal_calendar_engine.py -v"
    integration_tests: "pytest tests/integration/test_journal_calendar_api.py -v"
    command: "pytest tests/unit/test_journal_calendar_engine.py tests/integration/test_journal_calendar_api.py -v"
  definition_of_done:
    - "Calendar engine groups closed trades strictly by exit_time date in IST"
    - "Consecutive winning and losing daily streaks are mathematically computed without gaps"
    - "Time-of-day bucketing accurately tags morning (09:15-10:30), midday (10:30-13:00), and afternoon (13:00-15:30) trades"
    - "Direction (Long/Short) and holding duration (Intraday/Swing) metrics compute win rate, profit factor, and net P&L"
    - "All tests pass with 100% assertions and no lock contention with DuckDB"
  failure_modes_and_recovery:
    - "Zero trades recorded: Returns empty calendar days with 0 KPIs rather than throwing 500"
    - "Trades spanning months: Realized P&L is mapped exclusively to the month of exit_time"
    - "Null exit times: Open trades are safely omitted from realized daily P&L calculations"
  handoff:
    next_plan: "02-001"
    requires: "Calendar and Diagnostics endpoints active and returning validated schemas"
```

---

## 2. Goal & Scope / User Jobs Served
Quantitative traders need an objective, visual feedback loop to evaluate daily performance, emotional discipline, and execution habits.
- **Monthly P&L Wall Calendar**: Groups trades by closing date to calculate daily Net Realized P&L, Win/Loss trade ratios, weekly totals, and maximum winning/losing day streaks.
- **Quantitative Diagnostics**: Pinpoints where a trader makes or loses money across the Indian trading day (09:15-10:30 opening session vs. midday chop vs. 13:00-15:30 closing flow), direction bias (Long vs. Short), and holding duration (Intraday vs. Swing).

---

## 3. Architecture & SOLID Principles Application
- **Single Responsibility Principle (SRP)**:
  - `JournalCalendarService`: Pure focus on calendar aggregation, date bucket mapping, weekly rollups, and streak computation.
  - `JournalDiagnosticsService`: Pure focus on multi-dimensional performance attribution (session time-of-day, direction, duration, instrument).
  - `JournalRouter`: Handles HTTP validation, query parameter parsing, and serialization.
- **Open-Closed Principle (OCP)**:
  - New session segments or diagnostic dimensions can be added without modifying the core trade retrieval queries.
- **Dependency Inversion Principle (DIP)**:
  - Relies on DuckDB read cursors via `DuckDBConnectionManager` ensuring isolated non-locking queries.

---

## 4. Domain & Mathematical Specifications

### 4.1 Daily P&L Attribution & Streak Algorithm
- **Attribution Rule**:
  $$\text{Realized Date} = \text{CAST}(\text{exit\_time AS DATE})$$
- **Daily Net P&L**:
  $$\text{Net P&L}_{\text{day}} = \sum_{t \in \text{Trades}_{\text{day}}} \text{pnl\_net}_t$$
- **Streak Calculation**:
  Given ordered list of trading days $D = [d_1, d_2, \dots, d_n]$ where $\text{trades\_count} > 0$:
  - A day is a **Win Day** if $\text{Net P&L}_{\text{day}} > 0$.
  - A day is a **Loss Day** if $\text{Net P&L}_{\text{day}} < 0$.
  - A day is **Breakeven** if $\text{Net P&L}_{\text{day}} == 0$.
  - Max Win Streak = $\max(\text{consecutive Win Days in } D)$.
  - Max Loss Streak = $\max(\text{consecutive Loss Days in } D)$.

### 4.2 Time-of-Day Session Windows (IST)
- **Morning Momentum**: `09:15:00 <= entry_time < 10:30:00`
- **Midday Chop**: `10:30:00 <= entry_time < 13:00:00`
- **Afternoon Flow**: `13:00:00 <= entry_time <= 15:30:00`
- **Off-Hours / Other**: All other entry times.

### 4.3 Holding Duration Classification
- **Intraday**: $\text{CAST}(\text{entry\_time AS DATE}) == \text{CAST}(\text{exit\_time AS DATE})$
- **Swing / Positional**: $\text{CAST}(\text{exit\_time AS DATE}) > \text{CAST}(\text{entry\_time AS DATE})$

---

## 5. Domain Contracts & Service Interfaces

### 5.1 Pydantic Models (`api/models/journal_models.py`)
```python
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class CalendarDayItem(BaseModel):
    date: str  # YYYY-MM-DD
    day_of_month: int
    day_of_week: int  # 0=Mon, 6=Sun
    net_pnl: float
    gross_pnl: float
    total_charges: float
    trades_count: int
    win_count: int
    loss_count: int
    status: str  # 'WIN' | 'LOSS' | 'EVEN' | 'NO_TRADES'

class CalendarWeekSummary(BaseModel):
    week_number: int
    net_pnl: float
    trades_count: int
    win_count: int
    loss_count: int

class CalendarMonthlyKPIs(BaseModel):
    monthly_net_pnl: float
    trading_days: int
    win_days: int
    loss_days: int
    win_day_pct: float
    max_win_streak: int
    max_loss_streak: int
    avg_win_day_pnl: float
    avg_loss_day_pnl: float
    profit_factor: float

class CalendarResponse(BaseModel):
    success: bool
    year: int
    month: int
    kpis: CalendarMonthlyKPIs
    days: List[CalendarDayItem]
    weeks: List[CalendarWeekSummary]

class DiagnosticBucket(BaseModel):
    name: str
    label: str
    trades_count: int
    win_rate: float
    net_pnl: float
    avg_r: float
    profit_factor: float

class DiagnosticsResponse(BaseModel):
    success: bool
    time_of_day: List[DiagnosticBucket]
    direction: List[DiagnosticBucket]
    duration: List[DiagnosticBucket]
    instruments: List[DiagnosticBucket]
```

---

## 6. Implementation Steps
1. Create `api/models/journal_models.py` with Pydantic response models.
2. Implement `services/journal/calendar_service.py`:
   - `get_monthly_calendar(year: int, month: int) -> CalendarResponse`
   - Handles DuckDB date queries, fills missing calendar dates with 0 P&L, computes weekly row rollups and streak metrics.
3. Implement `services/journal/diagnostics_service.py`:
   - `get_quantitative_diagnostics() -> DiagnosticsResponse`
   - Groups trades into morning/midday/afternoon buckets, Long/Short, Intraday/Swing, and Equity/F&O.
4. Mount new endpoints in `api/routers/journal.py`:
   - `GET /api/v1/journal/calendar`
   - `GET /api/v1/journal/diagnostics`
5. Author unit tests `tests/unit/test_journal_calendar_engine.py` and integration tests `tests/integration/test_journal_calendar_api.py`.

---

## 7. Verification & Acceptance Criteria
- `pytest tests/unit/test_journal_calendar_engine.py tests/integration/test_journal_calendar_api.py -v` passes 100%.
- Daily calendar accurately reflects net P&L after statutory charges.
- Consecutive streak calculations match manual ground truth.
- Zero DuckDB writer lock contention.
