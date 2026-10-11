"""Integration tests for AuthService with EncryptedFileVault and token renewal flows."""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch
import pytest

from config.settings import Settings
from core.exceptions import AuthenticationExpiredError
from services.auth_service import AuthService
from services.vault import EncryptedFileVault


@pytest.fixture
def temp_vault_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / ".vault.enc"
        salt_path = Path(tmpdir) / ".vault.salt"
        vault = EncryptedFileVault(
            vault_path=vault_path,
            salt_path=salt_path,
            master_password="test_master_password",
        )
        yield vault, vault_path


def test_auth_service_with_encrypted_file_vault(temp_vault_files):
    """Test full storage, retrieval, and encryption verification with EncryptedFileVault."""
    vault, vault_path = temp_vault_files
    settings = Settings(AUTH_CREDENTIAL_STORAGE="ENCRYPTED_FILE")
    auth_service = AuthService(settings=settings, vault=vault)

    now_utc = datetime.now(timezone.utc)
    access_exp = now_utc + timedelta(hours=8)
    refresh_exp = now_utc + timedelta(days=12)

    # Store credentials
    vault.set_secret("fyers_access_token", "secret_access_xyz")
    vault.set_secret("fyers_access_expires_at", access_exp.isoformat())
    vault.set_secret("fyers_refresh_token", "secret_refresh_abc")
    vault.set_secret("fyers_refresh_expires_at", refresh_exp.isoformat())
    vault.set_secret("fyers_pin", "9876")

    # Ensure vault file on disk is encrypted (does not contain plaintext tokens)
    encrypted_bytes = vault_path.read_bytes()
    assert b"secret_access_xyz" not in encrypted_bytes
    assert b"9876" not in encrypted_bytes

    # Retrieve valid token
    assert auth_service.get_valid_token() == "secret_access_xyz"

    status = auth_service.get_token_status()
    assert status["is_valid"] is True
    assert status["refresh_days_remaining"] == 12
    assert status["is_near_expiry"] is False


def test_preflight_check_with_automated_refresh(temp_vault_files):
    """Test 15:40 IST pre-flight check when access token is expired and needs renewal."""
    vault, _ = temp_vault_files
    settings = Settings(AUTH_CREDENTIAL_STORAGE="ENCRYPTED_FILE")
    auth_service = AuthService(settings=settings, vault=vault)

    now_utc = datetime.now(timezone.utc)
    # Expired access token, valid refresh token
    vault.set_secret("fyers_access_token", "old_expired_token")
    vault.set_secret("fyers_access_expires_at", (now_utc - timedelta(minutes=10)).isoformat())
    vault.set_secret("fyers_refresh_token", "valid_refresh_token")
    vault.set_secret("fyers_refresh_expires_at", (now_utc + timedelta(days=5)).isoformat())
    vault.set_secret("fyers_pin", "4321")

    # Mock response for refresh-token and profile probe
    refresh_response = {
        "s": "ok",
        "code": 200,
        "access_token": "fresh_access_token_999",
    }
    profile_response = {
        "s": "ok",
        "code": 200,
        "data": {"name": "Test User"},
    }

    def mock_urlopen(req, timeout=10):
        url = req.full_url if hasattr(req, "full_url") else req.get_full_url()
        mock = MagicMock()
        mock.__enter__.return_value = mock
        if "validate-refresh-token" in url:
            mock.read.return_value = json.dumps(refresh_response).encode("utf-8")
        elif "profile" in url:
            mock.read.return_value = json.dumps(profile_response).encode("utf-8")
        return mock

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        assert auth_service.preflight_session_check() is True

    # Check updated token in vault
    assert vault.get_secret("fyers_access_token") == "fresh_access_token_999"


def test_logout_purges_vault(temp_vault_files):
    """Test logout clears all tokens and secrets from the vault."""
    vault, _ = temp_vault_files
    auth_service = AuthService(vault=vault)

    vault.set_secret("fyers_access_token", "some_token")
    vault.set_secret("fyers_pin", "1111")
    assert vault.has_secret("fyers_access_token") is True

    auth_service.logout()
    assert vault.has_secret("fyers_access_token") is False
    assert vault.has_secret("fyers_pin") is False
