"""JARVIS Developer Observability & Auto-Debug Package.

Provides production-grade runtime instrumentation:
- CommandTracer: Monotonic sequential Command IDs (CMD-XXXX) and full lifecycle tracing.
- PlaywrightTracer: Playwright browser DOM snapshots, network, console, and trace files.
- SentryMonitor: Runtime error boundaries and exception isolation.
- FailureBundleManager: Automatic diagnostic bundle generator on verification failure.
"""
from backend.observability.command_tracer import command_tracer, CommandTrace
from backend.observability.playwright_tracer import playwright_tracer
from backend.observability.sentry_monitor import sentry_monitor, sentry_error_boundary
from backend.observability.failure_bundle import failure_bundle_manager

__all__ = [
    "command_tracer",
    "CommandTrace",
    "playwright_tracer",
    "sentry_monitor",
    "sentry_error_boundary",
    "failure_bundle_manager",
]
