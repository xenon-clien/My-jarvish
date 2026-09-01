"""Windows Update and Core System Services Diagnostic Engine."""
import subprocess
from typing import Any, Dict, List, Optional
import psutil

from backend.core.logger import get_logger
from backend.problem_solver.models import (
    DiagnosticItem, DiagnosticReport, DiagnosticStatus, ProblemCategory
)

logger = get_logger("WindowsUpdateDiagnostic")


class WindowsUpdateDiagnostic:
    """Diagnoses Windows Update pipeline, pending restarts, and background update services."""

    @staticmethod
    def run_diagnostic() -> DiagnosticReport:
        """Execute Windows Update diagnostic inspection."""
        items: List[DiagnosticItem] = []
        raw_evidence: Dict[str, Any] = {}
        overall_status = DiagnosticStatus.HEALTHY
        summary_points = []

        # 1. Inspect Windows Update Services (wuauserv, bits, cryptsvc)
        update_services = ["wuauserv", "BITS", "CryptSvc", "TrustedInstaller"]
        srv_data = {}
        for s_name in update_services:
            try:
                srv = psutil.win_service_get(s_name)
                srv_data[s_name] = srv.status()
            except Exception:
                srv_data[s_name] = "not_found"

        raw_evidence["services"] = srv_data

        # CryptSvc should normally run; wuauserv and BITS may be demand-start
        cryptsvc_running = srv_data.get("CryptSvc") == "running"
        if not cryptsvc_running and srv_data.get("CryptSvc") != "not_found":
            overall_status = DiagnosticStatus.PROBLEM_DETECTED
            items.append(DiagnosticItem(
                name="Cryptographic Services (CryptSvc)",
                status=DiagnosticStatus.PROBLEM_DETECTED,
                value=str(srv_data.get("CryptSvc")),
                details="Cryptographic Service is stopped, which blocks signature verification of updates.",
            ))
            summary_points.append("Cryptographic service is stopped")
        else:
            items.append(DiagnosticItem(
                name="Cryptographic Services (CryptSvc)",
                status=DiagnosticStatus.HEALTHY,
                value="Running",
                details="Windows catalog database and signature services are active.",
            ))

        items.append(DiagnosticItem(
            name="Windows Update Service (wuauserv)",
            status=DiagnosticStatus.HEALTHY,
            value=f"State: {srv_data.get('wuauserv')}",
            details="Windows Update agent service status.",
        ))

        # 2. Check Pending System Restart via Windows Registry
        pending_restart = False
        try:
            cmd = "powershell -NoProfile -Command \"Test-Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Component Based Servicing\\RebootPending'\""
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3)
            if res.returncode == 0 and "true" in res.stdout.lower():
                pending_restart = True
        except Exception:
            pass

        raw_evidence["reboot_pending"] = pending_restart
        if pending_restart:
            items.append(DiagnosticItem(
                name="Pending System Restart",
                status=DiagnosticStatus.WARNING,
                value="Restart Required",
                details="A previous Windows Update or component installation requires a system restart to complete.",
            ))
            summary_points.append("A system restart is pending to complete installed updates")
        else:
            items.append(DiagnosticItem(
                name="Pending System Restart",
                status=DiagnosticStatus.HEALTHY,
                value="No Restart Pending",
                details="No pending restart locks detected.",
            ))

        if overall_status == DiagnosticStatus.HEALTHY and not pending_restart:
            summary = "Windows Update services and components are functioning normally."
        else:
            summary = f"Windows Update notice: {'; '.join(summary_points)}."

        return DiagnosticReport(
            category=ProblemCategory.WINDOWS_UPDATE,
            overall_status=overall_status if not pending_restart else DiagnosticStatus.WARNING,
            summary=summary,
            items=items,
            raw_evidence=raw_evidence,
            suggested_focus="pending_restart" if pending_restart else "update_services",
        )
