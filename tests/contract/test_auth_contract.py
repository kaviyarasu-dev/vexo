"""Contract tests for IAuthService interface implementation.
Validates get_auth_url, exchange_code_for_token, and validate_session adherence.
"""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from core.interfaces import AuthToken, IAuthService
from core.exceptions import AuthenticationExpiredError
from services.auth_service import AuthService
from services.vault import ICredentialVault


class InMemoryVault(ICredentialVault):
    """In-memory vault implementation for isolated testing."""

    def __init__(self) -> None:
        self.store = {}

    def get_secret(self, key: str):
        return self.store.get(key)

    def set_secret(self, key: str, value: str) -> None:
        self.store[key] = value

    def delete_secret(self, key: str) -> None:
        self.store.pop(key, None)

    def has_secret(self, key: str) -> bool:
        return key in self.store


@pytest.fixture
def memory_vault():
    return InMemoryVault()


@pytest.fixture
def auth_service(memory_vault):
    return AuthService(vault=memory_vault)


def test_iauth_service_subclass_check(auth_service):
    """Verify AuthService is a valid concrete implementation of IAuthService."""
    assert isinstance(auth_service, IAuthService)


def test_get_auth_url_contract(auth_service):
    """Verify get_auth_url returns a valid OAuth URL matching Fyers parameters."""
    url = auth_service.get_auth_url()
    assert "https://api-t1.fyers.in/api/v3/generate-authcode" in url
    assert "client_id=" in url
    assert "redirect_uri=" in url
    assert "response_type=code" in url


def test_exchange_code_for_token_contract(auth_service, memory_vault):
    """Verify exchange_code_for_token exchanges auth code and securely stores credentials."""
    mock_response_data = {
        "s": "ok",
        "code": 200,
        "message": "Authorization Successful",
        "access_token": "test_access_token_12345",
        "refresh_token": "test_refresh_token_67890",
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        token = auth_service.exchange_code_for_token(auth_code="dummy_auth_code", pin="1234")

        assert isinstance(token, AuthToken)
        assert token.access_token == "test_access_token_12345"
        assert token.refresh_token == "test_refresh_token_67890"
        assert token.access_token_expires_at > datetime.now(timezone.utc)
        assert token.refresh_token_expires_at is not None

        # Verify vault persistence
        assert memory_vault.get_secret("fyers_access_token") == "test_access_token_12345"
        assert memory_vault.get_secret("fyers_refresh_token") == "test_refresh_token_67890"
        assert memory_vault.get_secret("fyers_pin") == "1234"


def test_validate_session_contract(auth_service, memory_vault):
    """Verify validate_session probes profile endpoint and asserts viability."""
    fixture_path = Path("tests/fixtures/mock_fyers_profile.json")
    profile_data = fixture_path.read_text(encoding="utf-8")

    # Seed vault with valid token
    memory_vault.set_secret("fyers_access_token", "valid_access_token")
    exp = datetime.now(timezone.utc) + timedelta(hours=4)
    memory_vault.set_secret("fyers_access_expires_at", exp.isoformat())

    mock_resp = MagicMock()
    mock_resp.read.return_value = profile_data.encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        assert auth_service.validate_session() is True


def test_validate_session_failure(auth_service, memory_vault):
    """Verify validate_session handles HTTP failures safely by returning False."""
    memory_vault.set_secret("fyers_access_token", "invalid_token")
    exp = datetime.now(timezone.utc) + timedelta(hours=1)
    memory_vault.set_secret("fyers_access_expires_at", exp.isoformat())

    import urllib.error
    with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
        url="https://api-t1.fyers.in/api/v3/profile",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=MagicMock(read=lambda: b'{"s": "error", "code": 401}'),
    )):
        assert auth_service.validate_session() is False


def test_refresh_token_expiration_raises_error(auth_service, memory_vault):
    """Verify expired 15-day refresh token raises AuthenticationExpiredError."""
    # Seed vault with expired refresh token (> 15 days ago)
    expired_dt = datetime.now(timezone.utc) - timedelta(days=1)
    memory_vault.set_secret("fyers_access_token", "expired_token")
    memory_vault.set_secret("fyers_access_expires_at", (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat())
    memory_vault.set_secret("fyers_refresh_token", "old_refresh_token")
    memory_vault.set_secret("fyers_pin", "1234")
    memory_vault.set_secret("fyers_refresh_expires_at", expired_dt.isoformat())

    with pytest.raises(AuthenticationExpiredError) as exc_info:
        auth_service.refresh_token_if_needed()

    assert "15-day refresh window expired" in str(exc_info.value)


def test_token_status_countdown_under_48_hours(auth_service, memory_vault):
    """Verify countdown timer activates when refresh token is within 48 hours of expiry."""
    now_utc = datetime.now(timezone.utc)
    near_expiry_dt = now_utc + timedelta(hours=36, minutes=15, seconds=30)

    memory_vault.set_secret("fyers_access_token", "active_access_token")
    memory_vault.set_secret("fyers_access_expires_at", (now_utc + timedelta(hours=6)).isoformat())
    memory_vault.set_secret("fyers_refresh_token", "refresh_token")
    memory_vault.set_secret("fyers_refresh_expires_at", near_expiry_dt.isoformat())

    status = auth_service.get_token_status()
    assert status["is_valid"] is True
    assert status["is_refresh_valid"] is True
    assert status["is_near_expiry"] is True
    assert status["countdown_timer"] is not None
    assert "36h 15m" in status["countdown_timer"]
