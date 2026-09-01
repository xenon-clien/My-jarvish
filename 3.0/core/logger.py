"""JARVIS 3.0 - Centralized Observability & Sanitized Logger.

Ensures that all operations, tool calls, and diagnostics are structured and
never leak API keys, tokens, or private credentials into logs or console.
"""
import logging
import re
import sys
from typing import Optional


class SanitizedFormatter(logging.Formatter):
    """Custom formatter that automatically scrubs sensitive credentials and tokens."""

    SECRET_PATTERNS = [
        re.compile(r"(AIzaSy[a-zA-Z0-9_\-]{30,})"),           # Google API Keys
        re.compile(r"(sk-[a-zA-Z0-9_\-]{20,})"),              # OpenAI/Generic secret keys
        re.compile(r"(bearer\s+[a-zA-Z0-9_\-\.]{20,})", re.I), # Bearer tokens
        re.compile(r"(password\s*[:=]\s*['\"][^'\"]+['\"])", re.I),
    ]

    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        for pat in self.SECRET_PATTERNS:
            formatted = pat.sub("[REDACTED_SECRET]", formatted)
        return formatted


def get_logger(name: str = "JARVIS", level: Optional[str] = None) -> logging.Logger:
    """Return a configured sanitized logger instance."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, (level or "INFO").upper(), logging.INFO))
    logger.propagate = False

    handler = logging.StreamHandler(sys.stdout)
    formatter = SanitizedFormatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
