# Task Brief: Patch 05_RESAMPLING_AND_QUANT_METRICS_ENGINE.md

**Target File**: `plan/05_RESAMPLING_AND_QUANT_METRICS_ENGINE.md` (ONLY this file may be modified)  
**Allowed Read Set**:
- `plan/00A_CONTRACTS_AND_CONVENTIONS.md`
- `plan/05_RESAMPLING_AND_QUANT_METRICS_ENGINE.md`
- `plan/VERIFICATION_REPORT.md`

**Objective**:
Upgrade `05_RESAMPLING_AND_QUANT_METRICS_ENGINE.md` to enterprise quant architecture standards:
1. Add mandatory EXECUTION CONTRACT block at top.
2. Formulate IST session-correct bucketing with exact UTC conversion:
   - $09:15\text{ IST} - 05:30 = 03:45\text{ UTC}$.
   - DuckDB `time_bucket` with explicit `origin` parameter (`TIMESTAMP '2000-01-01 03:45:00'`).
   - Explicitly detail session stub bars for 30m, 1h, 2h, 4h.
3. Default query source: reads from `candles_1m_adjusted` (dynamic view), supporting unadjusted raw reads via flag `adjusted=False`.
4. Zero-volume bar rule: never forward-fill fake bars into storage; resampler flags empty higher-timeframe buckets with `is_zero_volume = TRUE`, `volume = 0`, and previous close.
5. Golden fixture test plan covering ALL 11 canonical timeframes.
6. Align interfaces: `IResamplingService`, `IIndicator`.
7. Keep file under 400 lines.

**Acceptance Self-Test**:
- Begins with EXECUTION CONTRACT.
- UTC conversion math shown ($09:15 - 05:30 = 03:45$).
- Zero references to retired `IResampler` or `IIndicatorCalculator`.
- Golden fixture tests specified for all 11 timeframes.
