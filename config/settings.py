"""Application configuration management using Pydantic Settings.
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md Section 6.
"""

from functools import lru_cache
from typing import List, Literal
from pydantic import Field, SecretStr

try:
    # Pydantic v2
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import field_validator

    class Settings(BaseSettings):
        """Typed application configuration with secret masking and validation."""

        # Fyers API Credentials
        FYERS_APP_ID: str = Field(
            default="SAMPLEAPPID-100",
            description="Format: {ALPHANUM}-{TYPE} e.g. 2Q10WHDO67-100",
        )
        FYERS_SECRET_KEY: SecretStr = Field(
            default=SecretStr("sample_secret_key_placeholder"),
            description="Secret key from Fyers developer portal. Never logged.",
        )
        FYERS_REDIRECT_URI: str = Field(
            default="https://127.0.0.1:5000/",
            description="Registered OAuth redirect URI",
        )

        # Credential Storage Backend
        AUTH_CREDENTIAL_STORAGE: str = Field(
            default="KEYRING",
            description="'KEYRING' (OS Keyring) or 'ENCRYPTED_FILE' (data/.vault.enc)",
        )

        # Database and Local Storage
        DUCKDB_PATH: str = Field(
            default="data/market_data.duckdb",
            description="Path to embedded DuckDB database",
        )
        EXPORT_DIR: str = Field(
            default="data/exports",
            description="Scratch folder for file exports",
        )

        # Global RateGovernor Policy
        RATE_GOVERNOR_BURST_PER_SEC: int = Field(
            default=10,
            description="Burst ceiling (Fyers hard cap: 10/s)",
        )
        RATE_GOVERNOR_TARGET_PER_MIN: int = Field(
            default=180,
            description="Sustained rate target (Fyers cap: 200/min)",
        )
        RATE_GOVERNOR_DAILY_CAP: int = Field(
            default=90000,
            description="Daily request soft cap (Fyers cap: 100,000/day)",
        )

        # Historical Ingestion Defaults
        DEFAULT_1M_HISTORY_YEARS: int = Field(
            default=5,
            description="Historical intraday target backfill depth",
        )
        DEFAULT_1D_HISTORY_YEARS: int = Field(
            default=15,
            description="Historical daily target backfill depth",
        )

        # Options Analytics
        RBI_RISK_FREE_RATE: float = Field(
            default=0.065,
            description="RBI 91-day T-bill yield for Black-Scholes",
        )

        # Application Logistics & Server
        CORS_ORIGINS: List[str] = Field(
            default=["http://localhost:8000", "http://127.0.0.1:8000"],
            description="Allowed CORS origins",
        )
        LOG_LEVEL: str = Field(
            default="INFO",
            description="DEBUG, INFO, WARNING, ERROR",
        )
        UVICORN_WORKERS: int = Field(
            default=1,
            description="Strictly 1 worker for single-process DuckDB",
        )

        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=True,
            extra="ignore",
        )

        @field_validator("FYERS_APP_ID")
        @classmethod
        def validate_app_id_format(cls, v: str) -> str:
            if not v or "-" not in v or len(v.split("-")) != 2:
                raise ValueError("FYERS_APP_ID must follow format {APP_ID}-{APP_TYPE} (e.g. 'ABCD1234EF-100')")
            return v

        @field_validator("AUTH_CREDENTIAL_STORAGE")
        @classmethod
        def validate_storage_backend(cls, v: str) -> str:
            v_upper = v.upper()
            if v_upper not in ("KEYRING", "ENCRYPTED_FILE"):
                raise ValueError("AUTH_CREDENTIAL_STORAGE must be 'KEYRING' or 'ENCRYPTED_FILE'")
            return v_upper

        @field_validator("LOG_LEVEL")
        @classmethod
        def validate_log_level(cls, v: str) -> str:
            v_upper = v.upper()
            if v_upper not in ("DEBUG", "INFO", "WARNING", "ERROR"):
                raise ValueError("LOG_LEVEL must be one of DEBUG, INFO, WARNING, ERROR")
            return v_upper

        @field_validator("UVICORN_WORKERS")
        @classmethod
        def validate_uvicorn_workers(cls, v: int) -> int:
            if v != 1:
                raise ValueError("UVICORN_WORKERS must strictly be 1 for single-process DuckDB")
            return v

except ImportError:
    # Pydantic v1 fallback
    from pydantic import BaseSettings, validator

    class Settings(BaseSettings):  # type: ignore[no-redef]
        """Typed application configuration with secret masking and validation."""

        # Fyers API Credentials
        FYERS_APP_ID: str = Field(
            default="SAMPLEAPPID-100",
            description="Format: {ALPHANUM}-{TYPE} e.g. 2Q10WHDO67-100",
        )
        FYERS_SECRET_KEY: SecretStr = Field(
            default=SecretStr("sample_secret_key_placeholder"),
            description="Secret key from Fyers developer portal. Never logged.",
        )
        FYERS_REDIRECT_URI: str = Field(
            default="https://127.0.0.1:5000/",
            description="Registered OAuth redirect URI",
        )

        # Credential Storage Backend
        AUTH_CREDENTIAL_STORAGE: str = Field(
            default="KEYRING",
            description="'KEYRING' (OS Keyring) or 'ENCRYPTED_FILE' (data/.vault.enc)",
        )

        # Database and Local Storage
        DUCKDB_PATH: str = Field(
            default="data/market_data.duckdb",
            description="Path to embedded DuckDB database",
        )
        EXPORT_DIR: str = Field(
            default="data/exports",
            description="Scratch folder for file exports",
        )

        # Global RateGovernor Policy
        RATE_GOVERNOR_BURST_PER_SEC: int = Field(
            default=10,
            description="Burst ceiling (Fyers hard cap: 10/s)",
        )
        RATE_GOVERNOR_TARGET_PER_MIN: int = Field(
            default=180,
            description="Sustained rate target (Fyers cap: 200/min)",
        )
        RATE_GOVERNOR_DAILY_CAP: int = Field(
            default=90000,
            description="Daily request soft cap (Fyers cap: 100,000/day)",
        )

        # Historical Ingestion Defaults
        DEFAULT_1M_HISTORY_YEARS: int = Field(
            default=5,
            description="Historical intraday target backfill depth",
        )
        DEFAULT_1D_HISTORY_YEARS: int = Field(
            default=15,
            description="Historical daily target backfill depth",
        )

        # Options Analytics
        RBI_RISK_FREE_RATE: float = Field(
            default=0.065,
            description="RBI 91-day T-bill yield for Black-Scholes",
        )

        # Application Logistics & Server
        CORS_ORIGINS: List[str] = Field(
            default=["http://localhost:8000", "http://127.0.0.1:8000"],
            description="Allowed CORS origins",
        )
        LOG_LEVEL: str = Field(
            default="INFO",
            description="DEBUG, INFO, WARNING, ERROR",
        )
        UVICORN_WORKERS: int = Field(
            default=1,
            description="Strictly 1 worker for single-process DuckDB",
        )

        @validator("FYERS_APP_ID")
        def validate_app_id_format(cls, v: str) -> str:
            if not v or "-" not in v or len(v.split("-")) != 2:
                raise ValueError("FYERS_APP_ID must follow format {APP_ID}-{APP_TYPE} (e.g. 'ABCD1234EF-100')")
            return v

        @validator("AUTH_CREDENTIAL_STORAGE")
        def validate_storage_backend(cls, v: str) -> str:
            v_upper = v.upper()
            if v_upper not in ("KEYRING", "ENCRYPTED_FILE"):
                raise ValueError("AUTH_CREDENTIAL_STORAGE must be 'KEYRING' or 'ENCRYPTED_FILE'")
            return v_upper

        @validator("LOG_LEVEL")
        def validate_log_level(cls, v: str) -> str:
            v_upper = v.upper()
            if v_upper not in ("DEBUG", "INFO", "WARNING", "ERROR"):
                raise ValueError("LOG_LEVEL must be one of DEBUG, INFO, WARNING, ERROR")
            return v_upper

        @validator("UVICORN_WORKERS")
        def validate_uvicorn_workers(cls, v: int) -> int:
            if v != 1:
                raise ValueError("UVICORN_WORKERS must strictly be 1 for single-process DuckDB")
            return v

        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            case_sensitive = True
            extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Singleton getter for application settings."""
    return Settings()


def clear_settings_cache() -> None:
    """Clear lru_cache for settings, primarily for tests."""
    get_settings.cache_clear()
