"""Institutional Compliance, Safe Exports, and Order Execution Hard Gate.
Adheres strictly to Phase 19: Regulatory Compliance, Security Auditing & Safe Exports.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Union, Optional
try:
    from starlette.exceptions import HTTPException
    from starlette.requests import Request
    from starlette.responses import Response, JSONResponse
    from starlette.middleware.base import BaseHTTPMiddleware
except ImportError:
    class HTTPException(Exception):
        def __init__(self, status_code: int = 500, detail: str = ""):
            self.status_code = status_code
            self.detail = detail
            super().__init__(detail)

    class Request:
        pass

    class Response:
        pass

    class JSONResponse:
        def __init__(self, status_code: int = 200, content: Any = None):
            self.status_code = status_code
            self.content = content

    class BaseHTTPMiddleware:
        def __init__(self, app=None):
            self.app = app

try:
    from fastapi.routing import APIRouter
except ImportError:
    class APIRouter:
        def __init__(self, *args, **kwargs):
            pass

        def api_route(self, *args, **kwargs):
            return lambda fn: fn

from core.interfaces import IComplianceRule

logger = logging.getLogger(__name__)

# Default legal notices fallback in case config file is missing
DEFAULT_LEGAL_NOTICES = {
    "sebi_disclaimer": (
        "DISCLAIMER: This application is a self-directed quantitative data analysis and backtesting "
        "tool for educational and research purposes only. It does NOT constitute investment advice, "
        "financial advisory, or a recommendation to buy or sell any securities under SEBI regulations. \n\n"
        "All indicators, backtest results, and screener outputs are purely mathematical computations "
        "based on historical data. Historical performance is NOT indicative of future returns. "
        "Algorithmic trading and equity investments are subject to substantial market risk, including the loss of principal capital. \n\n"
        "Users are solely responsible for their independent investment decisions and should consult a "
        "SEBI-registered financial advisor before committing capital to financial markets."
    ),
    "short_disclaimer": "DISCLAIMER: For educational and research purposes only. Does not constitute investment advice under SEBI regulations.",
    "fyers_license": "License: Personal Non-Commercial Use Only. Redistribution or commercial resale is prohibited under Fyers API Terms of Service.",
    "survivorship_bias_warning": "WARNING: This backtest is subject to survivorship bias. Historical analysis may exclude delisted or merged securities. Results may not be indicative of future performance.",
    "order_execution_notice": "Order execution is strictly out of scope. Automated order routing is disabled in compliance with SEBI retail algorithmic trading regulations.",
    "export_metadata": {
        "source": "Fyers API",
        "license": "Personal Non-Commercial",
        "license_detail": "License: Personal Non-Commercial Use Only. Redistribution or commercial resale is prohibited under Fyers API Terms of Service.",
        "disclaimer": "DISCLAIMER: For educational and research purposes only. Does not constitute investment advice under SEBI regulations.",
        "survivorship_disclosure": "Data and calculations are based on historical data and subject to survivorship and lookahead considerations.",
    },
}


def get_legal_notices() -> Dict[str, Any]:
    """Load canonical legal notices from config/legal_notices.json."""
    config_path = Path("config/legal_notices.json")
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load legal notices from {config_path}: {e}")
    return DEFAULT_LEGAL_NOTICES


def get_export_metadata() -> Dict[str, str]:
    """Retrieve standard export metadata dictionary."""
    notices = get_legal_notices()
    return notices.get("export_metadata", DEFAULT_LEGAL_NOTICES["export_metadata"])


def verify_export_metadata(metadata_or_path: Union[Dict[str, Any], str, Path]) -> bool:
    """Verify that export metadata or file contains required personal non-commercial license and disclaimers.
    
    Accepts:
        - Dict[str, Any]: Metadata key-value dictionary.
        - str or Path: Filepath to an exported .parquet, .csv, or .xlsx file.
    
    Returns:
        bool: True if metadata satisfies compliance requirements, False otherwise.
    """
    if isinstance(metadata_or_path, dict):
        license_val = metadata_or_path.get("license") or metadata_or_path.get("License") or ""
        if not isinstance(license_val, str):
            return False
        
        # Verify personal non-commercial license
        has_license = "personal" in license_val.lower() and "non-commercial" in license_val.lower()
        if not has_license:
            return False
            
        # If source is explicitly provided, verify
        source_val = metadata_or_path.get("source") or metadata_or_path.get("Source")
        if source_val and not isinstance(source_val, str):
            return False
            
        return True

    # Handle file path validation
    file_path = Path(metadata_or_path)
    if not file_path.exists() or not file_path.is_file():
        return False

    suffix = file_path.suffix.lower()

    if suffix == ".parquet":
        try:
            import pyarrow.parquet as pq
            with pq.ParquetFile(str(file_path)) as parquet_file:
                schema = parquet_file.schema_arrow
                meta = schema.metadata or {}
                # Metadata keys and values are bytes in pyarrow
                found_license = False
                for k, v in meta.items():
                    k_str = k.decode("utf-8", errors="ignore").lower()
                    v_str = v.decode("utf-8", errors="ignore").lower()
                    if "license" in k_str or "personal non-commercial" in v_str:
                        if "personal" in v_str and "non-commercial" in v_str:
                            found_license = True
                            break
            return found_license
        except Exception as e:
            logger.error(f"Error inspecting parquet file metadata: {e}")
            return False

    elif suffix == ".csv":
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                header_lines = [f.readline() for _ in range(15)]
            combined = "\n".join(header_lines).lower()
            return "personal non-commercial" in combined
        except Exception as e:
            logger.error(f"Error inspecting csv file metadata: {e}")
            return False

    elif suffix in (".xlsx", ".excel"):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(file_path), read_only=True)
            desc = (wb.properties.description or "").lower()
            keywords = (wb.properties.keywords or "").lower()
            comments = (wb.properties.category or "").lower()
            combined = f"{desc} {keywords} {comments}"
            wb.close()
            return "personal non-commercial" in combined
        except Exception as e:
            logger.error(f"Error inspecting excel file metadata: {e}")
            return False

    return False


def attach_export_metadata_to_file(filepath: str, format_type: str) -> None:
    """Embed mandatory Fyers personal non-commercial license and SEBI disclaimers into export files."""
    file_path = Path(filepath)
    if not file_path.exists():
        return

    metadata = get_export_metadata()
    format_type = format_type.lower()

    if format_type == "parquet":
        try:
            import pyarrow.parquet as pq
            table = pq.read_table(str(file_path))
            existing_meta = table.schema.metadata or {}
            new_meta = {
                **existing_meta,
                b"source": metadata.get("source", "Fyers API").encode("utf-8"),
                b"license": metadata.get("license", "Personal Non-Commercial").encode("utf-8"),
                b"license_detail": metadata.get("license_detail", "").encode("utf-8"),
                b"disclaimer": metadata.get("disclaimer", "").encode("utf-8"),
                b"survivorship_disclosure": metadata.get("survivorship_disclosure", "").encode("utf-8"),
            }
            table_with_meta = table.replace_schema_metadata(new_meta)
            pq.write_table(table_with_meta, str(file_path))
        except Exception as e:
            logger.error(f"Failed to embed metadata in parquet file: {e}")

    elif format_type == "csv":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            disclaimer_header = (
                f"# Source: {metadata.get('source', 'Fyers API')}\n"
                f"# License: {metadata.get('license', 'Personal Non-Commercial')} - {metadata.get('license_detail', '')}\n"
                f"# {metadata.get('disclaimer', '')}\n"
                f"# {metadata.get('survivorship_disclosure', '')}\n"
            )
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(disclaimer_header + content)
        except Exception as e:
            logger.error(f"Failed to embed metadata in csv file: {e}")

    elif format_type in ("excel", "xlsx"):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(file_path))
            wb.properties.description = metadata.get("license_detail", "License: Personal Non-Commercial Use Only.")
            wb.properties.keywords = "Fyers API; Personal Non-Commercial; SEBI Research Tool"
            wb.properties.category = metadata.get("disclaimer", "")
            wb.save(str(file_path))
        except Exception as e:
            logger.error(f"Failed to embed metadata in excel file: {e}")


# ==============================================================================
# SEBI Retail Algorithmic Trading Framework: Architectural Hard Gate
# ==============================================================================

class OrderExecutionBlockedException(HTTPException):
    """Raised when an automated order execution attempt is intercepted."""
    def __init__(self, detail: str = "Order execution is out of scope."):
        super().__init__(status_code=403, detail=detail)


def order_execution_hard_gate(*args, **kwargs):
    """Hard gate function that strictly forbids order execution and always halts with HTTP 403."""
    raise OrderExecutionBlockedException()


class OrderExecutionGateMiddleware(BaseHTTPMiddleware):
    """Middleware that intercepts all order-routing HTTP requests and returns 403 Forbidden."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path.lower()
        
        # Intercept order execution endpoints
        order_patterns = [
            "/api/v1/orders",
            "/api/v1/order",
            "/api/orders",
            "/api/order",
            "/orders",
            "/order",
            "/place_order",
            "/trade/order",
        ]
        
        is_order_route = any(
            path == pattern or path.startswith(f"{pattern}/")
            for pattern in order_patterns
        )
        
        if is_order_route:
            logger.warning(
                f"Blocked unauthorized order routing attempt on path: {request.url.path} from {request.client.host if request.client else 'unknown'}"
            )
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "error": {
                        "code": "ORDER_EXECUTION_OUT_OF_SCOPE",
                        "message": "Order execution is out of scope.",
                    },
                    "detail": "Order execution is out of scope.",
                },
            )

        return await call_next(request)


# APIRouter hard gate for documentation / explicit route interception
order_gate_router = APIRouter(tags=["Order Gate (Disabled)"])

@order_gate_router.api_route(
    "/api/v1/orders{rest_of_path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    include_in_schema=False,
)
@order_gate_router.api_route(
    "/api/v1/order{rest_of_path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    include_in_schema=False,
)
@order_gate_router.api_route(
    "/orders{rest_of_path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    include_in_schema=False,
)
async def catch_and_block_order_requests(rest_of_path: str = ""):
    raise OrderExecutionBlockedException()


# ==============================================================================
# SOLID Compliance Rules Implementation
# ==============================================================================

class SEBIDisclaimerRule(IComplianceRule):
    def rule_id(self) -> str:
        return "SEBI_STATUTORY_DISCLAIMER"

    def validate(self, context: Dict[str, Any]) -> bool:
        return "sebi_disclaimer" in context or "disclaimer" in context

    def get_notice(self) -> str:
        return get_legal_notices()["sebi_disclaimer"]


class FyersLicenseRule(IComplianceRule):
    def rule_id(self) -> str:
        return "FYERS_PERSONAL_LICENSE"

    def validate(self, context: Dict[str, Any]) -> bool:
        return verify_export_metadata(context)

    def get_notice(self) -> str:
        return get_legal_notices()["fyers_license"]


class OrderExecutionHardGateRule(IComplianceRule):
    def rule_id(self) -> str:
        return "ORDER_EXECUTION_HARD_GATE"

    def validate(self, context: Dict[str, Any]) -> bool:
        # If context attempts order execution, validation fails
        if context.get("action") in ("place_order", "route_order", "execute_trade"):
            return False
        return True

    def get_notice(self) -> str:
        return get_legal_notices()["order_execution_notice"]


class ComplianceNoticeManager:
    """Manages regulatory compliance rules and notice injection."""

    def __init__(self):
        self._rules: Dict[str, IComplianceRule] = {
            "sebi": SEBIDisclaimerRule(),
            "fyers_license": FyersLicenseRule(),
            "order_gate": OrderExecutionHardGateRule(),
        }

    def register_rule(self, rule: IComplianceRule) -> None:
        self._rules[rule.rule_id()] = rule

    def get_rule(self, rule_id: str) -> Optional[IComplianceRule]:
        return self._rules.get(rule_id)

    def validate_context(self, context: Dict[str, Any]) -> bool:
        return all(rule.validate(context) for rule in self._rules.values())

    def get_all_notices(self) -> Dict[str, str]:
        return {r.rule_id(): r.get_notice() for r in self._rules.values()}
