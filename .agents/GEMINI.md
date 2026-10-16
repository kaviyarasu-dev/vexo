# NSE Quant Platform - Agent Rules (GEMINI.md)

## 1. Architectural Standards
- **Tech Stack:** Python, FastAPI, DuckDB, React, Lightweight Charts.
- **Separation of Concerns:** Strict layer separation (Routes -> Service -> Repository). No application logic in `core/`.
- **Database Engine (DuckDB):** 
  - SINGLE writer process (`uvicorn workers=1`).
  - Read queries must use independent cursors (`conn.cursor()`) to avoid acquiring the writer lock.
  - Raw tables are append-only.
- **Typing:** Strict Python type hints and ABCs for all interfaces.

## 2. Security Rules
- **No Secrets in Code:** NEVER hardcode API keys (Fyers client ID, secret, tokens). Use OS Keyring or encrypted `.vault.enc`.
- **.env Safety:** Ensure `.env` is always in `.gitignore`. Do not read or write raw `.env` files with real keys.
- **File Access:** NEVER read or write to `plan/_work/`. It is forbidden.

## 3. Financial Data Rules
- **Timezone:** All timestamps, resampling, and scheduling must align strictly with IST (Indian Standard Time).
- **Data Validation:** Validate all OHLCV data. Handle splits, bonuses, and delisted stocks appropriately.
- **Holidays:** Rely on the dynamically fetched NSE calendar for trading days, not hardcoded dates.

## 4. Phase Execution & Handoff
- **Rule of One:** One Phase = One Fresh Conversation. Do NOT run two phases in the same chat.
- **Handoff Ledger:** After completing each phase, append a `STATUS: DONE` entry to `plan/HANDOFF.md` along with artifacts produced.
- **Hard Gates:** Follow the phase execution order strictly (e.g., Phase 09 is a hard gate for Stage 4).
