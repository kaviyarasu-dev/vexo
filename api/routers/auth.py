from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from api.models.envelope import ApiResponse
from services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/status")
def get_auth_status(request: Request, probe: bool = True):
    """Returns current Fyers session status (CONNECTED, EXPIRED, DISCONNECTED)."""
    correlation_id = getattr(request.state, "correlation_id", "req-auth-status")
    service = AuthService()
    status = service.get_token_status()
    
    auth_status = "DISCONNECTED"
    message = "No Fyers access token configured."
    is_live_verified = False

    access_token = service.vault.get_secret("fyers_access_token")
    if access_token:
        if status.get("is_valid"):
            if probe:
                is_live_verified = service.validate_session()
                if is_live_verified:
                    auth_status = "CONNECTED"
                    message = "Fyers session is active and verified."
                else:
                    auth_status = "EXPIRED"
                    message = "Fyers access token was rejected by broker API."
            else:
                auth_status = "CONNECTED"
                message = "Fyers access token active."
        else:
            auth_status = "EXPIRED"
            message = "Fyers access token has expired."

    payload = {
        "auth_status": auth_status,
        "is_authenticated": (auth_status == "CONNECTED"),
        "is_live_verified": is_live_verified,
        "token_expires_at": status.get("access_token_expires_at"),
        "days_remaining_refresh": status.get("refresh_days_remaining"),
        "countdown": status.get("access_token_countdown"),
        "has_refresh_token": status.get("has_refresh_token"),
        "is_near_expiry": status.get("is_near_expiry"),
        "message": message,
    }
    return ApiResponse.success_response(data=payload, correlation_id=correlation_id)


import urllib.parse
from typing import Optional
from pydantic import BaseModel, Field

class TokenUpdateDto(BaseModel):
    access_token: Optional[str] = Field(None, description="Fresh Fyers API v3 access token or raw auth code")
    token: Optional[str] = Field(None, description="Alias for access_token, auth_code, or full redirect URL")
    auth_code: Optional[str] = Field(None, description="Direct Fyers authorization code")

    def get_raw_input(self) -> str:
        val = self.token or self.auth_code or self.access_token or ""
        return val.strip()


def extract_auth_code_from_input(raw: str) -> tuple[str, bool]:
    """Inspects input string. If it's a URL or contains 'auth_code=' or 'code=',
    extracts the auth code parameter.
    Returns (cleaned_string, is_explicit_code).
    """
    s = raw.strip()
    if not s:
        return "", False

    if "auth_code=" in s or "code=" in s or s.startswith("http://") or s.startswith("https://") or "?" in s:
        try:
            query_str = s
            if "?" in s:
                query_str = s.split("?", 1)[1]
            if "#" in query_str:
                query_str = query_str.split("#", 1)[0]

            qs = urllib.parse.parse_qs(query_str)
            if "auth_code" in qs and qs["auth_code"]:
                return qs["auth_code"][0].strip(), True
            if "code" in qs and qs["code"]:
                code_val = qs["code"][0].strip()
                if len(code_val) > 20:
                    return code_val, True
        except Exception:
            pass

    return s, False


@router.post("/refresh")
def refresh_token(request: Request, force_api: bool = False):
    """Attempts session verification or automated renewal of daily access token."""
    correlation_id = getattr(request.state, "correlation_id", "req-auth-refresh")
    service = AuthService()

    # 1. If not forcing raw API call, verify current live token first
    status = service.get_token_status()
    if not force_api and status["is_valid"]:
        is_live = service.validate_session()
        if is_live:
            payload = {
                "auth_status": "CONNECTED",
                "is_authenticated": True,
                "is_live_verified": True,
                "refreshed": False,
                "token_expires_at": status["access_token_expires_at"],
                "days_remaining_refresh": status["refresh_days_remaining"],
                "countdown": status["access_token_countdown"],
                "message": f"Token is 100% Fresh & Active! Live Fyers session verified (Expires in {status['access_token_countdown']}).",
            }
            return ApiResponse.success_response(data=payload, correlation_id=correlation_id)

    # 2. Token is expired or force_api requested: Attempt renewal via Fyers validate-refresh-token API
    try:
        refreshed = service.refresh_token_if_needed(force=True)
        status = service.get_token_status()
        is_live = service.validate_session()
        payload = {
            "auth_status": "CONNECTED" if is_live else "EXPIRED",
            "is_authenticated": is_live,
            "is_live_verified": is_live,
            "refreshed": refreshed,
            "token_expires_at": status["access_token_expires_at"],
            "days_remaining_refresh": status["refresh_days_remaining"],
            "countdown": status["access_token_countdown"],
            "message": "Token renewed successfully via Fyers API.",
        }
        return ApiResponse.success_response(data=payload, correlation_id=correlation_id)
    except Exception as exc:
        return ApiResponse.error_response(
            code="AUTH_REFRESH_FAILED",
            message=str(exc),
            correlation_id=correlation_id,
        )


@router.post("/token")
def update_access_token(payload: TokenUpdateDto, request: Request):
    """Sets and validates a fresh Fyers session using either an auth_code, redirect URL, or access token."""
    correlation_id = getattr(request.state, "correlation_id", "req-auth-token-update")
    raw_input = payload.get_raw_input()
    if not raw_input or len(raw_input) < 10:
        return ApiResponse.error_response(
            code="INVALID_INPUT",
            message="Please provide a valid Fyers access token, auth code, or redirect URL.",
            correlation_id=correlation_id,
        )

    code_or_token, is_explicit_code = extract_auth_code_from_input(raw_input)
    service = AuthService()
    exchange_error = None

    # Option A: If explicit code or long token string, attempt OAuth code exchange first
    if is_explicit_code or len(code_or_token) > 20:
        try:
            service.exchange_code_for_token(code_or_token)
            if service.validate_session():
                status = service.get_token_status()
                result_data = {
                    "auth_status": "CONNECTED",
                    "is_authenticated": True,
                    "token_expires_at": status["access_token_expires_at"],
                    "days_remaining_refresh": status["refresh_days_remaining"],
                    "countdown": status["access_token_countdown"],
                    "message": "Fyers authorization code exchanged and verified successfully!",
                }
                return ApiResponse.success_response(data=result_data, correlation_id=correlation_id)
        except Exception as exc:
            exchange_error = str(exc)

    # Option B: If not an explicit code from URL, attempt direct access token validation
    if not is_explicit_code:
        try:
            status = service.set_access_token(code_or_token)
            if service.validate_session():
                result_data = {
                    "auth_status": "CONNECTED",
                    "is_authenticated": True,
                    "token_expires_at": status["access_token_expires_at"],
                    "days_remaining_refresh": status["refresh_days_remaining"],
                    "countdown": status["access_token_countdown"],
                    "message": "Fyers access token activated and verified successfully!",
                }
                return ApiResponse.success_response(data=result_data, correlation_id=correlation_id)
        except Exception:
            pass

    # Option C: Rejection handling with specific error guidance
    err_msg = (
        "Authentication Failed: Fyers rejected the provided code or token. "
        "If you copied an Auth Code from browser login, please note that auth codes expire within 2-3 minutes "
        "and can only be used once. Please click 'Login via Fyers (OAuth)' to generate a fresh code."
    )
    if exchange_error and ("invalid auth code" in exchange_error.lower() or "expired" in exchange_error.lower()):
        err_msg = (
            "Authentication Failed: The authorization code was rejected by Fyers (it may be expired or already used). "
            "Please click 'Login via Fyers (OAuth)' to generate a fresh code."
        )

    return ApiResponse.error_response(
        code="INVALID_FYERS_TOKEN",
        message=err_msg,
        correlation_id=correlation_id,
    )


@router.get("/login")
def login_redirect():
    """Redirects user browser directly to Fyers OAuth authorization login URL."""
    service = AuthService()
    url = service.get_auth_url()
    return RedirectResponse(url=url, status_code=302)


@router.get("/callback")
def auth_callback(
    auth_code: Optional[str] = None,
    code: Optional[str] = None,
    s: Optional[str] = None,
):
    """OAuth callback endpoint for automatic token exchange if redirect URI is configured to hit the backend."""
    target_code = auth_code or (code if code and len(code) > 20 else None)
    if not target_code:
        return RedirectResponse(url="/?auth=error&msg=missing_code", status_code=302)

    service = AuthService()
    try:
        service.exchange_code_for_token(target_code)
        if service.validate_session():
            return RedirectResponse(url="/?auth=success", status_code=302)
        else:
            return RedirectResponse(url="/?auth=error&msg=validation_failed", status_code=302)
    except Exception as exc:
        encoded_err = urllib.parse.quote(str(exc))
        return RedirectResponse(url=f"/?auth=error&msg={encoded_err}", status_code=302)
