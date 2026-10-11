from fastapi import APIRouter
from api.models.envelope import ApiResponse
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/api/v1/health")
def health_check():
    # As per 00A table: {"status": "healthy", "duckdb_connected": true, "auth_valid": true}
    # For now returning a mock with correlation_id
    from db.connection import get_db
    try:
        db = get_db()
        cursor = db.get_read_cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        db_connected = True
    except Exception:
        db_connected = False

    data = {
        "status": "healthy" if db_connected else "degraded",
        "duckdb_connected": db_connected,
        "auth_valid": True  # mock for now
    }
    return ApiResponse.success_response(data=data, correlation_id="req-health-001")

@router.get("/ready")
def ready_check():
    return ApiResponse.success_response(data={"status": "ready"}, correlation_id="req-ready-001")
