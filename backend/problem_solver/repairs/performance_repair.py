"""Safe Performance Optimization and Hung Process Recovery Module."""
import os
from typing import Any, Dict, List, Optional
import psutil

from backend.core.logger import get_logger

logger = get_logger("PerformanceRepair")

# Critical Windows core processes that must NEVER be terminated
PROTECTED_SYSTEM_PROCESSES = {
    "system", "system idle process", "smss.exe", "csrss.exe", "wininit.exe",
    "services.exe", "lsass.exe", "lsm.exe", "svchost.exe", "winlogon.exe",
    "explorer.exe", "taskmgr.exe", "dwm.exe", "spoolsv.exe", "conhost.exe"
}


class PerformanceRepair:
    """Safely terminates hung user processes and optimizes background system memory."""

    @staticmethod
    def terminate_hung_processes() -> Dict[str, Any]:
        """Identify and safely terminate frozen or zombie processes."""
        logger.info("Scanning for hung or zombie user processes...")
        terminated = []
        for p in psutil.process_iter(['pid', 'name', 'status']):
            try:
                p_name = (p.info['name'] or '').lower()
                pid = p.info['pid']

                if p_name in PROTECTED_SYSTEM_PROCESSES:
                    continue

                status = p.info.get('status')
                if status in ["zombie", "dead", "stopped"]:
                    p.terminate()
                    terminated.append(f"{p_name} (PID {pid})")
            except Exception:
                continue

        return {
            "status": "success",
            "action": "terminate_hung_processes",
            "terminated_count": len(terminated),
            "terminated": terminated,
            "message": f"Cleaned up {len(terminated)} unresponsive background process(es)." if terminated else "No hung background processes detected.",
        }
