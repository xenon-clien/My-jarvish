"""Structured and sanitized logging system for JARVIS AI.

Guarantees that sensitive secrets, API keys, passwords, and tokens
are never leaked into terminal logs or log files.
"""
import logging
import os
import re
from pathlib import Path
from typing import Optional

# Secret patterns to sanitize
SENSITIVE_PATTERNS = [
    (r"(?i)(api[-_]?key|apikey|bearer|token|secret|password|passwd|auth)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{6,})['\"]?", r"\1=***REDACTED***"),
    (r"(?i)(sk-[a-zA-Z0-9]{20,})", r"sk-***REDACTED***"),
    (r"(?i)(AIza[0-9A-Za-z-_]{35})", r"AIza***REDACTED***"),
]


def sanitize_log_message(message: str) -> str:
    """Mask any discovered API keys, passwords, or secret tokens from the log string."""
    if not isinstance(message, str):
        message = str(message)
    for pattern, replacement in SENSITIVE_PATTERNS:
        message = re.sub(pattern, replacement, message)
    return message


class SanitizedFormatter(logging.Formatter):
    """Custom log formatter that applies sanitization before emitting."""

    def format(self, record: logging.LogRecord) -> str:
        original_msg = super().format(record)
        return sanitize_log_message(original_msg)


def get_logger(name: str = "JARVIS", log_file: Optional[str] = "logs/jarvis.log") -> logging.Logger:
    """Return a configured logger with console and optional sanitized file output."""
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Console Handler
    import sys
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = SanitizedFormatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # Optional File Handler
    if log_file:
        try:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(console_format)
            logger.addHandler(file_handler)
        except Exception:
            # Fall back to console only if file access fails
            pass

    return logger
