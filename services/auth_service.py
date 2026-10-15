"""Authentication service implementing canonical IAuthService for Fyers API v3.
Manages dual-token lifecycle (daily access token + 15-day refresh token),
secure credential vault integration, 48-hour expiration countdown timers,
and 15:40 IST pre-flight sync probes.
"""

from datetime import datetime, time, timedelta, timezone
import hashlib
import json
import logging
from typing import Any, Dict, Optional
import urllib.parse
import urllib.request
import urllib.error

from config.settings import Settings, get_settings
from config.constants import (
    FYERS_AUTH_CODE_URL,
    FYERS_VALIDATE_AUTH_URL,
    FYERS_REFRESH_TOKEN_URL,
    FYERS_PROFILE_URL,
)
from core.interfaces import AuthToken, IAuthService
from core.exceptions import AuthenticationExpiredError, FyersAPIError
from services.vault import ICredentialVault, get_credential_vault

logger = logging.getLogger(__name__)

# IST timezone definition (UTC + 05:30)
IST_TZ = timezone(timedelta(hours=5, minutes=30))

# Vault key identifiers
KEY_ACCESS_TOKEN = "fyers_access_token"
KEY_REFRESH_TOKEN = "fyers_refresh_token"
KEY_USER_PIN = "fyers_pin"
KEY_ACCESS_EXPIRES_AT = "fyers_access_expires_at"
KEY_REFRESH_EXPIRES_AT = "fyers_refresh_expires_at"
KEY_REFRESH_CREATED_AT = "fyers_refresh_created_at"


class AuthService(IAuthService):
    """Production implementation of IAuthService for Fyers API v3."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        vault: Optional[ICredentialVault] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.vault = vault or get_credential_vault(self.settings.AUTH_CREDENTIAL_STORAGE)

    def _get_app_id_hash(self) -> str:
        """Computes SHA-256 hash of appId:appSecret required by Fyers API v3."""
        secret = self.settings.FYERS_SECRET_KEY.get_secret_value()
        raw = f"{self.settings.FYERS_APP_ID}:{secret}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def calculate_access_token_expiry(current_time: Optional[datetime] = None) -> datetime:
        """Calculates Fyers access token expiry (~06:00:00 AM IST of next morning).
        If currently before 06:00:00 AM IST, expires today at 06:00:00 AM IST.
        If currently after 06:00:00 AM IST, expires tomorrow at 06:00:00 AM IST.
        """
        now = current_time or datetime.now(timezone.utc)
        ist_now = now.astimezone(IST_TZ)
        cutoff_today = ist_now.replace(hour=6, minute=0, second=0, microsecond=0)

        if ist_now < cutoff_today:
            expiry_ist = cutoff_today
        else:
            expiry_ist = cutoff_today + timedelta(days=1)
        return expiry_ist.astimezone(timezone.utc)

    @staticmethod
    def calculate_refresh_token_expiry(created_at: Optional[datetime] = None) -> datetime:
        """Calculates Fyers refresh token expiry (strictly 15 calendar days from creation)."""
        base = created_at or datetime.now(timezone.utc)
        return base + timedelta(days=15)

    def get_auth_url(self) -> str:
        """Constructs OAuth login URL with client_id, redirect_uri, and state."""
        params = {
            "client_id": self.settings.FYERS_APP_ID,
            "redirect_uri": self.settings.FYERS_REDIRECT_URI,
            "response_type": "code",
            "state": "quant_auth_state",
        }
        return f"{FYERS_AUTH_CODE_URL}?{urllib.parse.urlencode(params)}"

    def exchange_code_for_token(self, auth_code: str, pin: Optional[str] = None) -> AuthToken:
        """Exchanges authorization code for access and refresh tokens.
        Stores credentials, PIN, and expiry timestamps in the secure vault.
        """
        app_id_hash = self._get_app_id_hash()
        payload = {
            "grant_type": "authorization_code",
            "appIdHash": app_id_hash,
            "code": auth_code,
        }

        data_json = json.dumps(payload).encode("utf-8")
        
        req = urllib.request.Request(
            FYERS_VALIDATE_AUTH_URL,
            data=data_json,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "python-requests/2.31.0"
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            logger.error(f"Fyers auth code exchange failed: {exc.code} {err_body}")
            raise FyersAPIError(f"OAuth code exchange failed: {err_body}", status_code=exc.code) from exc
        except Exception as exc:
            logger.error(f"Network error during auth code exchange: {exc}")
            raise FyersAPIError(f"Network error during OAuth code exchange: {exc}") from exc

        if resp_data.get("s") != "ok":
            msg = resp_data.get("message", "Unknown error in auth code exchange")
            raise FyersAPIError(f"OAuth code exchange error: {msg}")

        access_token = resp_data.get("access_token")
        refresh_token = resp_data.get("refresh_token")

        if not access_token:
            raise FyersAPIError("Response did not contain an access_token")

        now_utc = datetime.now(timezone.utc)
        access_expires_at = self.calculate_access_token_expiry(now_utc)
        refresh_expires_at = self.calculate_refresh_token_expiry(now_utc) if refresh_token else None

        # Securely persist to vault
        self.vault.set_secret(KEY_ACCESS_TOKEN, access_token)
        self.vault.set_secret(KEY_ACCESS_EXPIRES_AT, access_expires_at.isoformat())

        if refresh_token:
            self.vault.set_secret(KEY_REFRESH_TOKEN, refresh_token)
            self.vault.set_secret(KEY_REFRESH_EXPIRES_AT, refresh_expires_at.isoformat())  # type: ignore[union-attr]
            self.vault.set_secret(KEY_REFRESH_CREATED_AT, now_utc.isoformat())

        if pin:
            self.vault.set_secret(KEY_USER_PIN, pin)

        logger.info("Fyers OAuth exchange succeeded. Credentials secured in vault.")
        return AuthToken(
            access_token=access_token,
            refresh_token=refresh_token,
            access_token_expires_at=access_expires_at,
            refresh_token_expires_at=refresh_expires_at,
        )

    def refresh_token_if_needed(self, force: bool = False) -> bool:
        """Uses stored refresh token and PIN to acquire fresh access token.
        Returns True if a fresh token was generated, False if current token is still valid.
        Raises AuthenticationExpiredError if refresh token expired (> 15 calendar days).
        """
        now_utc = datetime.now(timezone.utc)
        access_token = self.vault.get_secret(KEY_ACCESS_TOKEN)
        access_exp_str = self.vault.get_secret(KEY_ACCESS_EXPIRES_AT)

        if not force and access_token and access_exp_str:
            try:
                access_exp = datetime.fromisoformat(access_exp_str)
                # If valid for at least another 60 seconds, no refresh needed
                if access_exp > now_utc + timedelta(seconds=60):
                    return False
            except ValueError:
                pass

        # Refresh is needed
        refresh_token = self.vault.get_secret(KEY_REFRESH_TOKEN)
        pin = self.vault.get_secret(KEY_USER_PIN)
        refresh_exp_str = self.vault.get_secret(KEY_REFRESH_EXPIRES_AT)

        if not refresh_token or not pin:
            raise AuthenticationExpiredError(
                "Missing refresh token or PIN. Please log in via: python scripts/auth_cli.py --login"
            )

        if refresh_exp_str:
            try:
                refresh_exp = datetime.fromisoformat(refresh_exp_str)
                if now_utc >= refresh_exp:
                    raise AuthenticationExpiredError(
                        "15-day refresh window expired. Run python scripts/auth_cli.py --login for browser OAuth"
                    )
            except ValueError:
                pass

        app_id_hash = self._get_app_id_hash()
        payload = {
            "grant_type": "refresh_token",
            "appIdHash": app_id_hash,
            "refresh_token": refresh_token,
            "pin": pin,
        }

        data_json = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            FYERS_REFRESH_TOKEN_URL,
            data=data_json,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "python-requests/2.31.0"
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            logger.error(f"Refresh token request failed with HTTP {exc.code}: {err_body}")
            try:
                err_json = json.loads(err_body)
                err_msg = err_json.get("message", err_body)
            except Exception:
                err_msg = err_body
            raise AuthenticationExpiredError(
                f"Fyers renewal failed ({err_msg}). Run python scripts/auth_cli.py --login or update access token directly."
            ) from exc
        except Exception as exc:
            logger.error(f"Network error during refresh token request: {exc}")
            raise FyersAPIError(f"Network error refreshing token: {exc}") from exc

        if resp_data.get("s") != "ok":
            msg = resp_data.get("message", "Token renewal failed")
            raise AuthenticationExpiredError(
                f"15-day refresh window expired or renewal rejected ({msg}). Run python scripts/auth_cli.py --login for browser OAuth"
            )

        new_access_token = resp_data.get("access_token")
        if not new_access_token:
            raise AuthenticationExpiredError("Fyers response did not contain new access_token")

        new_expiry = self.calculate_access_token_expiry(now_utc)
        self.vault.set_secret(KEY_ACCESS_TOKEN, new_access_token)
        self.vault.set_secret(KEY_ACCESS_EXPIRES_AT, new_expiry.isoformat())

        logger.info("Fyers access token renewed successfully via refresh token.")
        return True

    def set_access_token(self, access_token: str, expires_in_hours: Optional[float] = None) -> Dict[str, Any]:
        """Directly persists an active access token to vault and computes expiry."""
        clean_token = access_token.strip()
        if clean_token.startswith(f"{self.settings.FYERS_APP_ID}:"):
            clean_token = clean_token[len(f"{self.settings.FYERS_APP_ID}:"):].strip()
        elif ":" in clean_token:
            prefix = clean_token.split(":", 1)[0]
            if prefix.endswith("-100") or prefix.endswith("-200") or len(prefix) <= 20:
                clean_token = clean_token.split(":", 1)[1].strip()

        now_utc = datetime.now(timezone.utc)
        if expires_in_hours:
            access_expires_at = now_utc + timedelta(hours=expires_in_hours)
        else:
            access_expires_at = self.calculate_access_token_expiry(now_utc)

        self.vault.set_secret(KEY_ACCESS_TOKEN, clean_token)
        self.vault.set_secret(KEY_ACCESS_EXPIRES_AT, access_expires_at.isoformat())
        logger.info("Access token updated successfully in secure vault.")
        return self.get_token_status()

    def get_valid_token(self) -> str:
        """Returns cached access token. Refreshes if expired.
        Raises AuthenticationExpiredError if re-authentication is required.
        """
        self.refresh_token_if_needed()
        token = self.vault.get_secret(KEY_ACCESS_TOKEN)
        if not token:
            raise AuthenticationExpiredError(
                "No valid access token found. Please run: python scripts/auth_cli.py --login"
            )
        return token

    def validate_session(self) -> bool:
        """Pings Fyers API profile endpoint to verify live token viability."""
        try:
            access_token = self.get_valid_token()
        except Exception as exc:
            logger.warning(f"Could not retrieve valid access token: {exc}")
            return False

        headers = {
            "Authorization": f"{self.settings.FYERS_APP_ID}:{access_token}",
            "User-Agent": "python-requests/2.31.0"
        }
        req = urllib.request.Request(
            FYERS_PROFILE_URL,
            headers=headers,
            method="GET",
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("s") == "ok"
        except urllib.error.HTTPError as exc:
            logger.warning(f"Profile probe failed with HTTP {exc.code}")
            return False
        except Exception as exc:
            logger.warning(f"Profile probe network error: {exc}")
            return False

    def preflight_session_check(self) -> bool:
        """Pre-flight check protocol designed to run at 15:40 IST prior to post-market sync.
        Probes session, attempts refresh if invalid, and returns readiness status.
        """
        logger.info("Running pre-flight authentication check at 15:40 IST.")
        if self.validate_session():
            logger.info("Pre-flight check: Live Fyers session is VALID.")
            return True

        logger.warning("Pre-flight check: Session invalid or expired. Attempting token refresh...")
        try:
            refreshed = self.refresh_token_if_needed()
            if refreshed and self.validate_session():
                logger.info("Pre-flight check: Token refresh succeeded and session verified.")
                return True
        except Exception as exc:
            logger.error(f"Pre-flight check failed during token refresh: {exc}")

        logger.error("Pre-flight check FAILED: Unable to establish valid Fyers session.")
        return False

    def get_token_status(self) -> Dict[str, Any]:
        """Returns metadata: is_valid, access_expiry, refresh_days_remaining, countdown timers.
        Displays countdown timer when 15-day refresh token is within 48 hours of expiry.
        """
        now_utc = datetime.now(timezone.utc)
        access_token = self.vault.get_secret(KEY_ACCESS_TOKEN)
        access_exp_str = self.vault.get_secret(KEY_ACCESS_EXPIRES_AT)
        refresh_token = self.vault.get_secret(KEY_REFRESH_TOKEN)
        refresh_exp_str = self.vault.get_secret(KEY_REFRESH_EXPIRES_AT)

        is_access_valid = False
        access_countdown = "Expired"
        access_exp_dt: Optional[datetime] = None

        if access_token and access_exp_str:
            try:
                access_exp_dt = datetime.fromisoformat(access_exp_str)
                diff = access_exp_dt - now_utc
                if diff.total_seconds() > 0:
                    is_access_valid = True
                    hrs = int(diff.total_seconds() // 3600)
                    mins = int((diff.total_seconds() % 3600) // 60)
                    access_countdown = f"{hrs:02d}h {mins:02d}m"
            except ValueError:
                pass

        is_refresh_valid = False
        refresh_days_remaining = 0
        refresh_countdown = "Expired"
        is_near_expiry = False
        refresh_timer_str: Optional[str] = None
        refresh_exp_dt: Optional[datetime] = None

        if refresh_token and refresh_exp_str:
            try:
                refresh_exp_dt = datetime.fromisoformat(refresh_exp_str)
                diff = refresh_exp_dt - now_utc
                if diff.total_seconds() > 0:
                    is_refresh_valid = True
                    refresh_days_remaining = round(diff.total_seconds() / 86400)
                    hrs_rem = int(diff.total_seconds() // 3600)
                    mins_rem = int((diff.total_seconds() % 3600) // 60)
                    secs_rem = int(diff.total_seconds() % 60)

                    # 48-Hour Threshold Check
                    if diff.total_seconds() <= 48 * 3600:
                        is_near_expiry = True
                        refresh_timer_str = f"{hrs_rem:02d}h {mins_rem:02d}m {secs_rem:02d}s"
                        refresh_countdown = f"{refresh_timer_str} (WARNING: < 48 hours remaining)"
                    else:
                        refresh_countdown = f"{refresh_days_remaining} days remaining"
            except ValueError:
                pass

        return {
            "is_valid": is_access_valid,
            "has_refresh_token": bool(refresh_token),
            "is_refresh_valid": is_refresh_valid,
            "access_token_expires_at": access_exp_dt.isoformat() if access_exp_dt else None,
            "access_token_countdown": access_countdown,
            "refresh_token_expires_at": refresh_exp_dt.isoformat() if refresh_exp_dt else None,
            "refresh_days_remaining": refresh_days_remaining,
            "refresh_token_countdown": refresh_countdown,
            "is_near_expiry": is_near_expiry,
            "countdown_timer": refresh_timer_str,
            "needs_relogin": not is_refresh_valid,
        }

    def logout(self) -> None:
        """Purges stored tokens and credentials from vault."""
        for key in (
            KEY_ACCESS_TOKEN,
            KEY_REFRESH_TOKEN,
            KEY_USER_PIN,
            KEY_ACCESS_EXPIRES_AT,
            KEY_REFRESH_EXPIRES_AT,
            KEY_REFRESH_CREATED_AT,
        ):
            self.vault.delete_secret(key)
        logger.info("Purged all stored credentials from vault.")
