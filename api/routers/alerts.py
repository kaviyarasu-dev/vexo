from fastapi import APIRouter, Depends
from typing import List, Any
from api.models.envelope import StandardResponse, success_response, error_response
from api.models.alert_models import CreateAlertRequest, AlertRuleResponse, CreateAlertResponse
from db.connection import get_db
from services.alert_service import AlertService

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])

def get_alert_service():
    # Factory for alert service, reusing the same DB connection manager
    db = get_db()
    return AlertService(db_manager=db)

@router.get("/status", response_model=StandardResponse[dict])
def get_alert_status(service: AlertService = Depends(get_alert_service)):
    from datetime import datetime, timezone, timedelta
    now_utc = datetime.now(timezone.utc)
    ist_time = now_utc + timedelta(hours=5, minutes=30)
    is_quiet = service.is_quiet_hours(ist_time.hour)
    alerts = service.list_alerts()
    active_count = sum(1 for a in alerts if a.is_active)
    
    return success_response(data={
        "is_quiet_hours": is_quiet,
        "ist_hour": ist_time.hour,
        "ist_time": ist_time.strftime("%H:%M:%S IST"),
        "active_count": active_count,
        "total_count": len(alerts),
        "status_message": "🌙 Quiet Hours Active (23:00 - 08:00 IST) — Overnight notifications paused" if is_quiet else "☀️ Active Hours — Real-time triggers operational"
    })

@router.get("", response_model=StandardResponse[List[AlertRuleResponse]])
def get_alerts(service: AlertService = Depends(get_alert_service)):
    alerts = service.list_alerts()
    return success_response(data=[
        AlertRuleResponse(
            alert_id=a.alert_id,
            symbol=a.symbol,
            rule_type=a.rule_type,
            condition_params=a.condition_params,
            channel=a.channel,
            is_active=a.is_active,
            last_triggered_at=a.last_triggered_at
        ) for a in alerts
    ])

@router.post("", response_model=StandardResponse[CreateAlertResponse])
def create_alert(request: CreateAlertRequest, service: AlertService = Depends(get_alert_service)):
    alert_id = service.create_alert(
        symbol=request.symbol,
        rule_type=request.rule_type,
        params=request.condition_params,
        channel=request.channel
    )
    return success_response(data=CreateAlertResponse(alert_id=alert_id))

@router.delete("/{alert_id}", response_model=StandardResponse[Any])
def delete_alert(alert_id: str, service: AlertService = Depends(get_alert_service)):
    success = service.delete_alert(alert_id)
    if success:
        return success_response(data={"deleted": True})
    return error_response(code="DELETE_FAILED", message="Failed to delete alert.")
