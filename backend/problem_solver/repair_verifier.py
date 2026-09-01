"""Repair Verification Engine with Strict BEFORE vs AFTER State Validation."""
from typing import Any, Dict
from datetime import datetime

from backend.core.logger import get_logger
from backend.problem_solver.models import (
    DiagnosticReport, DiagnosticStatus, ProblemCategory, VerificationResult
)
from backend.problem_solver.diagnostics.bluetooth_diagnostic import BluetoothDiagnostic
from backend.problem_solver.diagnostics.wifi_network_diagnostic import WiFiNetworkDiagnostic
from backend.problem_solver.diagnostics.audio_diagnostic import AudioDiagnostic
from backend.problem_solver.diagnostics.performance_diagnostic import PerformanceDiagnostic
from backend.problem_solver.diagnostics.storage_diagnostic import StorageDiagnostic
from backend.problem_solver.diagnostics.dev_env_diagnostic import DevEnvDiagnostic

logger = get_logger("RepairVerifier")


class RepairVerifier:
    """Performs strict BEFORE vs AFTER delta verification. NEVER claims success unless confirmed."""

    @staticmethod
    def verify(category: ProblemCategory, before_report: DiagnosticReport) -> VerificationResult:
        """Run post-repair diagnostic and strictly verify whether problem condition has resolved."""
        logger.info(f"Verifying repair outcome for category: {category}...")

        after_report: DiagnosticReport
        if category == ProblemCategory.BLUETOOTH:
            after_report = BluetoothDiagnostic.run_diagnostic()
        elif category in [ProblemCategory.WIFI_NETWORK, ProblemCategory.INTERNET]:
            after_report = WiFiNetworkDiagnostic.run_diagnostic()
        elif category == ProblemCategory.AUDIO:
            after_report = AudioDiagnostic.run_diagnostic()
        elif category in [ProblemCategory.PERFORMANCE_HANG, ProblemCategory.SLOW_SYSTEM]:
            after_report = PerformanceDiagnostic.run_diagnostic()
        elif category == ProblemCategory.STORAGE:
            after_report = StorageDiagnostic.run_diagnostic()
        elif category == ProblemCategory.DEV_ENVIRONMENT:
            after_report = DevEnvDiagnostic.run_diagnostic()
        else:
            after_report = before_report

        is_verified = after_report.overall_status in [DiagnosticStatus.HEALTHY, DiagnosticStatus.WARNING]

        # Explicit remaining issues
        remaining_issues = []
        if not is_verified:
            for item in after_report.items:
                if item.status == DiagnosticStatus.PROBLEM_DETECTED:
                    remaining_issues.append(f"{item.name}: {item.value}")

        if is_verified:
            msg = f"Verification PASSED. {after_report.summary}"
        else:
            msg = f"Verification FAILED. Problem condition persists: {'; '.join(remaining_issues) if remaining_issues else after_report.summary}. I have not marked this problem as fixed."

        logger.info(f"Verification outcome: {'PASSED' if is_verified else 'FAILED'}")

        return VerificationResult(
            verified=is_verified,
            timestamp=datetime.now(),
            category=category,
            before_state=before_report.raw_evidence,
            after_state=after_report.raw_evidence,
            message=msg,
            remaining_issues=remaining_issues,
        )
