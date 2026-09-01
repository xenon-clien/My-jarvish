"""Master Problem Solver Engine for JARVIS AI.

Coordinates the complete 8-stage self-healing and diagnostic loop:
Problem Description -> Observation -> Diagnosis -> RCA -> Fix Plan -> Safety Check -> Execute -> Verify -> Self-Correction -> Final Report.
"""
import re
from typing import Any, Dict, List, Optional
from datetime import datetime

from backend.core.logger import get_logger
from backend.problem_solver.models import (
    DiagnosticReport, DiagnosticStatus, ProblemCategory,
    RepairPlan, RiskLevel, RootCauseAnalysis, VerificationResult
)
from backend.problem_solver.system_health import SystemHealthEngine
from backend.problem_solver.diagnostics.bluetooth_diagnostic import BluetoothDiagnostic
from backend.problem_solver.diagnostics.wifi_network_diagnostic import WiFiNetworkDiagnostic
from backend.problem_solver.diagnostics.audio_diagnostic import AudioDiagnostic
from backend.problem_solver.diagnostics.performance_diagnostic import PerformanceDiagnostic
from backend.problem_solver.diagnostics.storage_diagnostic import StorageDiagnostic
from backend.problem_solver.diagnostics.dev_env_diagnostic import DevEnvDiagnostic
from backend.problem_solver.diagnostics.app_diagnostic import AppDiagnostic
from backend.problem_solver.diagnostics.display_diagnostic import DisplayDiagnostic
from backend.problem_solver.diagnostics.usb_input_diagnostic import USBInputDiagnostic
from backend.problem_solver.diagnostics.windows_update_diagnostic import WindowsUpdateDiagnostic
from backend.problem_solver.root_cause_engine import RootCauseEngine
from backend.problem_solver.repair_planner import RepairPlanner
from backend.problem_solver.repair_executor import RepairExecutor
from backend.problem_solver.repair_verifier import RepairVerifier
from backend.problem_solver.rollback_manager import RollbackManager
from backend.problem_solver.history import RepairHistory
from backend.problem_solver.timeline_engine import SystemTimelineEngine
from backend.problem_solver.knowledge_base import ProblemKnowledgeBase

logger = get_logger("ProblemSolverEngine")


class ProblemSolverEngine:
    """Master AI problem solver coordinating deep diagnostics, root-cause isolation, safe repair, and verification."""

    @staticmethod
    def classify_problem_category(query: str) -> ProblemCategory:
        """Classify user natural language problem query into ProblemCategory."""
        q = query.lower().strip()
        if any(w in q for w in ["health", "diagnose", "system check", "pc check"]) or ("check" in q and any(dev in q for dev in ["laptop", "pc", "system"])):
            return ProblemCategory.SYSTEM_HEALTH
        elif any(w in q for w in ["bluetooth", "blutooth", "bluetoth", "ब्लूटूथ"]):
            return ProblemCategory.BLUETOOTH
        elif any(w in q for w in ["wifi", "wi-fi", "internet", "dns", "gateway", "वाईफाई", "इंटरनेट"]) or (re.search(r"\bnet\b", q) and "nahi" in q):
            return ProblemCategory.WIFI_NETWORK
        elif any(w in q for w in ["sound", "audio", "mic", "microphone", "speaker", "volume", "mute", "awaaz", "aawaz", "आवाज़"]):
            return ProblemCategory.AUDIO
        elif any(w in q for w in ["slow", "hang", "freeze", "lag", "cpu", "ram", "memory", "heavier", "धीमा", "हैंग"]):
            return ProblemCategory.PERFORMANCE_HANG
        elif any(w in q for w in ["storage", "disk", "space", "c drive", "clean junk", "full", "स्टोरेज", "डिस्क"]):
            return ProblemCategory.STORAGE
        elif any(w in q for w in ["npm", "node", "python", "git", "pip", "compile", "gcc", "docker"]):
            return ProblemCategory.DEV_ENVIRONMENT
        elif any(w in q for w in ["usb", "mouse", "keyboard", "touchpad", "type", "कीबोर्ड", "माउस"]):
            return ProblemCategory.USB_INPUT
        elif any(w in q for w in ["display", "screen", "resolution", "flicker", "monitor", "डिस्प्ले"]):
            return ProblemCategory.DISPLAY
        elif any(w in q for w in ["update", "windows update", "restart pending"]):
            return ProblemCategory.WINDOWS_UPDATE
        else:
            return ProblemCategory.GENERIC_ERROR

    @classmethod
    def _run_diagnostic_for_category(cls, category: ProblemCategory, problem_text: str) -> DiagnosticReport:
        """Run the specialized diagnostic check for a category."""
        if category == ProblemCategory.BLUETOOTH:
            return BluetoothDiagnostic.run_diagnostic()
        elif category in [ProblemCategory.WIFI_NETWORK, ProblemCategory.INTERNET]:
            return WiFiNetworkDiagnostic.run_diagnostic()
        elif category == ProblemCategory.AUDIO:
            return AudioDiagnostic.run_diagnostic()
        elif category in [ProblemCategory.PERFORMANCE_HANG, ProblemCategory.SLOW_SYSTEM]:
            return PerformanceDiagnostic.run_diagnostic()
        elif category == ProblemCategory.STORAGE:
            return StorageDiagnostic.run_diagnostic()
        elif category == ProblemCategory.DEV_ENVIRONMENT:
            return DevEnvDiagnostic.run_diagnostic(specific_tool=problem_text)
        elif category == ProblemCategory.USB_INPUT:
            return USBInputDiagnostic.run_diagnostic()
        elif category == ProblemCategory.DISPLAY:
            return DisplayDiagnostic.run_diagnostic()
        elif category == ProblemCategory.WINDOWS_UPDATE:
            return WindowsUpdateDiagnostic.run_diagnostic()
        else:
            return BluetoothDiagnostic.run_diagnostic()

    @classmethod
    def solve_problem(
        cls,
        problem_text: str,
        auto_repair: bool = True,
        user_confirmed: bool = False
    ) -> Dict[str, Any]:
        """Execute end-to-end diagnosis, RCA, safe repair, self-correction, and verification for any PC problem."""
        logger.info(f"Initiating Problem Solver for query: '{problem_text}' (auto_repair={auto_repair})...")
        category = cls.classify_problem_category(problem_text)

        # Special Case: Universal Full System Health Scan
        if category == ProblemCategory.SYSTEM_HEALTH:
            health_res = SystemHealthEngine.get_full_health_report()
            RepairHistory.record_entry(
                problem_text=problem_text,
                category=category,
                diagnosis_summary=f"System Health: {health_res.get('issues_count', 0)} issues detected.",
                verification_passed=True,
            )
            return {
                "category": category.value,
                "stage": "health_scan",
                "diagnosis_report": health_res,
                "summary": health_res["formatted_report"],
            }

        # 1. Observation & Diagnosis
        report = cls._run_diagnostic_for_category(category, problem_text)

        # 2. Root Cause Analysis
        rca: RootCauseAnalysis = RootCauseEngine.analyze(report, raw_error_text=problem_text)

        # 3. Formulate Safe Repair Plan
        plan: RepairPlan = RepairPlanner.create_plan(rca)

        # If system is healthy or no repair action is required
        if report.overall_status == DiagnosticStatus.HEALTHY and not plan.steps:
            human_response = f"✅ **{category.value.title()} Diagnosis Complete**\n\n{report.summary}\nEverything is operational and functioning normally."
            return {
                "category": category.value,
                "status": "healthy",
                "diagnosis": report.model_dump(),
                "rca": rca.model_dump(),
                "summary": human_response,
            }

        # 4. Safety Check & Snapshot
        snap = RollbackManager.capture_snapshot(category, description=f"Pre-repair for {category.value}")

        # 5. Execution & Multi-Path Self-Correction Loop
        should_execute = auto_repair if plan.risk_level == RiskLevel.LOW else user_confirmed

        if not should_execute:
            # Plan requires user confirmation
            human_response = (
                f"🔍 **{category.value.title()} Problem Diagnosis**\n\n"
                f"• **Issue:** {report.summary}\n"
                f"• **Likely Cause:** {rca.primary_cause.title if rca.primary_cause else 'Configuration issue'}\n"
                f"• **Recommended Fix:** {plan.summary}\n"
                f"• **Risk Level:** {plan.risk_level.value.upper()}\n\n"
                f"Kya aap chahte hain ki main ye repair step execute karu?"
            )
            return {
                "category": category.value,
                "status": "confirmation_required",
                "diagnosis": report.model_dump(),
                "rca": rca.model_dump(),
                "plan": plan.model_dump(),
                "summary": human_response,
            }

        # Attempt Fix 1
        repair_res = RepairExecutor.execute_plan(plan, user_confirmed=True)
        verif_res: VerificationResult = RepairVerifier.verify(category, report)

        # Self-Correction: If Fix 1 fails and we have secondary hypotheses
        if not verif_res.verified and rca.secondary_hypotheses:
            logger.info("First repair verification failed. Attempting next safe diagnostic repair path...")
            next_hypothesis = rca.secondary_hypotheses[0]
            rca_retry = RootCauseAnalysis(
                category=category,
                timestamp=datetime.now(),
                primary_cause=next_hypothesis,
                summary=f"Fallback hypothesis: {next_hypothesis.title}",
            )
            plan_retry = RepairPlanner.create_plan(rca_retry)
            if plan_retry.risk_level == RiskLevel.LOW:
                repair_res = RepairExecutor.execute_plan(plan_retry, user_confirmed=True)
                verif_res = RepairVerifier.verify(category, report)

        # 6. Record in History
        passed = verif_res.verified
        RepairHistory.record_entry(
            problem_text=problem_text,
            category=category,
            diagnosis_summary=report.summary,
            root_cause_title=rca.primary_cause.title if rca.primary_cause else None,
            repair_summary=plan.summary,
            verification_passed=passed,
        )

        # 7. Human-like Concise Spoken / Text Report
        lines = [
            f"🛠️ **JARVIS Problem Solver — {category.value.title()}**",
            f"• **Diagnosis:** {report.summary}",
            f"• **Root Cause:** {rca.primary_cause.title if rca.primary_cause else 'Service/Driver issue'}",
            f"• **Repair Action:** {plan.summary}",
            f"• **Status:** {'✅ ' + verif_res.message if passed else '⚠️ ' + verif_res.message}",
        ]
        full_summary = "\n".join(lines)

        return {
            "category": category.value,
            "status": "completed" if passed else "verification_failed",
            "diagnosis": report.model_dump(),
            "rca": rca.model_dump(),
            "plan": plan.model_dump(),
            "repair_result": repair_res,
            "verification": verif_res.model_dump(),
            "summary": full_summary,
        }


# Global problem solver singleton
problem_solver_engine = ProblemSolverEngine()
