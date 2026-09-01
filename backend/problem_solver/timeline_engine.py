"""System Timeline & Recent Changes Engine for Problem Chronology Isolation."""
import subprocess
from typing import Any, Dict, List, Optional
from datetime import datetime

from backend.core.logger import get_logger

logger = get_logger("SystemTimelineEngine")


class SystemTimelineEngine:
    """Discovers recent system changes (updates, new software, driver changes, unexpected shutdowns)."""

    @staticmethod
    def get_recent_timeline(hours_back: int = 48) -> Dict[str, Any]:
        """Aggregate recent Windows updates, driver events, and system errors into a coherent timeline."""
        logger.info(f"Gathering system timeline changes for the last {hours_back} hours...")
        timeline_events: List[Dict[str, Any]] = []

        # 1. Check Recent Windows Updates (Get-HotFix)
        try:
            cmd = "powershell -NoProfile -Command \"Get-HotFix | Sort-Object -Property InstalledOn -Descending | Select-Object -First 5 -Property HotFixID, Description, InstalledOn | ConvertTo-Json -Compress\""
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                import json
                try:
                    data = json.loads(res.stdout.strip())
                    hotfixes = [data] if isinstance(data, dict) else (data if isinstance(data, list) else [])
                    for hf in hotfixes:
                        timeline_events.append({
                            "type": "windows_update",
                            "name": f"Hotfix {hf.get('HotFixID')} ({hf.get('Description', 'Update')})",
                            "time": str(hf.get("InstalledOn", "")),
                            "details": "Windows System Component Update",
                        })
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Hotfix timeline query error: {e}")

        # 2. Check Event Logs for recent Driver/Service Crashes
        try:
            from backend.problem_solver.diagnostics.event_log_analyzer import EventLogAnalyzer
            critical_events = EventLogAnalyzer.get_recent_critical_events(hours_back=hours_back)
            for ev in critical_events[:5]:
                timeline_events.append({
                    "type": "system_error_event",
                    "name": f"{ev.get('provider')} (Event ID {ev.get('event_id')})",
                    "time": ev.get("time", ""),
                    "details": ev.get("message", ""),
                })
        except Exception:
            pass

        return {
            "timestamp": datetime.now().isoformat(),
            "hours_analyzed": hours_back,
            "total_events": len(timeline_events),
            "timeline": timeline_events,
            "summary": f"Detected {len(timeline_events)} recent system timeline change(s) and update events in the last {hours_back}h.",
        }
