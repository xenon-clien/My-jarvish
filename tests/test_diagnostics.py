"""Automated Unit & Integration Test Suite for JARVIS Self-Diagnostic Bug Finder Engine."""
import pytest
import time
from backend.diagnostics.engine import SelfDiagnosticEngine
from backend.diagnostics.models import (
    DiagnosticEvent,
    ErrorCode,
    FailureCategory,
    FixabilityType,
    HealthStatus,
    TransactionTrace,
)
from backend.diagnostics.startup_checker import StartupHealthChecker


@pytest.fixture
def engine(tmp_path):
    """Provide an isolated test diagnostic engine instance."""
    return SelfDiagnosticEngine(log_dir=str(tmp_path / "diag_logs"))


class TestDiagnosticEngineLifecycle:
    """Test correlation ID generation, transaction recording, and event emission."""

    def test_correlation_id_format(self, engine):
        cid = engine.create_correlation_id()
        assert cid.startswith("JRV-")
        assert len(cid.split("-")) >= 3

    def test_successful_transaction_lifecycle(self, engine):
        cid = engine.start_transaction("video pause karo")
        engine.record_event(DiagnosticEvent(
            eventId="EVT-1",
            correlationId=cid,
            category="NLU",
            operation="PAUSE",
            stage="INTENT",
            status="SUCCESS",
        ))
        engine.record_event(DiagnosticEvent(
            eventId="EVT-2",
            correlationId=cid,
            category="YOUTUBE",
            operation="control_media",
            stage="EXECUTE",
            status="SUCCESS",
        ))
        engine.record_event(DiagnosticEvent(
            eventId="EVT-3",
            correlationId=cid,
            category="YOUTUBE",
            operation="control_media",
            stage="VERIFY",
            status="SUCCESS",
        ))
        trace = engine.end_transaction(cid, success=True, final_response="Ji Boss, pause kar diya.")
        
        assert trace.finalStatus == "SUCCESS"
        assert trace.correlationId == cid
        assert len(trace.stages) >= 4  # Start event + 3 stages
        assert trace.rootCause is None


class TestRootCauseAnalyzer:
    """Test evidence-based root-cause deduction and failure classification."""

    def test_execution_verification_mismatch_rca(self, engine):
        """Simulate command executed successfully but video remained playing."""
        cid = engine.start_transaction("video pause karo")
        engine.record_event(DiagnosticEvent(
            eventId="EVT-1",
            correlationId=cid,
            category="YOUTUBE",
            operation="control_media",
            stage="EXECUTE",
            status="SUCCESS",
        ))
        engine.record_event(DiagnosticEvent(
            eventId="EVT-2",
            correlationId=cid,
            category="YOUTUBE",
            operation="control_media",
            stage="VERIFY",
            status="FAILED",
            errorCode=ErrorCode.EXECUTION_VERIFICATION_MISMATCH,
            expected="PAUSED",
            actual="PLAYING",
        ))
        trace = engine.end_transaction(cid, success=False, target_subsystem="YOUTUBE")

        assert trace.finalStatus == "FAILED"
        assert trace.rootCause is not None
        assert trace.rootCause.failureCategory == FailureCategory.VERIFICATION_ERROR
        assert trace.rootCause.confidence >= 0.85
        assert "target state unchanged" in " ".join(trace.rootCause.evidence).lower()
        assert trace.rootCause.fixability == FixabilityType.FIXABLE_BY_CODE

    def test_stt_timeout_rca(self, engine):
        """Simulate microphone speech recognition timeout."""
        cid = engine.start_transaction("video rok do")
        engine.record_event(DiagnosticEvent(
            eventId="EVT-STT-FAIL",
            correlationId=cid,
            category="VOICE",
            operation="LISTEN_ONCE",
            stage="STT",
            status="FAILED",
            errorCode=ErrorCode.VOICE_STT_TIMEOUT,
        ))
        trace = engine.end_transaction(cid, success=False, target_subsystem="VOICE")

        assert trace.rootCause is not None
        assert trace.rootCause.failureCategory == FailureCategory.TIMEOUT
        assert trace.rootCause.confidence >= 0.90

    def test_whatsapp_call_platform_limitation_rca(self, engine):
        """Verify WhatsApp call is classified as platform limitation, not a code bug."""
        cid = engine.start_transaction("Harsh ko WhatsApp call lagao")
        trace = engine.end_transaction(cid, success=False, target_subsystem="WHATSAPP")

        assert trace.rootCause is not None
        assert trace.rootCause.failureCategory == FailureCategory.PLATFORM_LIMITATION
        assert trace.rootCause.fixability == FixabilityType.PLATFORM_LIMITATION


class TestFeatureHealthAndTelemetry:
    """Test live feature health calculation and log sanitization."""

    def test_feature_health_calculation(self, engine):
        # 4 successes, 1 failure in YOUTUBE
        for _ in range(4):
            cid = engine.start_transaction("video pause")
            engine.end_transaction(cid, success=True, target_subsystem="YOUTUBE")
        
        cid_fail = engine.start_transaction("video pause")
        engine.end_transaction(cid_fail, success=False, target_subsystem="YOUTUBE")

        health = engine.get_feature_health()
        yt_health = health.get("YOUTUBE")
        assert yt_health is not None
        assert yt_health.totalAttempts == 5
        assert yt_health.successCount == 4
        assert yt_health.failureCount == 1
        assert yt_health.successRatePercent == 80.0
        assert yt_health.healthStatus == HealthStatus.DEGRADED

    def test_sanitized_export_without_secrets(self, engine):
        cid = engine.start_transaction("api key AIzaSyABC1234567890_secret-token-test")
        engine.end_transaction(cid, success=True)
        report = engine.export_diagnostic_report()

        report_str = str(report)
        assert "AIzaSy" not in report_str
        assert "[REDACTED_API_KEY]" in report_str


class TestStartupHealthChecker:
    """Test boot health checks across subsystems."""

    def test_startup_health_checks(self):
        report = StartupHealthChecker.run_all_checks()
        assert "microphone" in report
        assert "speech_to_text" in report
        assert "windows_automation" in report
        assert "overall_health" in report
        assert report["overall_health"] in ["HEALTHY", "DEGRADED"]

        banner = StartupHealthChecker.format_banner(report)
        assert "JARVIS SELF-DIAGNOSTIC STARTUP HEALTH REPORT" in banner
