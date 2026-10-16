from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List

from db.connection import get_db, DuckDBConnectionManager
from services.chart_drawing_service import ChartDrawingService
from api.models.drawing_models import (
    CreateDrawingRequest,
    UpdateDrawingRequest,
    DrawingResponse,
)

router = APIRouter(prefix="/api/v1/chart/drawings", tags=["Chart Drawings"])


def get_drawing_service(db: DuckDBConnectionManager = Depends(get_db)) -> ChartDrawingService:
    """Dependency provider for ChartDrawingService."""
    return ChartDrawingService(db)


@router.get("/{symbol}", response_model=Dict[str, Any])
def get_symbol_drawings(
    symbol: str,
    service: ChartDrawingService = Depends(get_drawing_service)
):
    """Retrieves all active technical drawings saved for a symbol."""
    try:
        drawings = service.get_drawings(symbol=symbol)
        return {
            "success": True,
            "symbol": symbol.strip().upper(),
            "data": [d.model_dump() for d in drawings],
            "count": len(drawings)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{symbol}", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_symbol_drawing(
    symbol: str,
    req: CreateDrawingRequest,
    service: ChartDrawingService = Depends(get_drawing_service)
):
    """Creates a new technical drawing annotation on a symbol chart."""
    try:
        drawing = service.create_drawing(
            symbol=symbol,
            tool_type=req.tool_type,
            points=req.points,
            style=req.style
        )
        return {
            "success": True,
            "message": "Drawing created successfully",
            "data": drawing.model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{drawing_id}", response_model=Dict[str, Any])
def update_drawing(
    drawing_id: str,
    req: UpdateDrawingRequest,
    service: ChartDrawingService = Depends(get_drawing_service)
):
    """Updates points or styling for an existing drawing."""
    try:
        updated = service.update_drawing(
            drawing_id=drawing_id,
            points=req.points,
            style=req.style
        )
        if not updated:
            raise HTTPException(status_code=404, detail=f"Drawing {drawing_id} not found")

        return {
            "success": True,
            "message": "Drawing updated successfully",
            "data": updated.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{symbol}/all", response_model=Dict[str, Any])
def clear_all_symbol_drawings(
    symbol: str,
    service: ChartDrawingService = Depends(get_drawing_service)
):
    """Clears all technical drawing annotations for a symbol."""
    try:
        cleared_count = service.clear_symbol_drawings(symbol=symbol)
        return {
            "success": True,
            "message": f"Cleared {cleared_count} drawings for {symbol}",
            "count": cleared_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{drawing_id}", response_model=Dict[str, Any])
def delete_drawing(
    drawing_id: str,
    service: ChartDrawingService = Depends(get_drawing_service)
):
    """Deletes a specific technical drawing annotation by ID."""
    try:
        deleted = service.delete_drawing(drawing_id=drawing_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Drawing {drawing_id} not found")

        return {
            "success": True,
            "message": f"Drawing {drawing_id} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
