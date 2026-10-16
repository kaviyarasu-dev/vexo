"""Structured Logging with Cryptographic Secret Redaction.
Adheres strictly to Phase 19: Regulatory Compliance, Security Auditing & Safe Exports.
"""

import re
import logging
from typing import Optional, List, Tuple


# Regex patterns and their replacement formats
REDACTION_RULES: List[Tuple[re.Pattern, str]] = [
    # 1. Fyers App ID / API key format: {ALPHANUM 8-15}-{DIGITS 2-4} e.g. 2Q10WHDO67-100
    (re.compile(r"\b[A-Za-z0-9]{8,15}-\d{2,4}\b"), "[REDACTED_SECRET]"),
    
    # 2. 4-to-6 digit numeric PINs / Passcodes / OTPs (preceded by pin/mpin/passcode)
    (
        re.compile(r"(?i)\b((?:pin|mpin|passcode|user_pin|otp)\s*[:=]?\s*['\"]?)\d{4,6}\b"),
        r"\g<1>[REDACTED_SECRET]",
    ),
    
    # 3. JWT Tokens (header.payload.signature)
    (
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
        "[REDACTED_SECRET]",
    ),
    
    # 4. Bearer tokens
    (
        re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9_\-\.+=/]{16,}\b"),
        r"\g<1>[REDACTED_SECRET]",
    ),
    
    # 5. Labeled secrets, passwords, access/refresh tokens
    (
        re.compile(
            r"(?i)\b((?:fyers_secret_key|secret_key|api_secret|secret|access_token|refresh_token|password|auth_token)\s*[:=]\s*['\"]?)[A-Za-z0-9_\-\.+=/]{8,}(['\"]?)"
        ),
        r"\g<1>[REDACTED_SECRET]\g<2>",
    ),
    
    # 6. Standalone 64-char hex strings if labeled as hash / appIdHash
    (
        re.compile(r"(?i)\b((?:appIdHash|hash|key)\s*[:=]\s*['\"]?)[a-fA-F0-9]{32,64}\b"),
        r"\g<1>[REDACTED_SECRET]",
    ),
]


def redact_text(text: str) -> str:
    """Scrub sensitive patterns (API keys, secrets, JWT tokens, 4-digit PINs) from text."""
    if not text:
        return text
    
    result = str(text)
    for pattern, replacement in REDACTION_RULES:
        result = pattern.sub(replacement, result)
    return result


class RedactingFormatter(logging.Formatter):
    """Logging Formatter that redacts API keys, secrets, tokens, and PINs from all logs."""

    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        style: str = "%",
        validate: bool = True,
    ):
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, validate=validate)

    def format(self, record: logging.LogRecord) -> str:
        # Obtain standard formatted string (including timestamp, level, msg, exc_info)
        formatted = super().format(record)
        # Scrub all sensitive credentials
        return redact_text(formatted)


def setup_logging(
    level: int = logging.INFO,
    format_str: Optional[str] = None,
) -> logging.Logger:
    """Configure root logging to use RedactingFormatter across all handlers."""
    if format_str is None:
        format_str = (
            "%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s"
            if "%(correlation_id)s" in (format_str or "")
            else "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    formatter = RedactingFormatter(fmt=format_str)
    
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    else:
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)
            
    return root_logger
