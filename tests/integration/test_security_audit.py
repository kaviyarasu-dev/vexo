"""Integration tests for repository security audit and order execution hard gate.
Adheres strictly to Phase 19 test plan.
"""

from pathlib import Path
from starlette.applications import Starlette
from starlette.testclient import TestClient
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from scripts.audit_security import (
    check_gitignore_compliance,
    scan_repository,
    verify_order_execution_hard_gate,
    WORKSPACE_ROOT,
)
from core.security import OrderExecutionGateMiddleware, OrderExecutionBlockedException


def test_gitignore_compliance_integration():
    violations = check_gitignore_compliance(WORKSPACE_ROOT)
    assert violations == [], f"Gitignore compliance violations found: {violations}"


def test_repository_secrets_scan_integration():
    violations = scan_repository(WORKSPACE_ROOT)
    assert violations == [], f"Plaintext secret violations detected in repository: {violations}"


def test_zero_order_execution_code_in_repo():
    violations = verify_order_execution_hard_gate(WORKSPACE_ROOT)
    assert violations == [], f"Order execution endpoints or calls detected: {violations}"


def test_order_execution_middleware_blocks_all_order_endpoints():
    async def dummy_endpoint(request):
        return PlainTextResponse("OK")

    app = Starlette(routes=[Route("/api/v1/market-data", dummy_endpoint)])
    app.add_middleware(OrderExecutionGateMiddleware)
    client = TestClient(app)

    # Allowed endpoint passes
    allowed = client.get("/api/v1/market-data")
    assert allowed.status_code == 200

    # Order routes are strictly blocked with HTTP 403
    blocked_endpoints = [
        "/api/v1/orders",
        "/api/v1/orders/123",
        "/api/v1/order",
        "/api/orders",
        "/orders",
        "/place_order",
        "/trade/order/execute",
    ]

    for endpoint in blocked_endpoints:
        res = client.post(endpoint, json={"symbol": "RELIANCE", "qty": 10})
        assert res.status_code == 403
        data = res.json()
        assert data["success"] is False
        assert "Order execution is out of scope." in data["detail"]
