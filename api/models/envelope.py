from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import time
import uuid

T = TypeVar("T")

class ErrorDetails(BaseModel):
    code: str
    message: str
    details: Optional[dict[str, Any]] = None

class MetaDetails(BaseModel):
    correlation_id: str
    timestamp: str
    execution_time_ms: Optional[float] = None

class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[ErrorDetails] = None
    meta: MetaDetails

    @classmethod
    def success_response(cls, data: T, correlation_id: str, execution_time_ms: float = 0.0) -> "ApiResponse[T]":
        return cls(
            success=True,
            data=data,
            error=None,
            meta=MetaDetails(
                correlation_id=correlation_id,
                timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                execution_time_ms=execution_time_ms
            )
        )

    @classmethod
    def error_response(cls, code: str, message: str, correlation_id: str, details: Optional[dict[str, Any]] = None) -> "ApiResponse[T]":
        return cls(
            success=False,
            data=None,
            error=ErrorDetails(code=code, message=message, details=details),
            meta=MetaDetails(
                correlation_id=correlation_id,
                timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )
        )

# Backward-compatibility aliases
StandardResponse = ApiResponse

def success_response(data: Any, correlation_id: str = "req-default", execution_time_ms: float = 0.0) -> ApiResponse[Any]:
    return ApiResponse.success_response(data=data, correlation_id=correlation_id, execution_time_ms=execution_time_ms)

def error_response(code: str, message: str, correlation_id: str = "req-default", details: Optional[dict[str, Any]] = None) -> ApiResponse[Any]:
    return ApiResponse.error_response(code=code, message=message, correlation_id=correlation_id, details=details)
