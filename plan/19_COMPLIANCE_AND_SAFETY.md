# Phase 19: Regulatory Compliance, Security Auditing & Safe Exports

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "plan/00_MASTER_ARCHITECTURE.md"
    - "plan/01_ENVIRONMENT_CONFIG_AND_AUTH.md"
    - "plan/07_FASTAPI_BACKEND_AND_QUANT_APIS.md"
    - "plan/14_BACKTESTING_ENGINE.md"
  reads:
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#6-canonical-configuration-key-registry"
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#10-enterprise-non-functional-requirements-nfr-checklist"
    - "plan/VERIFICATION_REPORT.md#28-indian-costs-sebi-regulations--terms-of-use"
  produces:
    - "core/security.py"
    - "core/logging_config.py"
    - "scripts/audit_security.py"
    - "config/legal_notices.json"
  exposes: []
  must_not_modify:
    - "plan/*"
    - "db/migrations.py"
  test_plan:
    unit_tests: "tests/unit/test_log_redaction.py tests/unit/test_export_sanitization.py"
    integration_tests: "tests/integration/test_security_audit.py"
    contract_tests: "tests/contract/test_compliance_notices.py"
    fixtures: "config/legal_notices.json"
    command: "pytest tests/unit/test_log_redaction.py tests/integration/test_security_audit.py -v"
  definition_of_done:
    - item: 1
      command: "python scripts/audit_security.py"
      result: "Scans repository; confirms zero API keys, secrets, or PINs in .env, code, git commit history, or test fixtures."
    - item: 2
      command: "python -c 'from core.logging_config import RedactingFormatter; import logging; r = RedactingFormatter(); record = logging.LogRecord(\"test\", logging.INFO, \"\", 0, \"Key: 2Q10WHDO67-100 and PIN 1234\", (), None); assert \"1234\" not in r.format(record)'"
      result: "Logging formatter successfully sanitizes API tokens, app secrets, and 4-digit PINs."
    - item: 3
      command: "python -c 'from core.security import verify_export_metadata; assert verify_export_metadata({\"source\": \"Fyers API\", \"license\": \"Personal Non-Commercial\"})'"
      result: "Verifies every exported file contains mandatory personal non-commercial license and survivorship disclaimers."
  failure_modes_and_recovery:
    - failure: "Secret detected in plaintext log output"
      detection: "Audit script regex matches token pattern in application log files"
      recovery: "Purge log file immediately; enforce RedactingFormatter filter across all Python logging handlers"
    - failure: "User attempts automated order routing"
      detection: "Invocation of order execution endpoint or unauthorized broker trading API"
      recovery: "Hard gate: Endpoint does not exist; application halts request with 403 Forbidden: 'Order execution is out of scope'"
  handoff:
    - "Security audit scripts and log redacting formatters operational."
    - "SEBI regulatory disclaimers and export licensing verified."
    - "All phase plans (00 to 19) complete and compliant."
```

---

## 1. Goal & Governance Scope
Establish institutional regulatory compliance, data protection, secret isolation, and export licensing governance across the platform adhering to the 00A Canonical Registry.

This phase delivers:
- Statutory SEBI "Not Investment Advice" disclaimers embedded across all UI views, backtests, and exported files.
- Rigorous regulatory analysis of SEBI's Retail Algorithmic Trading Framework and the enforcement of an architectural hard gate preventing order execution.
- Cryptographic secret management: zero plaintext credentials in `.env`, repositories, or logs; OS Keyring storage; and structured log secret redaction.
- Strict adherence to Fyers End-User License Agreement (EULA) regarding personal, non-commercial data usage and the prevention of illegal commercial redistribution.

---

## 2. SOLID Principles Application
- **Single Responsibility Principle (SRP)**:
  - `SecurityAuditor`: Responsible solely for scanning source code, configurations, and exports for leaked credentials.
  - `RedactingLoggingFormatter`: Responsible solely for scrubbing sensitive patterns from structured log streams.
  - `ComplianceNoticeManager`: Responsible solely for injecting required regulatory disclaimers into UI views and export headers.
- **Open/Closed Principle (OCP)**:
  - Compliance rules implement `IComplianceRule`. Adding new exchange notices or statutory regulatory disclosures requires registering a rule class without altering export or backtesting engines.

---

## 3. SEBI Statutory Disclaimers ("Not Investment Advice")

### 3.1. Regulatory Context
Under the **SEBI (Research Analysts) Regulations, 2014** and **SEBI (Investment Advisers) Regulations, 2013**, providing automated buy/sell recommendations, target prices, or financial advice requires formal SEBI registration.
- This platform is strictly an **analytical data utility and backtesting software**. It does not provide investment advice, portfolio management, or trade recommendations.

### 3.2. Mandatory Legal Text (`config/legal_notices.json`)
```
"DISCLAIMER: This application is a self-directed quantitative data analysis and backtesting tool for educational and research purposes only. It does NOT constitute investment advice, financial advisory, or a recommendation to buy or sell any securities under SEBI regulations. 

All indicators, backtest results, and screener outputs are purely mathematical computations based on historical data. Historical performance is NOT indicative of future returns. Algorithmic trading and equity investments are subject to substantial market risk, including the loss of principal capital. 

Users are solely responsible for their independent investment decisions and should consult a SEBI-registered financial advisor before committing capital to financial markets."
```

### 3.3. Standardized Placement Rules
1. **Persistent UI Footer**: Displayed on every web page in Simple and Pro modes.
2. **Backtest Summary Reports**: Rendered in a high-visibility amber banner at the top of every generated backtest PDF/HTML report.
3. **Data Exports**: Embedded as metadata comments in all exported Parquet, CSV, and Excel files.

---

## 4. SEBI Retail Algorithmic Trading Framework (The Hard Gate)

### 4.1. Technical Analysis of SEBI Retail Algo Regulations
As verified in `VERIFICATION_REPORT.md`, SEBI's regulatory framework for retail algorithmic trading mandates:
1. **Static IP Whitelisting**: Every automated order routed through a broker API must originate from a verified, registered static IP address.
2. **Exchange Algo ID Tagging**: Every automated order must carry a unique Algo ID registered by the broker with the stock exchange.
3. **Orders Per Second (OPS) Ceiling**: Retail automated trading is capped at **10 OPS**. Exceeding 10 OPS classifies the strategy as institutional high-frequency trading requiring comprehensive institutional exchange audits.
4. **Mandatory Daily 2FA**: Automated long-lived unattended trading sessions are prohibited; daily interactive authentication is mandatory.

### 4.2. Application Boundary & Architectural Hard Gate
- **Definitive Scope Boundary**: This platform is strictly an **NSE Equity Data & Research Platform** (Find $\rightarrow$ Analyze $\rightarrow$ Test $\rightarrow$ Monitor $\rightarrow$ Review).
- **Order Execution is STRICTLY OUT OF SCOPE**:
  - The codebase contains zero order placement endpoints (`fyers.place_order()` is forbidden).
  - The app requires no static IP whitelisting, broker strategy approval, or exchange Algo ID registrations.
- **The Architectural Hard Gate**:
  - If automated order execution is ever proposed for future versions, the implementing team must treat SEBI's framework (Static IP, Algo ID, 10 OPS cap, broker risk systems) as an **insurmountable prerequisite gate**.
  - No order routing code may be written until formal broker algorithmic trading approval and exchange audit compliance are certified.

---

## 5. Secret Handling & Cryptographic Sanitization

```
       [ Application Events / Network Calls ]
                         │
                         ▼
        [ Structured JSON Logging Pipeline ]
                         │
                         ▼
       [ RedactingFormatter: Regex Scrubber ]
       - Matches FYERS_SECRET_KEY patterns
       - Matches access_token & refresh_token
       - Matches 4-digit numeric PINs
       - Replaces with "[REDACTED_SECRET]"
                         │
                         ▼
             [ Clean Output: Log File ]
```

### 5.1. Zero Plaintext Credentials
- API secrets and user PINs are stored in the OS Keyring (`keyring` library) or an AES-256 encrypted local vault (`data/.vault.enc`).
- The `.env` file contains only public identifiers (`FYERS_APP_ID`); `.env` is explicitly declared in `.gitignore`.
- Running `git status` verifies `.env` and `data/` are never tracked by source control.

### 5.2. Automated Log Redaction
The application configures a custom `RedactingFormatter` (`core/logging_config.py`) across all log handlers:
- Automatically replaces any string matching API secret formats, bearer tokens, or 4-digit user PINs with `"[REDACTED_SECRET]"`.
- Even in `DEBUG` log mode, raw tokens are never written to disk or stdout.

### 5.3. Export File Sanitization
- `IDataExporter` implementations guarantee that exported Parquet, CSV, and Excel files contain market data only.
- User account numbers, client IDs, tokens, and machine network identifiers are strictly excluded from file metadata.

---

## 6. Fyers Data Redistribution Terms & Licensing

### 6.1. Personal Non-Commercial Use License
Under the Fyers API End-User License Agreement:
- Data retrieved via Fyers API is licensed **strictly for the personal, non-commercial research of the trading account holder**.
- Commercial redistribution, reselling, sublicensing, or public hosting of raw historical candle datasets to third parties is explicitly prohibited.

### 6.2. Compliance Enforcement
- Every exported dataset embeds the standardized personal license tag:
  `"License: Personal Non-Commercial Use Only. Redistribution or commercial resale is prohibited under Fyers API Terms of Service."`
- The web server binds by default to `127.0.0.1` (localhost), preventing inadvertent public network exposure.

---

## 7. Implementation Steps
1. Create `config/legal_notices.json` compiling statutory SEBI disclaimers, survivorship notices, and personal non-commercial license statements.
2. Implement `core/logging_config.py` with `RedactingFormatter` regex sanitization.
3. Implement `core/security.py`:
   - Validates that export metadata contains required disclaimers.
   - Enforces that no order execution modules exist.
4. Implement standalone audit script `scripts/audit_security.py`:
   - Scans entire repository for API keys, unmasked secrets, and git leaks.
   - Asserts that `.env` and `market_data.duckdb` are in `.gitignore`.

---

## 8. Verification & Acceptance Criteria
- Running `python scripts/audit_security.py` passes with zero leaked secrets or untracked sensitive files.
- Logging a simulated string containing `FYERS_SECRET_KEY` outputs `[REDACTED_SECRET]` in log files.
- Every page rendered in `static/index.html` displays the statutory SEBI disclaimer in the footer.
- Generating a Parquet, CSV, or Excel export verifies that the output file contains the personal non-commercial license tag and survivorship disclosure.
- Order execution gate verified: zero references to order placement APIs exist in the codebase.
