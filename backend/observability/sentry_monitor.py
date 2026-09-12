"""Sentry Runtime Error & Exception Boundary Monitor for JARVIS.

Captures uncaught exceptions, tool/adapter failures, API errors, and task timeouts
with strict automatic redaction of keys, passwords, and private tokens.
"""
from functools import wraps
import os
import re
from typing import Any, Callable, Dict, Optional

try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration
    _SENTRY_AVAILABLE = True
except ImportError:
    sentry_sdk = None  # type: ignore[assignment]
    LoggingIntegration = None  # type: ignore[assignment,misc]
    _SENTRY_AVAILABLE = False

from backend.core.config import get_settings
from backend.core.logger import get_logger

logger = get_logger("SentryMonitor")


def _sanitize_event(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Strictly sanitize Sentry event payloads to prevent any secret or sensitive data leakage."""
    sensitive_keys = ["api_key", "password", "token", "secret", "authorization", "cookie"]
    
    # Sanitize extra / tags
    if "extra" in event:
        for k, v in list(event["extra"].items()):
            if any(sk in k.lower() for sk in sensitive_keys):
                event["extra"][k] = "[REDACTED]"
            elif isinstance(v, str):
                # Redact potential API keys (e.g. AIza..., AQ..., sk-...)
                event["extra"][k] = re.sub(r"(AIza|AQ\.|sk-)[A-Za-z0-9_\-]{20,}", "[REDACTED_API_KEY]", v)

    # Sanitize message
    if "message" in event and isinstance(event["message"], str):
        event["message"] = re.sub(r"(AIza|AQ\.|sk-)[A-Za-z0-9_\-]{20,}", "[REDACTED_API_KEY]", event["message"])

    return event


class SentryMonitor:
    """Singleton error boundary and exception telemetry manager."""

    def __init__(self):
        self.settings = get_settings()
        self.dsn = getattr(self.settings, "SENTRY_DSN", None) or os.getenv("SENTRY_DSN", "")
        self.initialized = False
        self._init_sentry()

    def _init_sentry(self) -> None:
        """Initialize Sentry SDK with strict PII protection."""
        if not _SENTRY_AVAILABLE or not self.dsn:
            logger.debug("Sentry DSN not configured. Running in local error-boundary mode.")
            return

        try:
            sentry_sdk.init(
                dsn=self.dsn,
                traces_sample_rate=1.0,
                profiles_sample_rate=1.0,
                environment=self.settings.APP_ENV,
                release=f"jarvis@{self.settings.APP_VERSION}",
                before_send=_sanitize_event,
                send_default_pii=False,
            )
            self.initialized = True
            logger.info("🛡️ Sentry Runtime Error & Performance Monitoring initialized.")
        except Exception as e:
            logger.warning(f"Could not initialize Sentry: {e}")

    def capture_exception(
        self,
        exc: Exception,
        command_id: Optional[str] = None,
        adapter: Optional[str] = None,
        tool_name: Optional[str] = None,
        task_state: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Capture an exception with sanitized execution metadata."""
        logger.error(f"Capturing exception in {adapter or 'Core'} -> {exc}")
        if not _SENTRY_AVAILABLE or not self.initialized:
            return

        with sentry_sdk.push_scope() as scope:
            if command_id:
                scope.set_tag("command_id", command_id)
            if adapter:
                scope.set_tag("adapter", adapter)
            if tool_name:
                scope.set_tag("tool_name", tool_name)
            if task_state:
                scope.set_tag("task_state", task_state)
            if extra_data:
                for k, v in extra_data.items():
                    if not any(sk in k.lower() for sk in ["key", "pass", "token", "secret"]):
                        scope.set_extra(k, str(v)[:200])

            sentry_sdk.capture_exception(exc)


# Global Singleton Sentry Monitor
sentry_monitor = SentryMonitor()


def sentry_error_boundary(adapter: str = "core"):
    """Decorator to wrap functions in isolated error boundaries and report to Sentry."""
    def decorator(func: Callable):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                sentry_monitor.capture_exception(
                    exc=exc,
                    adapter=adapter,
                    tool_name=func.__name__,
                    extra_data={"func_args": str(kwargs)[:200]},
                )
                logger.error(f"Error Boundary caught exception in '{adapter}.{func.__name__}': {exc}")
                return {"status": "error", "message": f"Error in {adapter}: {str(exc)}", "error": str(exc)}

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                sentry_monitor.capture_exception(
                    exc=exc,
                    adapter=adapter,
                    tool_name=func.__name__,
                    extra_data={"func_args": str(kwargs)[:200]},
                )
                logger.error(f"Error Boundary caught async exception in '{adapter}.{func.__name__}': {exc}")
                return {"status": "error", "message": f"Error in {adapter}: {str(exc)}", "error": str(exc)}

        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
