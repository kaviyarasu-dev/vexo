from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from api.models.envelope import ApiResponse
from services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/status")
def get_auth_status(request: Request):
    """Returns current Fyers session status, countdown timers, and refresh window."""
    correlation_id = getattr(request.state, "correlation_id", "req-auth-status")
    service = AuthService()
    status = service.get_token_status()
    payload = {
        "is_authenticated": status["is_valid"],
        "token_expires_at": status["access_token_expires_at"],
        "days_remaining_refresh": status["refresh_days_remaining"],
        "countdown": status["access_token_countdown"],
        "has_refresh_token": status["has_refresh_token"],
        "is_near_expiry": status["is_near_expiry"],
    }
    return ApiResponse.success_response(data=payload, correlation_id=correlation_id)


from pydantic import BaseModel, Field

class TokenUpdateDto(BaseModel):
    access_token: str = Field(..., min_length=10, description="Fresh Fyers API v3 access token")


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
        payload = {
            "is_authenticated": status["is_valid"],
            "is_live_verified": True,
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
    """Directly sets and activates a fresh Fyers access token in secure vault."""
    correlation_id = getattr(request.state, "correlation_id", "req-auth-token-update")
    service = AuthService()
    try:
        status = service.set_access_token(payload.access_token)
        result_data = {
            "is_authenticated": status["is_valid"],
            "token_expires_at": status["access_token_expires_at"],
            "days_remaining_refresh": status["refresh_days_remaining"],
            "countdown": status["access_token_countdown"],
            "message": "Access token updated and activated successfully in vault.",
        }
        return ApiResponse.success_response(data=result_data, correlation_id=correlation_id)
    except Exception as exc:
        return ApiResponse.error_response(
            code="TOKEN_UPDATE_FAILED",
            message=str(exc),
            correlation_id=correlation_id,
        )


@router.post("/simulate-refresh")
def simulate_refresh(request: Request):
    """Extends session validity for developer/testing environments."""
    correlation_id = getattr(request.state, "correlation_id", "req-auth-sim-refresh")
    service = AuthService()
    status = service.simulate_token_refresh(hours=8.0)
    result_data = {
        "is_authenticated": status["is_valid"],
        "token_expires_at": status["access_token_expires_at"],
        "days_remaining_refresh": status["refresh_days_remaining"],
        "countdown": status["access_token_countdown"],
        "message": "Session simulated and extended by 8 hours.",
    }
    return ApiResponse.success_response(data=result_data, correlation_id=correlation_id)


@router.get("/login")
def login_redirect():
    """Redirects user browser directly to Fyers OAuth authorization login URL."""
    service = AuthService()
    url = service.get_auth_url()
    return RedirectResponse(url=url, status_code=302)
