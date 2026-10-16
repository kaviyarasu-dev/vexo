"""Unit tests for config/settings.py."""

import pytest
from pydantic import ValidationError
from config.settings import Settings, get_settings, clear_settings_cache


def test_settings_loads_with_secret_masked():
    """Verify get_settings loads cleanly and masks FYERS_SECRET_KEY in string representation."""
    clear_settings_cache()
    settings = get_settings()
    assert settings.FYERS_APP_ID is not None
    assert "***" in str(settings.FYERS_SECRET_KEY)
    assert settings.FYERS_SECRET_KEY.get_secret_value() != ""


def test_fyers_app_id_validation():
    """Verify FYERS_APP_ID validation rejects formats without hyphen or invalid parts."""
    # Valid App ID
    s = Settings(FYERS_APP_ID="2Q10WHDO67-100")
    assert s.FYERS_APP_ID == "2Q10WHDO67-100"

    # Missing hyphen
    with pytest.raises(ValidationError):
        Settings(FYERS_APP_ID="INVALIDAPPID")

    # Too many hyphens
    with pytest.raises(ValidationError):
        Settings(FYERS_APP_ID="PART1-PART2-PART3")


def test_credential_storage_validation():
    """Verify AUTH_CREDENTIAL_STORAGE accepts only KEYRING or ENCRYPTED_FILE."""
    s1 = Settings(AUTH_CREDENTIAL_STORAGE="KEYRING")
    assert s1.AUTH_CREDENTIAL_STORAGE == "KEYRING"

    s2 = Settings(AUTH_CREDENTIAL_STORAGE="ENCRYPTED_FILE")
    assert s2.AUTH_CREDENTIAL_STORAGE == "ENCRYPTED_FILE"

    with pytest.raises(ValidationError):
        Settings(AUTH_CREDENTIAL_STORAGE="PLAINTEXT")


def test_uvicorn_workers_must_be_strictly_one():
    """Verify UVICORN_WORKERS must strictly be 1 for single-process DuckDB."""
    s = Settings(UVICORN_WORKERS=1)
    assert s.UVICORN_WORKERS == 1

    with pytest.raises(ValidationError):
        Settings(UVICORN_WORKERS=4)


def test_rate_governor_defaults():
    """Verify RateGovernor default configurations match Fyers API v3 specifications."""
    s = Settings()
    assert s.RATE_GOVERNOR_BURST_PER_SEC == 10
    assert s.RATE_GOVERNOR_TARGET_PER_MIN == 180
    assert s.RATE_GOVERNOR_DAILY_CAP == 90000


def test_historical_depth_defaults():
    """Verify default backfill targets match quant requirements."""
    s = Settings()
    assert s.DEFAULT_1M_HISTORY_YEARS == 5
    assert s.DEFAULT_1D_HISTORY_YEARS == 15
