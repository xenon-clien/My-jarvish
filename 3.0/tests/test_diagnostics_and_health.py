"""Unit tests for Feature Health Manager, Diagnostics Engine, and Bug Finder."""
import pytest
from core.bug_finder import BugFinder, bug_finder
from core.diagnostics_engine import DiagnosticsEngine
from core.health_manager import FeatureHealthManager, HealthStatus


def test_feature_health_tracking():
    hm = FeatureHealthManager()

    # Initial state is HEALTHY
    health = hm.get_health()
    assert health["YouTube"].status == HealthStatus.HEALTHY

    # Record repeated failures
    for _ in range(5):
        hm.record_call("YouTube", success=False, error="Simulated element not found")

    health_after = hm.get_health()
    assert health_after["YouTube"].status in [HealthStatus.DEGRADED, HealthStatus.BROKEN]
    assert health_after["YouTube"].failed_calls == 5

    # WhatsApp and Voice should still be HEALTHY (Feature Isolation!)
    assert health_after["WhatsApp"].status == HealthStatus.HEALTHY
    assert health_after["Voice"].status == HealthStatus.HEALTHY

    # Recovery: record successes
    for _ in range(10):
        hm.record_call("YouTube", success=True)
    health_recovered = hm.get_health()
    assert health_recovered["YouTube"].status == HealthStatus.HEALTHY


def test_diagnostics_trace_and_root_cause():
    diag = DiagnosticsEngine()
    cid = diag.start_trace("play first short")

    diag.record_event(
        correlation_id=cid,
        category="YOUTUBE",
        operation="play_first_short",
        stage="EXECUTE",
        status="FAILED",
        message="browser_window_missing: Chrome window not open",
        error_code="TIMEOUT",
    )

    trace = diag.end_trace(cid, success=False)
    assert trace.final_status == "FAILED"
    assert trace.root_cause is not None
    assert trace.root_cause["category"] == "TIMEOUT" or "time" in trace.root_cause["likely_cause"].lower()


def test_bug_finder_scan():
    bugs = bug_finder.scan_system_integrity()
    assert isinstance(bugs, list)
