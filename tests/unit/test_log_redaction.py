"""Unit tests for structured logging and sensitive secret redaction.
Adheres strictly to Phase 19 test plan.
"""

import logging
from core.logging_config import RedactingFormatter, redact_text


def test_redact_fyers_app_id():
    raw = "Connecting to Fyers API with app_id 2Q10WHDO67-100 on lane 1"
    redacted = redact_text(raw)
    assert "2Q10WHDO67-100" not in redacted
    assert "[REDACTED_SECRET]" in redacted


def test_redact_numeric_pin():
    raw = "User entered pin: 1234 and mpin: 987654 for 2FA"
    redacted = redact_text(raw)
    assert "1234" not in redacted
    assert "987654" not in redacted
    assert "[REDACTED_SECRET]" in redacted


def test_redact_jwt_token():
    dummy_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4ifQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    raw = f"Received access token: {dummy_jwt}"
    redacted = redact_text(raw)
    assert dummy_jwt not in redacted
    assert "[REDACTED_SECRET]" in redacted


def test_redact_bearer_token():
    raw = "Authorization: Bearer my_super_secret_bearer_token_123456789"
    redacted = redact_text(raw)
    assert "my_super_secret_bearer_token_123456789" not in redacted
    assert "[REDACTED_SECRET]" in redacted


def test_redact_labeled_secrets():
    raw = "fyers_secret_key: 'my_production_app_secret_value_12345'"
    redacted = redact_text(raw)
    assert "my_production_app_secret_value_12345" not in redacted
    assert "[REDACTED_SECRET]" in redacted


def test_redacting_formatter_record():
    formatter = RedactingFormatter(fmt="%(levelname)s: %(message)s")
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Authenticated user with AppID: 2Q10WHDO67-100 and PIN: 4321",
        args=(),
        exc_info=None,
    )
    output = formatter.format(record)
    assert "2Q10WHDO67-100" not in output
    assert "4321" not in output
    assert "[REDACTED_SECRET]" in output


def test_preserve_non_sensitive_data():
    raw = "Processed 500 candles for RELIANCE at price 2845.50 on 2026-10-10"
    redacted = redact_text(raw)
    assert redacted == raw
