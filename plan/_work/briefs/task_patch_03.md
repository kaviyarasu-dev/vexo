# Task Brief: Patch 03_SYMBOL_MASTER_AND_UNIVERSE_MANAGER.md

**Target File**: `plan/03_SYMBOL_MASTER_AND_UNIVERSE_MANAGER.md` (ONLY this file may be modified)  
**Allowed Read Set**:
- `plan/00A_CONTRACTS_AND_CONVENTIONS.md`
- `plan/03_SYMBOL_MASTER_AND_UNIVERSE_MANAGER.md`
- `plan/VERIFICATION_REPORT.md`

**Objective**:
Upgrade `03_SYMBOL_MASTER_AND_UNIVERSE_MANAGER.md` to enterprise quant architecture standards:
1. Add mandatory EXECUTION CONTRACT block at top.
2. Fix tier arithmetic and hierarchy:
   - Tier 1: Nifty 50 (50) + Nifty Next 50 (50) = 100 stocks.
   - Tier 2: Nifty Midcap 150 = 150 stocks.
   - Tier 3: Nifty Smallcap 250 = 250 stocks.
   - Total Tiers 1-3 = Exactly Nifty 500 (500 stocks).
   - Tier 4: Remaining non-Nifty-500 NSE equities (~1,500+ stocks).
   - Eliminate the old "remaining Nifty 500 constituents" error.
3. Automated constituent ingestion:
   - Constituents and holidays fetched via automated scripts (`scripts/fetch_nse_indices.py`, `scripts/fetch_nse_holidays.py`) from official NSE URLs, NEVER hardcoded in plans or model memory.
   - Provide manual override fallback JSON files (`config/indices/manual_override_indices.json`, `config/holidays/manual_override_holidays.json`).
4. Default Universe Rules:
   - 1m Intraday scope = Nifty 500 (Tiers 1-3).
   - 1D Daily scope = All active NSE EQ stocks (Tiers 1-4).
5. Incorporate verified Fyers `NSE_CM.csv` specifications (no header, 0-indexed columns).
6. Align interfaces: `ISymbolRepository`.
7. Keep file under 400 lines.

**Acceptance Self-Test**:
- Begins with EXECUTION CONTRACT.
- Arithmetic is verified: $100 + 150 + 250 = 500$.
- No hardcoded constituent lists or holidays; script + override file specified.
