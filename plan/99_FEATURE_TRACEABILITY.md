# Phase 99: Master Feature Traceability Matrix & Scope Boundary Registry

**Document Version**: 1.0.0  
**Status**: APPROVED ARCHITECTURAL BASELINE  
**Purpose**: Guarantees 100% bidirectional traceability from high-level user jobs down to individual execution contracts, test commands, and delivery phases.

---

## 1. Traceability Matrix

Every feature planned across Phases 00 through 19 appears in this matrix. Priorities follow standard MoSCoW notation (Must have, Should have, Could have, Won't have). Every **Must Have** is linked to a concrete Definition of Done in its owner phase document.

| User Job | Feature Description | Plan File | Phase | Priority | Definition of Done Link / Test Command |
|---|---|---|---|---|---|
| **Platform** | Unified SOLID interfaces & exceptions | `00_MASTER_ARCHITECTURE.md` | 00 | **Must** | `pytest tests/contract/test_canonical_registry.py` |
| **Platform** | Canonical contracts & timeframes | `00A_CONTRACTS_AND_CONVENTIONS.md` | 00A | **Must** | Locked architectural gate |
| **Platform** | Pydantic settings & masked secrets | `01_ENVIRONMENT_CONFIG_AND_AUTH.md` | 01 | **Must** | `pytest tests/unit/test_settings.py` |
| **Platform** | Dual-token auth & Keyring vault | `01_ENVIRONMENT_CONFIG_AND_AUTH.md` | 01 | **Must** | `python scripts/auth_cli.py --status` |
| **Platform** | DuckDB schema DDLs & versioning | `02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md` | 02 | **Must** | `python -c 'from db.migrations import init_db; init_db()'` |
| **Platform** | Non-blocking reader cursors | `02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md` | 02 | **Must** | `pytest tests/integration/test_duckdb_concurrency.py` |
| **Find** | Automated symbol master ingestion | `03_SYMBOL_MASTER_AND_UNIVERSE_MANAGER.md` | 03 | **Must** | `python scripts/sync_symbols.py` |
| **Find** | Nifty 500 tier classification | `03_SYMBOL_MASTER_AND_UNIVERSE_MANAGER.md` | 03 | **Must** | Tier check: $100 + 150 + 250 = 500$ stocks |
| **Analyze** | Global RateGovernor (180/min) | `04_HISTORICAL_DOWNLOADER_ENGINE.md` | 04 | **Must** | `pytest tests/unit/test_rate_governor.py` |
| **Analyze** | Resumable chunk downloader | `04_HISTORICAL_DOWNLOADER_ENGINE.md` | 04 | **Must** | `pytest tests/integration/test_downloader_resumption.py` |
| **Analyze** | IST-aligned dynamic resampling | `05_RESAMPLING_AND_QUANT_METRICS_ENGINE.md` | 05 | **Must** | `pytest tests/unit/test_resampling_math.py` |
| **Analyze** | Session-reset VWAP & quant features | `05_RESAMPLING_AND_QUANT_METRICS_ENGINE.md` | 05 | **Must** | Session VWAP reset assertion at 09:15 IST |
| **Monitor** | Automated 15:45 IST incremental sync | `06_DAILY_INCREMENTAL_UPDATE_AND_SCHEDULER.md` | 06 | **Must** | `pytest tests/integration/test_missed_run_catchup.py` |
| **Monitor** | Trading calendar holiday filter | `06_DAILY_INCREMENTAL_UPDATE_AND_SCHEDULER.md` | 06 | **Must** | `python -c 'assert not tc.is_trading_day("2024-01-26")'` |
| **Platform** | FastAPI REST & SSE telemetry | `07_FASTAPI_BACKEND_AND_QUANT_APIS.md` | 07 | **Must** | `pytest tests/contract/test_api_envelope.py` |
| **Analyze** | Streaming Parquet & CSV export | `07_FASTAPI_BACKEND_AND_QUANT_APIS.md` | 07 | **Must** | `python -c 'import pandas as pd; pd.read_parquet(...)'` |
| **Platform** | Excel 1,048,575 row ceiling guard | `07_FASTAPI_BACKEND_AND_QUANT_APIS.md` | 07 | **Must** | HTTP 400 `EXCEL_ROW_LIMIT_EXCEEDED` on breach |
| **Analyze** | Lightweight Charts multi-pane UI | `08_FRONTEND_CHARTING_AND_DASHBOARD.md` | 08 | **Must** | `curl http://localhost:8000/static/index.html` |
| **Analyze** | Crosshair time synchronization | `08_FRONTEND_CHARTING_AND_DASHBOARD.md` | 08 | **Must** | Unified cursor coordinate dispatch across sub-panes |
| **Platform** | Token countdown & re-auth modal | `08_FRONTEND_CHARTING_AND_DASHBOARD.md` | 08 | **Must** | Live countdown in navbar; re-auth prompt |
| **Platform** | Milestone 1 benchmark on RELIANCE | `09_MILESTONE_1_RELIANCE_VERIFICATION.md` | 09 | **Must** | `python scripts/run_m1_benchmark.py` |
| **Platform** | Scaling Readiness 5-Gate pass | `09_MILESTONE_1_RELIANCE_VERIFICATION.md` | 09 | **Must** | All 5 scaling gates pass; report generated |
| **Platform** | Post-sync WAL checkpoint & vacuum | `10_EDGE_CASES_RISKS_AND_MAINTENANCE.md` | 10 | **Must** | WAL file shrinks to 0 bytes |
| **Platform** | Weekly backup restore drill | `10_EDGE_CASES_RISKS_AND_MAINTENANCE.md` | 10 | **Must** | `python scripts/run_backup_drill.py` |
| **Platform** | Corporate action price anomaly audit| `10_EDGE_CASES_RISKS_AND_MAINTENANCE.md` | 10 | **Must** | Auditor flags $> 25\%$ single-day moves |
| **UX** | Simple Mode vs Pro Mode switcher | `11_PERSONAS_AND_SIMPLE_PRO_UX.md` | 11 | **Must** | `pytest tests/integration/test_mode_switching.py` |
| **UX** | Plain-language translation registry | `11_PERSONAS_AND_SIMPLE_PRO_UX.md` | 11 | **Must** | `config/ux_translations.json` complete |
| **Find** | Multi-factor technical screener | `12_SCREENER_ENGINE.md` | 12 | **Must** | Full Nifty 500 scan in $< 2.0\text{ seconds}$ |
| **Find** | 1-Click pre-built screener cards | `12_SCREENER_ENGINE.md` | 12 | **Must** | 3 pre-built templates in `config/screener_templates.json` |
| **Find** | Screener row one-click jump to chart| `12_SCREENER_ENGINE.md` | 12 | **Must** | Row click updates main chart view |
| **Monitor** | Real-time price & VWAP alerts | `13_ALERTS_AND_WATCHLISTS.md` | 13 | **Must** | `pytest tests/unit/test_alert_rules.py` |
| **Monitor** | Telegram & Email dispatch | `13_ALERTS_AND_WATCHLISTS.md` | 13 | **Should** | Webhook POST and SMTP dispatch |
| **Monitor** | 15-minute alert cooldown & quiet hrs| `13_ALERTS_AND_WATCHLISTS.md` | 13 | **Must** | Cooldown suppression & 23:00-08:00 quiet hours |
| **Test** | Realistic Indian statutory cost model| `14_BACKTESTING_ENGINE.md` | 14 | **Must** | STT, Brokerage, SEBI fee, GST, Stamp duty match |
| **Test** | Anti-lookahead execution engine | `14_BACKTESTING_ENGINE.md` | 14 | **Must** | Lookahead adversarial test must fail |
| **Test** | Monte Carlo & Walk-Forward analysis | `14_BACKTESTING_ENGINE.md` | 14 | **Should** | 1,000 resampled iterations with 95% CI |
| **Analyze** | Corporate actions adjustment engine | `15_CORPORATE_ACTIONS_AND_EXTERNAL_DATA.md` | 15 | **Must** | Cumulative price & volume factors in SQL views |
| **Analyze** | UDiFF Bhavcopy & delivery volume | `15_CORPORATE_ACTIONS_AND_EXTERNAL_DATA.md` | 15 | **Should** | `python scripts/fetch_bhavcopy_udiff.py` |
| **Analyze** | Daily EOD option-chain snapshots | `16_OPTIONS_MODULE.md` | 16 | **Should** | Captured at 15:35 IST into `option_chain_snapshots` |
| **Analyze** | Black-Scholes Greeks engine | `16_OPTIONS_MODULE.md` | 16 | **Must** | `pytest tests/unit/test_greeks_math.py` |
| **Analyze** | Max Pain strike optimization | `16_OPTIONS_MODULE.md` | 16 | **Must** | Max pain algorithm minimization verified |
| **Analyze** | Interactive multi-leg payoff curve | `16_OPTIONS_MODULE.md` | 16 | **Should** | Canvas payoff plot with breakeven calculation |
| **Review** | Trade journal with $R$-multiples | `17_JOURNAL_AND_PAPER_TRADING.md` | 17 | **Must** | $R = (\text{Gain}) / R_{\text{risk}}$ calculation |
| **Review** | Fyers/Zerodha tradebook CSV import | `17_JOURNAL_AND_PAPER_TRADING.md` | 17 | **Should** | FIFO trade matching from tradebook CSV |
| **Test** | Paper trading execution simulator | `17_JOURNAL_AND_PAPER_TRADING.md` | 17 | **Should** | Virtual fills applying Phase 14 cost model |
| **Review** | Behavioral mistake tagging | `17_JOURNAL_AND_PAPER_TRADING.md` | 17 | **Must** | `config/mistake_tags.json` + cost of mistakes |
| **Learn** | Educational three-part glossary | `18_BEGINNER_LEARNING_LAYER.md` | 18 | **Must** | 100% of terms have definition, analogy, risk |
| **Learn** | Contextual "What does this mean?" | `18_BEGINNER_LEARNING_LAYER.md` | 18 | **Must** | Glassmorphic popover on hover in Simple Mode |
| **Learn** | Guided first-scan interactive tour | `18_BEGINNER_LEARNING_LAYER.md` | 18 | **Should** | 4-step onboarding spotlight tour |
| **Safety** | Statutory SEBI disclaimers | `19_COMPLIANCE_AND_SAFETY.md` | 19 | **Must** | Persistent footer and export header notices |
| **Safety** | SEBI retail algo regulatory hard gate| `19_COMPLIANCE_AND_SAFETY.md` | 19 | **Must** | Order execution locked out of scope |
| **Safety** | Automated log secret redaction | `19_COMPLIANCE_AND_SAFETY.md` | 19 | **Must** | Regex redacting tokens, keys, and 4-digit PINs |
| **Safety** | Personal non-commercial license tag | `19_COMPLIANCE_AND_SAFETY.md` | 19 | **Must** | Embedded on all exported Parquet/CSV/Excel |

---

## 2. Cut Items & Out-of-Scope Registry

To maintain focus and avoid scope creep, the following candidate features are explicitly excluded with clear architectural and regulatory justifications:

| Feature Candidate | Reason for Cut / Exclusion | Regulatory / Architectural Justification |
|---|---|---|
| **Direct Order Execution / Broker Trading Routing** | **EXCLUDED (Hard Cut)** | Current scope is strictly a Research & Data Platform (Find $\rightarrow$ Analyze $\rightarrow$ Test $\rightarrow$ Monitor $\rightarrow$ Review). Direct order execution would subject the local app to SEBI's retail algo trading regulations (mandatory static IP whitelisting, broker strategy registration, and exchange Algo ID tagging). |
| **Multi-Tenant Cloud Architecture / User Accounts** | **EXCLUDED** | Application is designed for single-user local deployment. Multi-tenancy introduces cloud hosting costs, authentication infrastructure, and security vectors without benefiting the quant desktop workflow. |
| **Cloning TradingView Charting Engine** | **EXCLUDED** | We use TradingView's official **Lightweight Charts** library. Building a custom canvas charting engine from scratch wastes thousands of engineering hours without adding quantitative value. |
| **Real-Time Level 2 / Tick-by-Tick Order Book Depth** | **EXCLUDED** | Broker historical APIs do not provide historical Level 2 market depth. Storing full tick books for 2,000 stocks locally would exceed terabytes of storage and overwhelm local single-user disk I/O. |
| **Proprietary Scripting Language (e.g. Pine Script clone)**| **EXCLUDED** | Systematic quant traders prefer standard Python, Pandas, and Polars. Custom domain-specific languages limit interoperability. |
| **Intraday 1-Minute Backfill for Tier 4 Penny Stocks** | **EXCLUDED** | Tier 4 (~1,500 illiquid micro-caps) wastes 1m API request quotas on non-trading instruments. Tier 4 receives daily 1D EOD data; 1m is focused on the Nifty 500 (Tiers 1-3). |
| **Retrospective Expired Options Historical Candles** | **EXCLUDED** | Fyers API does not provide historical candles for expired options contracts. We implement forward snapshot collection instead. |
