from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class DrawingPoint(BaseModel):
    """Anchor coordinate on the chart: logical timestamp and price level."""
    time: Any
    price: float


class DrawingStyle(BaseModel):
    """Visual styling attributes for chart annotations."""
    color: str = "#2962FF"
    lineWidth: int = 2
    lineStyle: int = 0  # 0: Solid, 1: Dotted, 2: Dashed
    filled: bool = False
    fillColor: Optional[str] = None
    transparency: Optional[float] = 0.2


class CreateDrawingRequest(BaseModel):
    """Payload to register a new technical drawing on a symbol chart."""
    tool_type: str = Field(..., description="TRENDLINE, HORIZONTAL_RAY, FIBONACCI, POSITION_RR")
    points: List[DrawingPoint] = Field(..., min_length=1)
    style: Optional[DrawingStyle] = Field(default_factory=DrawingStyle)


class UpdateDrawingRequest(BaseModel):
    """Payload to modify points coordinates or styles for an existing drawing."""
    points: Optional[List[DrawingPoint]] = None
    style: Optional[DrawingStyle] = None


class DrawingResponse(BaseModel):
    """Standard serialized drawing representation returned by REST endpoints."""
    drawing_id: str
    symbol: str
    tool_type: str
    points: List[DrawingPoint]
    style: DrawingStyle
    created_at: str
    updated_at: str
