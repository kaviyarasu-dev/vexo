from fastapi import APIRouter, Query, Request
from typing import Optional, List
from api.models.envelope import ApiResponse
from api.models.symbol_models import SymbolSummary
from db.repositories.duckdb_symbol_repo import DuckDBSymbolRepo

router = APIRouter()

@router.get("/api/v1/symbols/popular", response_model=ApiResponse[List[SymbolSummary]])
def get_popular_symbols(
    request: Request,
    limit: int = Query(10, ge=1, le=50)
):
    correlation_id = getattr(request.state, "correlation_id", "req-symbols-popular")
    repo = DuckDBSymbolRepo()
    cursor = repo.db.get_read_cursor()
    try:
        sql = """
            SELECT symbol, name, isin, exchange, segment, series,
                   lot_size, tick_size, category, tier, priority_rank,
                   listing_date, is_active, updated_at
            FROM symbols
            WHERE is_active = TRUE
            ORDER BY tier ASC, priority_rank ASC, symbol ASC
            LIMIT ?;
        """
        rows = cursor.execute(sql, [limit]).fetchall()
        summaries = [
            SymbolSummary(
                symbol=r[0],
                name=r[1],
                lot_size=r[6] if r[6] is not None else 1,
                category=r[8],
                tier=r[9] if r[9] is not None else 4,
                priority_rank=r[10] if r[10] is not None else 9999,
                is_active=bool(r[12]) if r[12] is not None else True
            )
            for r in rows
        ]
        return ApiResponse.success_response(data=summaries, correlation_id=correlation_id)
    finally:
        cursor.close()


@router.get("/api/v1/symbols/search", response_model=ApiResponse[List[SymbolSummary]])
def search_symbols(
    request: Request,
    query: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100)
):
    correlation_id = getattr(request.state, "correlation_id", "req-symbols-search")
    repo = DuckDBSymbolRepo()
    clean_query = query.strip() if query else ""

    if not clean_query:
        cursor = repo.db.get_read_cursor()
        try:
            sql = """
                SELECT symbol, name, isin, exchange, segment, series,
                       lot_size, tick_size, category, tier, priority_rank,
                       listing_date, is_active, updated_at
                FROM symbols
                WHERE is_active = TRUE
                ORDER BY tier ASC, priority_rank ASC, symbol ASC
                LIMIT ?;
            """
            rows = cursor.execute(sql, [limit]).fetchall()
            summaries = [
                SymbolSummary(
                    symbol=r[0],
                    name=r[1],
                    lot_size=r[6],
                    category=r[8],
                    tier=r[9],
                    priority_rank=r[10],
                    is_active=r[12]
                )
                for r in rows
            ]
            return ApiResponse.success_response(data=summaries, correlation_id=correlation_id)
        finally:
            cursor.close()

    results = repo.search_symbols(query=clean_query, category=category, limit=limit)
    
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
