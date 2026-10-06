# Task Brief: Patch 01_ENVIRONMENT_CONFIG_AND_AUTH.md

**Target File**: `plan/01_ENVIRONMENT_CONFIG_AND_AUTH.md` (ONLY this file may be modified)  
**Allowed Read Set**:
- `plan/00A_CONTRACTS_AND_CONVENTIONS.md`
- `plan/01_ENVIRONMENT_CONFIG_AND_AUTH.md`
- `plan/VERIFICATION_REPORT.md`

**Objective**:
Upgrade `01_ENVIRONMENT_CONFIG_AND_AUTH.md` to enterprise quant architecture standards:
1. Add mandatory EXECUTION CONTRACT block at top.
2. Incorporate full verified Fyers OAuth v3 flow:
   - Access token daily expiry at ~06:00 AM IST.
   - Refresh token 15-day validity requiring appIdHash and user PIN.
   - Secure PIN and token storage: use OS Keyring (`keyring` package) or encrypted vault (`data/.vault.enc`), NEVER plain `.env`.
   - 15-day re-login reminder and UI expiry countdown.
   - Pre-flight check at 15:40 IST before the 15:45 IST scheduled sync.
3. Align config keys with 00A Section 6 (`FYERS_APP_ID`, `FYERS_SECRET_KEY`, `AUTH_CREDENTIAL_STORAGE`, `RATE_GOVERNOR_*`, etc.).
4. Use canonical interface `IAuthService`.
5. Keep file under 400 lines while retaining original document structure.

**Acceptance Self-Test**:
- Begins with EXECUTION CONTRACT.
- Zero plaintext PIN or tokens in `.env`.
- Explicit 15-day refresh token lifecycle and daily access token renewal flow.
- Definition of Done commands and measurable results specified.
