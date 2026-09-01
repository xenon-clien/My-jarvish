"""Comprehensive Unit and Integration Tests for JARVIS AI Universal PC Problem Solver."""
import pytest
from backend.problem_solver.models import (
    ProblemCategory, DiagnosticStatus, RiskLevel,
    DiagnosticReport, RootCauseAnalysis, RepairPlan
)
from backend.problem_solver.safety import CommandSafetyEngine, SAFE_COMMAND_ALLOWLIST
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
from backend.problem_solver.diagnostics.event_log_analyzer import EventLogAnalyzer
from backend.problem_solver.system_health import SystemHealthEngine
from backend.problem_solver.root_cause_engine import RootCauseEngine
from backend.problem_solver.repair_planner import RepairPlanner
from backend.problem_solver.repair_executor import RepairExecutor
from backend.problem_solver.repair_verifier import RepairVerifier
from backend.problem_solver.rollback_manager import RollbackManager
from backend.problem_solver.history import RepairHistory
from backend.problem_solver.problem_solver_engine import ProblemSolverEngine, problem_solver_engine
from backend.ai.action_planner import action_planner
from backend.ai.intent_engine import fast_intent_engine


def test_command_safety_engine_allowlist():
    """Verify safe commands are authorized with correct risk levels."""
    is_safe, msg, risk = CommandSafetyEngine.validate_command("ipconfig /flushdns")
    assert is_safe is True
    assert risk == RiskLevel.LOW

    is_safe2, msg2, risk2 = CommandSafetyEngine.validate_command("netsh winsock reset")
    assert is_safe2 is True
    assert risk2 == RiskLevel.MEDIUM


def test_command_safety_engine_blocks_dangerous_commands():
    """Verify forbidden destructive commands are strictly blocked."""
    is_safe, msg, risk = CommandSafetyEngine.validate_command("format C:")
    assert is_safe is False
    assert risk == RiskLevel.CRITICAL

    is_safe2, msg2, risk2 = CommandSafetyEngine.validate_command("del /f /s /q C:\\Windows")
    assert is_safe2 is False
    assert risk2 == RiskLevel.CRITICAL


def test_command_safety_redacts_sensitive_tokens():
    """Verify passwords and API keys are redacted before logging or AI reasoning."""
    raw_text = "Connecting with api_key='sk-1234567890abcdef12345678' and password='mySecretPassword123'"
    redacted = CommandSafetyEngine.redact_sensitive_data(raw_text)
    assert "mySecretPassword123" not in redacted
    assert "1234567890abcdef12345678" not in redacted
    assert "********" in redacted


def test_bluetooth_diagnostic():
    """Verify Bluetooth diagnostic runs and returns structured report."""
    report = BluetoothDiagnostic.run_diagnostic()
    assert isinstance(report, DiagnosticReport)
    assert report.category == ProblemCategory.BLUETOOTH
    assert len(report.items) > 0
    assert report.overall_status in [DiagnosticStatus.HEALTHY, DiagnosticStatus.PROBLEM_DETECTED, DiagnosticStatus.WARNING]


def test_wifi_network_diagnostic():
    """Verify 6-layer WiFi and internet diagnostic chain."""
    report = WiFiNetworkDiagnostic.run_diagnostic()
    assert isinstance(report, DiagnosticReport)
    assert report.category in [ProblemCategory.WIFI_NETWORK, ProblemCategory.INTERNET]
    assert len(report.items) >= 3


def test_audio_diagnostic():
    """Verify audio services and endpoints diagnostic."""
    report = AudioDiagnostic.run_diagnostic()
    assert isinstance(report, DiagnosticReport)
    assert report.category == ProblemCategory.AUDIO
    assert any("Audio" in item.name for item in report.items)


def test_performance_diagnostic():
    """Verify CPU, RAM, and process bottleneck diagnostic."""
    report = PerformanceDiagnostic.run_diagnostic()
    assert isinstance(report, DiagnosticReport)
    assert "cpu_percent" in report.raw_evidence
    assert "ram_percent" in report.raw_evidence


def test_storage_diagnostic():
    """Verify storage partition space and safe preview scan."""
    report = StorageDiagnostic.run_diagnostic()
    assert isinstance(report, DiagnosticReport)
    assert report.category == ProblemCategory.STORAGE
    assert "drives" in report.raw_evidence


def test_dev_env_diagnostic():
    """Verify developer toolchains inspection."""
    report = DevEnvDiagnostic.run_diagnostic()
    assert isinstance(report, DiagnosticReport)
    assert report.category == ProblemCategory.DEV_ENVIRONMENT
    assert "tools" in report.raw_evidence
    assert "python" in report.raw_evidence["tools"]


def test_app_diagnostic():
    """Verify application diagnostic."""
    report = AppDiagnostic.run_diagnostic("chrome")
    assert isinstance(report, DiagnosticReport)
    assert report.category == ProblemCategory.APPLICATION


def test_display_and_usb_diagnostic():
    """Verify display and USB/HID device diagnostics."""
    disp_rep = DisplayDiagnostic.run_diagnostic()
    assert disp_rep.category == ProblemCategory.DISPLAY

    usb_rep = USBInputDiagnostic.run_diagnostic()
    assert usb_rep.category == ProblemCategory.USB_INPUT


def test_windows_update_and_event_log_diagnostic():
    """Verify Windows Update and Event Log diagnostics."""
    upd_rep = WindowsUpdateDiagnostic.run_diagnostic()
    assert upd_rep.category == ProblemCategory.WINDOWS_UPDATE

    ev_rep = EventLogAnalyzer.run_diagnostic()
    assert ev_rep.category == ProblemCategory.SYSTEM_FILES


def test_system_health_engine():
    """Verify Master System Health overview report generation."""
    health = SystemHealthEngine.get_full_health_report()
    assert health["status"] == "success"
    assert "components" in health
    assert "CPU" in health["components"]
    assert "RAM" in health["components"]
    assert "Bluetooth" in health["components"]
    assert "formatted_report" in health


def test_root_cause_and_repair_planning():
    """Verify RootCauseEngine and RepairPlanner construct valid, safe repair plans."""
    bt_rep = BluetoothDiagnostic.run_diagnostic()
    rca = RootCauseEngine.analyze(bt_rep)
    assert isinstance(rca, RootCauseAnalysis)
    assert rca.primary_cause is not None

    plan = RepairPlanner.create_plan(rca)
    assert isinstance(plan, RepairPlan)
    assert len(plan.steps) > 0
    assert plan.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]


def test_repair_verifier():
    """Verify RepairVerifier performs strict validation without false success claims."""
    bt_rep = BluetoothDiagnostic.run_diagnostic()
    verif = RepairVerifier.verify(ProblemCategory.BLUETOOTH, bt_rep)
    assert isinstance(verif.verified, bool)
    assert "Verification" in verif.message


def test_rollback_manager_and_history():
    """Verify logical snapshot capture, rollback, and history persistence."""
    snap = RollbackManager.capture_snapshot(ProblemCategory.BLUETOOTH, description="Unit test snapshot")
    assert snap.snapshot_id.startswith("snap_")
    retrieved = RollbackManager.get_snapshot(snap.snapshot_id)
    assert retrieved is not None
    assert retrieved.category == ProblemCategory.BLUETOOTH

    hist_entry = RepairHistory.record_entry(
        problem_text="Test problem",
        category=ProblemCategory.BLUETOOTH,
        diagnosis_summary="Unit test diagnosis",
        verification_passed=True,
    )
    assert hist_entry.entry_id.startswith("hist_")
    recent = RepairHistory.get_recent_entries(limit=5)
    assert any(e.entry_id == hist_entry.entry_id for e in recent)


def test_problem_solver_master_solve():
    """Verify ProblemSolverEngine executes end-to-end diagnosis and self-healing."""
    res = problem_solver_engine.solve_problem("Bluetooth nahi chal raha", auto_repair=True)
    assert "category" in res
    assert res["category"] == "bluetooth"
    assert "summary" in res

    health_res = problem_solver_engine.solve_problem("check my laptop", auto_repair=True)
    assert health_res["category"] == "system_health"
    assert "formatted_report" in health_res["diagnosis_report"]


def test_action_planner_problem_solver_routing():
    """Verify ActionPlanner routes PC problem queries to Problem Solver tools."""
    queries = [
        ("check my laptop", "get_comprehensive_system_health"),
        ("laptop check karo", "get_comprehensive_system_health"),
        ("Bluetooth Nahin chal raha hai", "diagnose_system_problem"),
        ("bluetooth nahi chal raha", "diagnose_system_problem"),
        ("why is bluetooth not working", "diagnose_system_problem"),
        ("wifi nahi chal raha", "diagnose_system_problem"),
        ("WiFi nahin chal raha", "diagnose_system_problem"),
        ("internet nahi chal raha", "diagnose_system_problem"),
        ("no sound", "diagnose_system_problem"),
        ("awaaz nahi aa rahi", "diagnose_system_problem"),
        ("laptop slow hai", "diagnose_system_problem"),
        ("storage full hai", "diagnose_system_problem"),
        ("npm kaam nahi kar raha", "diagnose_system_problem"),
    ]
    for q, expected_tool in queries:
        plan = action_planner.create_plan(q)
        assert plan is not None, f"Failed to plan for: {q}"
        assert plan.steps[0].tool_call.name == expected_tool, f"Query '{q}' routed to '{plan.steps[0].tool_call.name}', expected '{expected_tool}'"


def test_fast_intent_engine_problem_solver_routing():
    """Verify FastIntentEngine routes PC problem queries instantaneously."""
    match1 = fast_intent_engine.match("check my laptop")
    assert match1 is not None
    assert match1.tool_calls[0].name == "get_comprehensive_system_health"

    match2 = fast_intent_engine.match("Bluetooth Nahin chal raha hai")
    assert match2 is not None
    assert match2.tool_calls[0].name == "diagnose_system_problem"

    match3 = fast_intent_engine.match("wifi nahi chal raha")
    assert match3 is not None
    assert match3.tool_calls[0].name == "diagnose_system_problem"


def test_driver_engine_and_backup_manager():
    """Verify DriverDiagnosticEngine, DriverRepairEngine, and DriverBackupManager."""
    from backend.problem_solver.driver_engine import (
        DriverDiagnosticEngine, DriverRepairEngine, DriverBackupManager
    )
    rep = DriverDiagnosticEngine.diagnose_driver("Bluetooth")
    assert isinstance(rep, DiagnosticReport)

    restore_info = DriverBackupManager.check_system_restore_available()
    assert "restore_enabled" in restore_info
    assert "message" in restore_info

    driver_meta = DriverBackupManager.record_driver_state("Bluetooth")
    assert driver_meta["device"] == "Bluetooth"
    assert "provider" in driver_meta


def test_system_timeline_engine():
    """Verify SystemTimelineEngine gathers updates and critical events."""
    from backend.problem_solver.timeline_engine import SystemTimelineEngine
    timeline = SystemTimelineEngine.get_recent_timeline(hours_back=48)
    assert "timeline" in timeline
    assert "hours_analyzed" in timeline
    assert timeline["hours_analyzed"] == 48


def test_problem_knowledge_base():
    """Verify ProblemKnowledgeBase returns structured categories and guidelines."""
    from backend.problem_solver.knowledge_base import ProblemKnowledgeBase
    bt_info = ProblemKnowledgeBase.get_info_for_category(ProblemCategory.BLUETOOTH)
    assert bt_info is not None
    assert "symptoms" in bt_info
    assert "safe_fixes" in bt_info
    assert bt_info["risk_level"] == RiskLevel.LOW


def test_root_cause_error_text_parsing():
    """Verify RootCauseEngine parses stacktraces, terminal errors, and Windows error codes."""
    hypo1 = RootCauseEngine.analyze_error_text("Error: connect ECONNREFUSED 127.0.0.1:5000")
    assert "Connection Refused" in hypo1.title
    assert hypo1.confidence > 0.85

    hypo2 = RootCauseEngine.analyze_error_text("ModuleNotFoundError: No module named 'fastapi'")
    assert "Missing Dependency" in hypo2.title
    assert hypo2.confidence > 0.85

    hypo3 = RootCauseEngine.analyze_error_text("Windows has stopped this device because it has reported problems. (Code 43)")
    assert "Code 43" in hypo3.title

