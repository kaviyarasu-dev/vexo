# Task Brief: Create 13_ALERTS_AND_WATCHLISTS.md

**Target File**: `plan/13_ALERTS_AND_WATCHLISTS.md` (ONLY this file may be modified)  
**Allowed Read Set**:
- `plan/00A_CONTRACTS_AND_CONVENTIONS.md`
- `plan/VERIFICATION_REPORT.md`

**Objective**:
Create `13_ALERTS_AND_WATCHLISTS.md` specifying the alert evaluation and watchlist monitoring engine:
1. Begin with mandatory EXECUTION CONTRACT block.
2. Outline User Jobs: "Monitor my watchlist for critical price, indicator, and volume breakouts without keeping my eyes glued to the screen."
3. Alert Rule Typology:
   - Price threshold & crossover rules.
   - Technical indicator rules (Session VWAP cross, RSI oversold/overbought).
   - Screener match alerts (triggering when a watchlist stock matches a saved scan).
4. Notification Channels & Dispatch:
   - In-app toast / bell notification drawer.
   - Email (SMTP).
   - Telegram Bot webhook.
5. Production Operational Safeguards:
   - Alert state machine: `PENDING`, `ARMED`, `TRIGGERED`, `MUTED`, `EXPIRED`.
   - Cooldown & deduplication: 15-minute suppression window after trigger.
   - Quiet hours: no external pings between 23:00 and 08:00 IST.
   - RateGovernor integration: market quote evaluations run through Lane 2 in 50-symbol batches consuming $\le 10$ req/min.
   - Token expiry behavior: transitions to `PAUSED_AUTH_EXPIRED` cleanly.
6. Align interface: `IAlertService`.
7. Keep file under 400 lines.
