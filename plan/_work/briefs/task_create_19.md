# Task Brief: Create 19_COMPLIANCE_AND_SAFETY.md

**Target File**: `plan/19_COMPLIANCE_AND_SAFETY.md` (ONLY this file may be modified)  
**Allowed Read Set**:
- `plan/00A_CONTRACTS_AND_CONVENTIONS.md`
- `plan/VERIFICATION_REPORT.md`

**Objective**:
Create `19_COMPLIANCE_AND_SAFETY.md` specifying regulatory compliance, secret security, and data licensing governance:
1. Begin with mandatory EXECUTION CONTRACT block.
2. Formulate SEBI Statutory Disclaimers ("Not Investment Advice"):
   - Complies with SEBI (Research Analysts) Regulations 2014.
   - Exact legal wording and standardized placement across UI footers, backtest summaries, and export headers.
3. SEBI Retail Algorithmic Trading Framework Analysis:
   - Technical breakdown of SEBI's retail algo framework (Static IP whitelisting, exchange Algo IDs, 10 Orders Per Second limit, mandatory daily 2FA).
   - Definitive boundary: This application is strictly a research and backtesting platform; order placement is OUT OF SCOPE.
   - Enforce as an architectural hard gate preventing future order routing without formal regulatory approval.
4. Secret Handling & Cryptographic Security:
   - OS Keyring / AES-256 credential vault.
   - Structured JSON logging with automated regex secret redaction.
   - Zero credentials in `.env`, exports, or error traces.
5. Fyers Data Redistribution Licensing:
   - Personal non-commercial license enforcement.
   - Prohibition on commercial data reselling or public redistribution.
6. Keep file under 400 lines.
