# Phase 01: Environment Configuration, Security & Fyers API v3 Authentication

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "plan/00_MASTER_ARCHITECTURE.md"
  reads:
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#1-canonical-interface-registry"
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#6-canonical-configuration-key-registry"
    - "plan/VERIFICATION_REPORT.md#24-authentication-refresh-token--pin-storage"
  produces:
    - "config/settings.py"
    - "services/auth_service.py"
    - "core/exceptions.py"
    - "scripts/auth_cli.py"
    - ".env.example"
  exposes:
    - "IAuthService"
  must_not_modify:
    - "plan/*"
    - "db/*"
  test_plan:
    unit_tests: "tests/unit/test_settings.py"
    integration_tests: "tests/integration/test_auth_service.py"
    contract_tests: "tests/contract/test_auth_contract.py"
    fixtures: "tests/fixtures/mock_fyers_profile.json"
    command: "pytest tests/unit/test_settings.py tests/contract/test_auth_contract.py -v"
  definition_of_done:
    - item: 1
      command: "python -c 'from config.settings import get_settings; s = get_settings(); assert \"***\" in str(s.FYERS_SECRET_KEY)'"
      result: "Pydantic Settings loads without error; secrets are masked as SecretStr."
    - item: 2
      command: "pytest tests/contract/test_auth_contract.py"
      result: "IAuthService passes all contract assertions for get_auth_url, exchange_code_for_token, and validate_session."
    - item: 3
      command: "python scripts/auth_cli.py --status"
      result: "Reports authentication status, days remaining on refresh token, and token expiration countdown without exposing secrets."
  failure_modes_and_recovery:
    - failure: "Refresh token expired after 15 calendar days"
      detection: "validate_refresh_token returns error code or HTTP 401"
      recovery: "Emit AuthenticationExpiredError with prompt: '15-day refresh window expired. Run python scripts/auth_cli.py --login for browser OAuth'"
    - failure: "OS Keyring unavailable (headless Linux or permission denied)"
      detection: "keyring.errors.KeyringError during credential retrieval"
      recovery: "Fallback gracefully to local AES-256 encrypted file vault (data/.vault.enc) using user master password"
  handoff:
    - "IAuthService implemented and verified."
    - "Secure credential vault configured (OS Keyring / Encrypted Vault)."
    - "Ready for Phase 02 database schema and DuckDB engine initialization."
```

---

## 1. Goal & Scope
Establish a production-grade, secure configuration layer and an automated authentication manager for the Fyers API v3 adhering to the 00A Canonical Registry.

This phase delivers:
- Typed environment configuration using Pydantic Settings (`config/settings.py`) with strict validation for Fyers App IDs, paths, and runtime constants.
- A dedicated Authentication Service implementing the canonical `IAuthService` interface.
- Complete lifecycle management of Fyers access tokens (valid daily until ~06:00 AM IST) and refresh tokens (valid for 15 calendar days).
- Secure credential management: user PIN and refresh tokens are stored in the OS Keyring (`keyring` package) or an AES-256 encrypted vault file (`data/.vault.enc`). **Plaintext storage in `.env` is strictly prohibited.**
- Pre-flight automated session probe at 15:40 IST prior to post-market sync, plus proactive 15-day re-login reminders and UI countdown timers.

---

## 2. SOLID Principles Application
- **Single Responsibility Principle (SRP)**:
  - `Settings`: Responsible solely for parsing, typing, and validating environment variables.
  - `AuthService`: Responsible solely for OAuth URL generation, auth-code exchange, refresh token renewal, and credential vault persistence.
  - `TokenValidator`: Responsible solely for probing Fyers profile endpoints to verify live session viability.
- **Open/Closed Principle (OCP)**:
  - Credential storage supports multiple interchangeable backends (`OSKeyringStorage`, `EncryptedFileStorage`) via an internal `ICredentialVault` interface without altering core authentication flows.
- **Dependency Inversion Principle (DIP)**:
  - Downstream modules (Downloader, Scheduler, FastAPI routes) depend exclusively on the abstract interface `IAuthService`.

---

## 3. Configuration Specification (`config/settings.py`)
All application settings are declared using Pydantic Settings (`BaseSettings`) mapped to `.env`:

### 3.1. Settings Model
```python
from pydantic import BaseSettings, Field, SecretStr, validator
from typing import List

class Settings(BaseSettings):
    # Fyers API Credentials
    FYERS_APP_ID: str = Field(..., description="Format: {ALPHANUM}-{TYPE} e.g. 2Q10WHDO67-100")
    FYERS_SECRET_KEY: SecretStr = Field(..., description="Secret key from Fyers developer portal")
    FYERS_REDIRECT_URI: str = Field("https://127.0.0.1:5000/", description="Registered OAuth redirect URI")
    
    # Credential Storage Backend
    AUTH_CREDENTIAL_STORAGE: str = Field("KEYRING", description="'KEYRING' or 'ENCRYPTED_FILE'")
    
    # Database and Local Storage
    DUCKDB_PATH: str = Field("data/market_data.duckdb", description="Path to embedded DuckDB database")
    EXPORT_DIR: str = Field("data/exports", description="Scratch folder for file exports")
    
    # Global RateGovernor Policy
    RATE_GOVERNOR_BURST_PER_SEC: int = Field(10, description="Burst ceiling (Fyers hard cap: 10/s)")
    RATE_GOVERNOR_TARGET_PER_MIN: int = Field(180, description="Sustained rate target (Fyers cap: 200/min)")
    RATE_GOVERNOR_DAILY_CAP: int = Field(90000, description="Daily request soft cap (Fyers cap: 100,000/day)")
    
    # Application Logistics
    LOG_LEVEL: str = Field("INFO", description="DEBUG, INFO, WARNING, ERROR")
    UVICORN_WORKERS: int = Field(1, const=True, description="Strictly 1 worker for single-process DuckDB")

    @validator("FYERS_APP_ID")
    def validate_app_id_format(cls, v: str) -> str:
        if "-" not in v or len(v.split("-")) != 2:
            raise ValueError("FYERS_APP_ID must follow format {APP_ID}-{APP_TYPE} (e.g. 'ABCD1234EF-100')")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
```

---

## 4. Fyers v3 Authentication Architecture

### 4.1. Dual-Token Lifecycle in the Indian Market
1. **Access Token (`access_token`)**:
   - Issued upon successful authorization.
   - Valid until **~06:00 AM IST** of the following calendar day.
   - Required in the HTTP `Authorization` header (`Authorization: {FYERS_APP_ID}:{access_token}`) for all API calls.
2. **Refresh Token (`refresh_token`)**:
   - Generated simultaneously during initial login.
   - Valid for **15 calendar days**.
   - **Static Lifecycle**: Calling the refresh endpoint renews the *access token*, but does NOT extend the *refresh token*. After 15 days, a full interactive re-login is mandatory.

### 4.2. Daily Automated Renewal Flow
Between 06:00 AM and 15:40 IST (or triggered at pre-flight check):
1. `AuthService.refresh_token_if_needed()` reads `refresh_token` and user `pin` from the secure vault.
2. Computes `appIdHash`: SHA-256 hash of `(FYERS_APP_ID + ":" + FYERS_SECRET_KEY.get_secret_value())`.
3. Dispatches POST request to `https://api-t1.fyers.in/api/v3/validate-refresh-token`:
   ```json
   {
     "grant_type": "refresh_token",
     "appIdHash": "<sha256_hash>",
     "refresh_token": "<stored_refresh_token>",
     "pin": "<stored_user_pin>"
   }
   ```
4. If response returns a fresh `access_token`:
   - Store new `access_token` in secure memory/vault with `expires_at = tomorrow 06:00:00 IST`.
   - Log info: `"Fyers access token renewed successfully via refresh token."`
5. If response fails (e.g. 15 days elapsed or invalid PIN):
   - Set internal status to `AUTH_EXPIRED`.
   - Dispatch user alert: `"Fyers session expired. Please re-authenticate via UI or 'python scripts/auth_cli.py --login'"`

### 4.3. Pre-Flight Check Protocol (15:40 IST)
At 15:40 IST (5 minutes prior to the 15:45 IST post-market sync):
- Scheduler calls `IAuthService.validate_session()`.
- Probes `fyers.get_profile()`.
- If valid: confirms readiness for daily sync.
- If invalid: attempts `refresh_token_if_needed()`. If refresh fails, transitions scheduler to `FAILED_AUTH` and halts ingestion gracefully without spamming error logs.

---

## 5. Interface Contract (`core/interfaces.py`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass(frozen=True)
class AuthToken:
    access_token: str
    refresh_token: Optional[str]
    access_token_expires_at: datetime
    refresh_token_expires_at: Optional[datetime]

class IAuthService(ABC):
    @abstractmethod
    def get_auth_url(self) -> str:
        """Constructs OAuth login URL with client_id, redirect_uri, and state."""
        pass

    @abstractmethod
    def exchange_code_for_token(self, auth_code: str, pin: str) -> AuthToken:
        """Exchanges authorization code for access and refresh tokens; stores PIN in secure vault."""
        pass

    @abstractmethod
    def get_valid_token(self) -> str:
        """Returns cached access token. Refreshes if expired. Raises AuthenticationExpiredError if re-auth required."""
        pass

    @abstractmethod
    def refresh_token_if_needed(self) -> bool:
        """Uses stored refresh token and PIN to acquire fresh access token."""
        pass

    @abstractmethod
    def validate_session(self) -> bool:
        """Pings Fyers API profile endpoint to verify live token viability."""
        pass

    @abstractmethod
    def get_token_status(self) -> dict:
        """Returns metadata: is_valid, access_expiry, refresh_days_remaining."""
        pass
```

---

## 6. Implementation Steps
1. Create `config/settings.py` implementing Pydantic `BaseSettings` with secret masking.
2. Create `.env.example` containing dummy template keys (`FYERS_APP_ID=YOUR_APP_ID-100`).
3. Create `core/exceptions.py` defining:
   - `AuthenticationExpiredError`
   - `ConfigurationError`
   - `FyersAPIError`
   - `RateLimitExceededError`
4. Implement secure credential storage (`services/vault.py`):
   - Primary: `OSKeyringVault` utilizing `keyring` library.
   - Secondary: `EncryptedFileVault` utilizing `cryptography.fernet`.
5. Implement `services/auth_service.py` satisfying `IAuthService`.
6. Implement CLI utility `scripts/auth_cli.py`:
   - `--login`: Opens browser for OAuth, captures auth code, prompts for PIN, saves credentials.
   - `--status`: Displays active token viability, access token countdown, and refresh token days remaining.
   - `--refresh`: Force manual token renewal.

---

## 7. Verification & Acceptance Criteria
- Pydantic validation rejects malformed `FYERS_APP_ID` (missing hyphen or type suffix).
- Running `python scripts/auth_cli.py --status` displays:
  `Status: Active | Access Token Expires In: 08h 12m | Refresh Token Valid: 11 days remaining`.
- Automated test simulates an expired access token: `refresh_token_if_needed()` successfully generates a fresh access token without prompting for user login.
- Simulated 15-day refresh token expiration cleanly raises `AuthenticationExpiredError` with remediation instructions; zero raw 401 exceptions unhandled.
- Security audit: No secret keys, PINs, or raw access tokens appear in stdout, log files, or `.env`.
