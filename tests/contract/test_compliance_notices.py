"""Contract tests for SEBI legal notices, export licensing, and compliance rule interfaces.
Adheres strictly to Phase 19 test plan and EXECUTION_CONTRACT.
"""

import json
from pathlib import Path
from core.security import get_legal_notices, ComplianceNoticeManager
from core.interfaces import IComplianceRule


def test_legal_notices_file_exists_and_valid():
    notices_file = Path("config/legal_notices.json")
    assert notices_file.exists(), "config/legal_notices.json must exist"
    
    data = json.loads(notices_file.read_text(encoding="utf-8"))
    
    # Required top-level keys
    required_keys = [
        "sebi_disclaimer",
        "short_disclaimer",
        "fyers_license",
        "survivorship_bias_warning",
        "order_execution_notice",
        "export_metadata",
    ]
    for key in required_keys:
        assert key in data, f"Missing required legal notice key: {key}"


def test_sebi_disclaimer_mandatory_text_content():
    notices = get_legal_notices()
    disclaimer = notices["sebi_disclaimer"]

    # Statutory SEBI clauses
    assert "educational and research purposes only" in disclaimer
    assert "NOT constitute investment advice" in disclaimer
    assert "SEBI regulations" in disclaimer
    assert "substantial market risk" in disclaimer
    assert "consult a SEBI-registered financial advisor" in disclaimer


def test_fyers_eula_licensing_notice_content():
    notices = get_legal_notices()
    license_text = notices["fyers_license"]

    assert "Personal Non-Commercial" in license_text
    assert "Redistribution or commercial resale is prohibited" in license_text
    assert "Fyers API" in license_text


def test_export_metadata_schema_contract():
    notices = get_legal_notices()
    export_meta = notices["export_metadata"]

    assert export_meta["source"] == "Fyers API"
    assert export_meta["license"] == "Personal Non-Commercial"
    assert "disclaimer" in export_meta
    assert "survivorship_disclosure" in export_meta


def test_compliance_notice_manager_implements_interface():
    manager = ComplianceNoticeManager()
    all_notices = manager.get_all_notices()

    assert "SEBI_STATUTORY_DISCLAIMER" in all_notices
    assert "FYERS_PERSONAL_LICENSE" in all_notices
    assert "ORDER_EXECUTION_HARD_GATE" in all_notices

    # Context validation
    valid_context = {
        "disclaimer": "SEBI educational tool",
        "license": "Personal Non-Commercial",
        "action": "view_backtest",
    }
    assert manager.validate_context(valid_context) is True

    # Order execution action context must fail validation
    order_context = {
        "disclaimer": "SEBI educational tool",
        "license": "Personal Non-Commercial",
        "action": "place_order",
    }
    assert manager.validate_context(order_context) is False
