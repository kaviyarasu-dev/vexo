from fastapi import APIRouter
from api.models.envelope import ApiResponse
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/api/v1/health")
def health_check():
    # As per 00A table: {"status": "healthy", "duckdb_connected": true, "auth_valid": true}
    from db.connection import get_db
    from services.auth_service import AuthService

    try:
        db = get_db()
        cursor = db.get_read_cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        db_connected = True
    except Exception:
        db_connected = False

    auth_valid = False
    try:
        auth_service = AuthService()
        token_status = auth_service.get_token_status()
        auth_valid = bool(token_status.get("is_valid", False))
    except Exception as exc:
        logger.debug("Auth status check in health endpoint: %s", exc)
        auth_valid = False

    status = "healthy" if (db_connected and auth_valid) else ("degraded" if db_connected else "unhealthy")

    data = {
        "status": status,
        "duckdb_connected": db_connected,
        "auth_valid": auth_valid
    }
    return ApiResponse.success_response(data=data, correlation_id="req-health-001")

@router.get("/ready")
def ready_check():
    return ApiResponse.success_response(data={"status": "ready"}, correlation_id="req-ready-001")
