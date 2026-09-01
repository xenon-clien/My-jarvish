"""Windows Event Log & System Timeline Correlation Engine."""
import subprocess
from typing import Any, Dict, List, Optional
from datetime import datetime

from backend.core.logger import get_logger
from backend.problem_solver.models import (
    DiagnosticItem, DiagnosticReport, DiagnosticStatus, ProblemCategory
)

logger = get_logger("EventLogAnalyzer")


class EventLogAnalyzer:
    """Analyzes Windows System and Application Event Logs to isolate crash timelines and driver errors."""

    @staticmethod
    def get_recent_critical_events(hours_back: int = 12) -> List[Dict[str, Any]]:
        """Retrieve recent Windows Error and Critical events from System & Application logs."""
        events: List[Dict[str, Any]] = []
        try:
            # Query recent Level 1 (Critical) and Level 2 (Error) events via PowerShell
            ps_cmd = (
                f"$cutoff = (Get-Date).AddHours(-{hours_back}); "
                f"Get-WinEvent -FilterHashtable @{{LogName='System','Application'; Level=1,2; StartTime=$cutoff}} -MaxEvents 15 -ErrorAction SilentlyContinue | "
                f"Select-Object -Property TimeCreated, ProviderName, Id, LevelDisplayName, Message | ConvertTo-Json -Compress"
            )
            res = subprocess.run(f'powershell -NoProfile -Command "{ps_cmd}"', shell=True, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                import json
                try:
                    data = json.loads(res.stdout.strip())
                    if isinstance(data, dict):
                        events = [data]
                    elif isinstance(data, list):
                        events = data
                except Exception:
                    events = []
        except Exception as e:
            logger.debug(f"Event log query error: {e}")

        clean_events = []
        for ev in events:
            time_str = str(ev.get("TimeCreated", ""))
            clean_events.append({
                "time": time_str,
                "provider": ev.get("ProviderName", "Windows"),
                "event_id": ev.get("Id", 0),
                "level": ev.get("LevelDisplayName", "Error"),
                "message": (ev.get("Message") or "")[:200].strip(),
            })

        return clean_events

    @staticmethod
    def run_diagnostic() -> DiagnosticReport:
        """Run Event Log diagnostic report."""
        events = EventLogAnalyzer.get_recent_critical_events(hours_back=6)
        items: List[DiagnosticItem] = []
        overall_status = DiagnosticStatus.HEALTHY

        if not events:
            items.append(DiagnosticItem(
                name="Windows Event Log Health",
                status=DiagnosticStatus.HEALTHY,
                value="No Critical Errors in last 6 hours",
                details="Windows System and Application event logs show no recent critical crashes.",
            ))
            summary = "No recent critical system errors or driver crash logs detected."
        else:
            overall_status = DiagnosticStatus.WARNING
            items.append(DiagnosticItem(
                name="Windows Event Log Health",
                status=DiagnosticStatus.WARNING,
                value=f"{len(events)} Error/Warning events in last 6 hours",
                details=f"Recent event: {events[0]['provider']} (Event {events[0]['event_id']})",
            ))
            summary = f"Detected {len(events)} recent system error log events in Windows."

        return DiagnosticReport(
            category=ProblemCategory.SYSTEM_FILES,
            overall_status=overall_status,
            summary=summary,
            items=items,
            raw_evidence={"recent_events": events},
        )
