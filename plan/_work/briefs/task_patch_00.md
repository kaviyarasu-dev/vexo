# Task Brief: Patch 00_MASTER_ARCHITECTURE.md

**Target File**: `plan/00_MASTER_ARCHITECTURE.md` (ONLY this file may be modified)  
**Allowed Read Set**:
- `plan/00A_CONTRACTS_AND_CONVENTIONS.md`
- `plan/00_MASTER_ARCHITECTURE.md`
- `plan/VERIFICATION_REPORT.md`

**Objective**:
Upgrade `00_MASTER_ARCHITECTURE.md` to enterprise quant architecture standards:
1. Add mandatory EXECUTION CONTRACT block at the beginning.
2. Update roadmap to include 00A, 11-19, 99, and IMPLEMENTATION_ORDER.
3. Update directory/folder layout to match all 20 phases (including screener, alerts, backtest, journal, options, corporate actions, compliance).
4. Fix concurrency section 4.2: reads use lightweight cursors (`conn.cursor()`), NOT the write lock; only writes are queued and serialized under the write lock.
5. Use canonical interface names from 00A (`IAuthService`, `IMarketDataProvider`, `ISymbolRepository`, `ICandleReader`, `ICandleWriter`, `ICheckpointRepository`, `IResamplingService`, `IIndicator`, `IDataExporter`, `ICandleService`, `IScreenerService`, etc.).
6. Use canonical timeframes from 00A (`1m`, `3m`, `5m`, `10m`, `15m`, `30m`, `1h`, `2h`, `4h`, `1D`, `1W`).
7. Keep file under 400 lines while retaining original document structure and quantitative depth.

**Acceptance Self-Test**:
- Begins with EXECUTION CONTRACT with all required sections.
- Zero references to retired interface names (`IResampler`, `IIndicatorCalculator`, `DataExporter`).
- Concurrency model explicitly distinguishes writer lock from reader cursors.
- Roadmap lists all phases up to 19 + 99.
