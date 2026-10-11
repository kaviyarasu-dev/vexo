from fastapi import APIRouter, Depends, HTTPException
from typing import Any, List, Optional
from pydantic import BaseModel
from db.connection import get_db, DuckDBConnectionManager
from services.screener_service import ScreenerService
from core.interfaces import ScreenerFilter

router = APIRouter(prefix="/api/v1/screener", tags=["screener"])

class ScreenerRuleModel(BaseModel):
    field: str
    operator: str
    value: float

class ScreenerFilterModel(BaseModel):
    universe: str = "ALL"
    template: Optional[str] = None
    as_of_date: Optional[str] = None
    technical_rules: Optional[List[ScreenerRuleModel]] = None
    min_turnover_cr: float = 0.0

class CreateTemplateModel(BaseModel):
    name: str
    description: Optional[str] = ""
    universe: Optional[str] = "ALL"
    conditions: List[ScreenerRuleModel]

@router.get("/templates")
def get_templates(db: DuckDBConnectionManager = Depends(get_db)):
    service = ScreenerService(db)
    return {"success": True, "data": service.list_presets(), "error": None}

@router.post("/templates")
def create_template(template_data: CreateTemplateModel, db: DuckDBConnectionManager = Depends(get_db)):
    if not template_data.name.strip():
        raise HTTPException(status_code=400, detail="Template name cannot be empty")
    if not template_data.conditions:
        raise HTTPException(status_code=400, detail="At least one screening condition is required")
        
    service = ScreenerService(db)
    result = service.create_custom_template(
        name=template_data.name,
        description=template_data.description or "",
        universe=template_data.universe or "ALL",
        conditions=[r.model_dump() for r in template_data.conditions]
    )
    return {"success": True, "data": result, "error": None}

@router.delete("/templates/{template_id}")
def delete_template(template_id: str, db: DuckDBConnectionManager = Depends(get_db)):
    service = ScreenerService(db)
    success = service.delete_custom_template(template_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot delete template (either not found or system default)")
    return {"success": True, "message": f"Template {template_id} deleted successfully", "error": None}

@router.post("/run")
def run_screener(request: ScreenerFilterModel, db: DuckDBConnectionManager = Depends(get_db)):
    service = ScreenerService(db)
    rules_dicts = [rule.model_dump() for rule in request.technical_rules] if request.technical_rules else []
    
    filter_params = ScreenerFilter(
        universe=request.universe,
        as_of_date=request.as_of_date,
        technical_rules=rules_dicts,
        min_turnover_cr=request.min_turnover_cr
    )
    
    results = service.run_screener(filter_params, template=request.template)
    
    # Convert to dict for JSON serialization
    results_dicts = [
        {
            "symbol": r.symbol,
            "name": r.name,
            "category": r.category,
            "close": r.close,
            "turnover_cr": r.turnover_cr,
            "matched_rules": r.matched_rules,
            "as_of_date": r.as_of_date
        }
        for r in results
    ]
    
    return {
        "success": True,
        "data": results_dicts,
        "disclaimer": "DISCLAIMER: For educational and research purposes only. Does not constitute investment advice under SEBI regulations.",
        "sebi_disclaimer": "DISCLAIMER: This application is a self-directed quantitative data analysis and backtesting tool for educational and research purposes only. It does NOT constitute investment advice, financial advisory, or a recommendation to buy or sell any securities under SEBI regulations.",
        "error": None,
    }
