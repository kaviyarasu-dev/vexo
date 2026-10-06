# Task Brief: Patch 08_FRONTEND_CHARTING_AND_DASHBOARD.md

**Target File**: `plan/08_FRONTEND_CHARTING_AND_DASHBOARD.md` (ONLY this file may be modified)  
**Allowed Read Set**:
- `plan/00A_CONTRACTS_AND_CONVENTIONS.md`
- `plan/08_FRONTEND_CHARTING_AND_DASHBOARD.md`
- `plan/VERIFICATION_REPORT.md`

**Objective**:
Upgrade `08_FRONTEND_CHARTING_AND_DASHBOARD.md` to enterprise quant architecture standards:
1. Add mandatory EXECUTION CONTRACT block at top.
2. Incorporate Simple Mode vs Pro Mode UI toggle (referencing Phase 11 without duplicating):
   - Simple Mode: Beginner-friendly, uncluttered, plain-language labels, high-level timeframes.
   - Pro Mode: Institutional multi-pane (Candles, Volume, Oscillators), all 11 canonical timeframes, Session VWAP, advanced indicators.
3. Integrate glossary tooltips and guided onboarding references (referencing Phase 18).
4. Implement clean empty states for pending symbols or freshly initialized databases.
5. Add Token Lifecycle & Re-Auth UI in top navigation bar:
   - Live token expiry countdown.
   - Re-authentication modal triggered when token is expired or within 1 hour of expiry.
6. Connect historical pan lazy-loading to backend `limit` and `cursor` parameters from Phase 07.
7. Keep file under 400 lines.

**Acceptance Self-Test**:
- Begins with EXECUTION CONTRACT.
- Simple Mode vs Pro Mode explicitly defined with UI layout diagrams.
- Re-auth UI and token countdown specified.
- Historical lazy-loading cites `limit` and `cursor` API contracts.
