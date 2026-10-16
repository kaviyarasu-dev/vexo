from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime

class CreateAlertRequest(BaseModel):
    symbol: str = Field(..., description="The symbol for the alert (e.g. NSE:RELIANCE-EQ)")
    rule_type: str = Field(..., description="The rule type, e.g., PRICE_CROSS")
    condition_params: Dict[str, Any] = Field(..., description="Parameters for the condition")
    channel: str = Field(default="IN_APP", description="Notification channel: IN_APP, EMAIL, TELEGRAM")

class AlertRuleResponse(BaseModel):
    alert_id: str
    symbol: str
    rule_type: str
    condition_params: Dict[str, Any]
    channel: str
    is_active: bool
    last_triggered_at: Optional[datetime] = None

class CreateAlertResponse(BaseModel):
    alert_id: str
