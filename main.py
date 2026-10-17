import time
import uuid
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from contextlib import asynccontextmanager
from core.logging_config import RedactingFormatter
from core.security import OrderExecutionGateMiddleware, order_gate_router
from api.routers import health, symbols, candles, export, system, screener, alerts, options, journal, backtest, auth, studies, volume_profile, patterns, paper_trading, chart_drawings, predictions, orderblock
from api.models.envelope import ApiResponse
from db.connection import DuckDBConnectionManager, get_db
from services.orderblock.tick_recorder import get_tick_recorder

import contextvars
correlation_id_var = contextvars.ContextVar("correlation_id", default="SYSTEM")

class CorrelationIdFilter(logging.Filter):
    def filter(self, record):
        record.correlation_id = correlation_id_var.get()
        return True

# Configure structured logging with RedactingFormatter
handler = logging.StreamHandler()
handler.setFormatter(RedactingFormatter("%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s"))
handler.addFilter(CorrelationIdFilter())

logging.getLogger().setLevel(logging.INFO)
logging.getLogger().handlers = [handler]

logger = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure DuckDB is initialized and launch tick recorder daemon
    db = get_db()
    db.get_read_cursor().close()
    recorder = get_tick_recorder(db_manager=db)
    await recorder.start()
    yield
    # Shutdown: stop tick recorder and release database connection
    await recorder.stop()
    db = get_db()
    db.close()


app = FastAPI(title="NSE Quant Platform API", version="1.0.0", lifespan=lifespan)

# Institutional Compliance: Order Execution Hard Gate Middleware
app.add_middleware(OrderExecutionGateMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_correlation_id_and_timing(request: Request, call_next):
    correlation_id = f"req-{uuid.uuid4().hex[:8]}"
    request.state.correlation_id = correlation_id
    token = correlation_id_var.set(correlation_id)

    start_time = time.time()
    try:
        response = await call_next(request)
        execution_time_ms = (time.time() - start_time) * 1000
        return response
    finally:
        correlation_id_var.reset(token)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    correlation_id = getattr(request.state, "correlation_id", "req-unknown")
    
    # Handle the specific Excel limit detail structure
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        code = exc.detail["code"]
        message = exc.detail["message"]
        details = exc.detail.get("details")
    else:
        code = "HTTP_ERROR"
        message = str(exc.detail)
        details = {"status_code": exc.status_code}
        
    envelope = ApiResponse.error_response(
        code=code,
        message=message,
        correlation_id=correlation_id,
        details=details
    )
    return JSONResponse(status_code=exc.status_code, content=envelope.model_dump())

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    correlation_id = getattr(request.state, "correlation_id", "req-unknown")
    envelope = ApiResponse.error_response(
        code="VALIDATION_ERROR",
        message="Request validation failed",
        correlation_id=correlation_id,
        details={"errors": exc.errors()}
    )
    return JSONResponse(status_code=422, content=envelope.model_dump())

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    correlation_id = getattr(request.state, "correlation_id", "req-unknown")
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    envelope = ApiResponse.error_response(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred.",
        correlation_id=correlation_id
    )
    return JSONResponse(status_code=500, content=envelope.model_dump())
app.include_router(health.router)
app.include_router(symbols.router)
app.include_router(candles.router)
app.include_router(export.router)
app.include_router(system.router)
app.include_router(screener.router)
app.include_router(alerts.router)
app.include_router(options.router)
app.include_router(journal.router)
app.include_router(backtest.router)
app.include_router(auth.router)
app.include_router(volume_profile.router)
app.include_router(patterns.router)
app.include_router(studies.router)
app.include_router(paper_trading.router)
app.include_router(chart_drawings.router)
app.include_router(predictions.router)
app.include_router(orderblock.router)
app.include_router(order_gate_router)

import os
from fastapi import Response

# Mount static files
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/config/glossary.json", include_in_schema=False)
async def serve_config_glossary():
    if os.path.exists("config/glossary.json"):
        return FileResponse("config/glossary.json", media_type="application/json")
    return JSONResponse(status_code=404, content={"error": "Not found"})

@app.get("/data/glossary.json", include_in_schema=False)
async def serve_data_glossary():
    if os.path.exists("data/glossary.json"):
        return FileResponse("data/glossary.json", media_type="application/json")
    return JSONResponse(status_code=404, content={"error": "Not found"})

@app.get("/favicon.ico", include_in_schema=False)
async def serve_favicon():
    return Response(status_code=204)

@app.get("/", include_in_schema=False)
async def serve_spa():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    # MUST use workers=1 for DuckDB
    uvicorn.run("main:app", host="0.0.0.0", port=8000, workers=1, reload=False)
