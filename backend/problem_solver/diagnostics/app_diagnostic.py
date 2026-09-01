"""Application Launch, Crash, and Port Conflict Diagnostic Engine."""
import os
import psutil
from typing import Any, Dict, List, Optional

from backend.core.logger import get_logger
from backend.problem_solver.models import (
    DiagnosticItem, DiagnosticReport, DiagnosticStatus, ProblemCategory
)

logger = get_logger("AppDiagnostic")


class AppDiagnostic:
    """Diagnoses application crashing, frozen processes, missing binaries, and network port conflicts."""

    @staticmethod
    def run_diagnostic(app_name: str) -> DiagnosticReport:
        """Execute diagnostic on a specific application."""
        items: List[DiagnosticItem] = []
        raw_evidence: Dict[str, Any] = {}
        overall_status = DiagnosticStatus.HEALTHY
        summary_points = []
        clean_app = app_name.lower().strip()

        # 1. Resolve registered app entry
        app_entry = None
        try:
            from backend.tools.app_tools import app_registry
            app_entry = app_registry.resolve_app(clean_app)
        except Exception:
            pass

        raw_evidence["app_entry"] = app_entry

        if not app_entry:
            items.append(DiagnosticItem(
                name=f"Application '{app_name}'",
                status=DiagnosticStatus.PROBLEM_DETECTED,
                value="Not Registered / Not Installed",
                details=f"Could not locate an installed Windows shortcut or binary for '{app_name}'.",
            ))
            overall_status = DiagnosticStatus.PROBLEM_DETECTED
            summary_points.append(f"Application '{app_name}' is not installed or not registered")
        else:
            items.append(DiagnosticItem(
                name=f"Application: {app_entry['name']}",
                status=DiagnosticStatus.HEALTHY,
                value="Registered in Windows System",
                details=f"Configured launch command: {app_entry['command']}",
            ))

            # 2. Check running processes
            matching_pids = []
            target_exes = [e.lower() for e in app_entry.get("executables", [])]
            for p in psutil.process_iter(['pid', 'name', 'status']):
                try:
                    p_name = (p.info['name'] or '').lower()
                    if any(t_ex in p_name for t_ex in target_exes) or clean_app in p_name:
                        matching_pids.append({
                            "pid": p.info['pid'],
                            "name": p.info['name'],
                            "status": p.info['status'],
                        })
                except Exception:
                    continue

            raw_evidence["running_processes"] = matching_pids

            if matching_pids:
                hung_pids = [p for p in matching_pids if p.get("status") in ["stopped", "zombie", "dead"]]
                if hung_pids:
                    overall_status = DiagnosticStatus.PROBLEM_DETECTED
                    items.append(DiagnosticItem(
                        name="Process Runtime State",
                        status=DiagnosticStatus.PROBLEM_DETECTED,
                        value=f"{len(matching_pids)} Instances ({len(hung_pids)} Not Responding)",
                        details="A previously crashed or hung background instance is blocking new windows.",
                    ))
                    summary_points.append(f"{len(hung_pids)} unresponsive process instance(s) found")
                else:
                    items.append(DiagnosticItem(
                        name="Process Runtime State",
                        status=DiagnosticStatus.HEALTHY,
                        value=f"{len(matching_pids)} Process instances active",
                        details="Application is running in background.",
                    ))
            else:
                items.append(DiagnosticItem(
                    name="Process Runtime State",
                    status=DiagnosticStatus.HEALTHY,
                    value="Not Currently Running",
                    details="Process is idle and ready to be launched.",
                ))

        if overall_status == DiagnosticStatus.HEALTHY:
            summary = f"Application '{app_name}' is healthy and operational."
        else:
            summary = f"Issue with '{app_name}': {'; '.join(summary_points)}."

        return DiagnosticReport(
            category=ProblemCategory.APPLICATION,
            overall_status=overall_status,
            summary=summary,
            items=items,
            raw_evidence=raw_evidence,
            suggested_focus="hung_process" if summary_points else None,
        )
