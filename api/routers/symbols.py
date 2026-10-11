from fastapi import APIRouter, Query, Request
from typing import Optional, List
from api.models.envelope import ApiResponse
from api.models.symbol_models import SymbolSummary
from db.repositories.duckdb_symbol_repo import DuckDBSymbolRepo

router = APIRouter()

@router.get("/api/v1/symbols/search", response_model=ApiResponse[List[SymbolSummary]])
def search_symbols(
    request: Request,
    query: str = Query(..., min_length=1),
    category: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100)
):
    correlation_id = getattr(request.state, "correlation_id", "req-symbols-search")
    repo = DuckDBSymbolRepo()
    results = repo.search_symbols(query=query, category=category, limit=limit)
    
    # Map SymbolEntity to SymbolSummary
    summaries = []
    for r in results:
        summaries.append(SymbolSummary(
            symbol=r.symbol,
            name=r.name,
            lot_size=r.lot_size,
            category=r.category,
            tier=r.tier,
            priority_rank=r.priority_rank,
            is_active=r.is_active
        ))
        
    return ApiResponse.success_response(data=summaries, correlation_id=correlation_id)
