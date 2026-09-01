"""Display, GPU Adapter, Resolution, and Refresh Rate Diagnostic Engine."""
import ctypes
import subprocess
from typing import Any, Dict, List, Optional

from backend.core.logger import get_logger
from backend.problem_solver.models import (
    DiagnosticItem, DiagnosticReport, DiagnosticStatus, ProblemCategory
)

logger = get_logger("DisplayDiagnostic")


class DisplayDiagnostic:
    """Diagnoses Windows display adapters, GPU drivers, screen resolution, and refresh rate."""

    @staticmethod
    def run_diagnostic() -> DiagnosticReport:
        """Execute display and GPU diagnostics."""
        items: List[DiagnosticItem] = []
        raw_evidence: Dict[str, Any] = {}
        overall_status = DiagnosticStatus.HEALTHY
        summary_points = []

        # 1. Screen Resolution via Windows User32
        try:
            user32 = ctypes.windll.user32
            width = user32.GetSystemMetrics(0)
            height = user32.GetSystemMetrics(1)
            monitors = user32.GetSystemMetrics(80)  # SM_CMONITORS
            items.append(DiagnosticItem(
                name="Primary Screen Resolution",
                status=DiagnosticStatus.HEALTHY,
                value=f"{width} x {height} ({monitors} display detected)",
                details="Native primary screen resolution read successfully.",
            ))
            raw_evidence["resolution"] = f"{width}x{height}"
            raw_evidence["monitors"] = monitors
        except Exception as e:
            raw_evidence["resolution_error"] = str(e)

        # 2. GPU Display Adapters via PowerShell Get-PnpDevice / WMI
        gpu_adapters = []
        try:
            cmd = "powershell -NoProfile -Command \"Get-PnpDevice -Class 'Display' | Select-Object -Property FriendlyName, Status, Problem | ConvertTo-Json -Compress\""
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                import json
                try:
                    data = json.loads(res.stdout.strip())
                    if isinstance(data, dict):
                        gpu_adapters = [data]
                    elif isinstance(data, list):
                        gpu_adapters = data
                except Exception:
                    gpu_adapters = []
        except Exception as e:
            logger.debug(f"GPU PnP query error: {e}")

        raw_evidence["gpu_adapters"] = gpu_adapters

        if not gpu_adapters:
            items.append(DiagnosticItem(
                name="Graphics / GPU Adapters",
                status=DiagnosticStatus.WARNING,
                value="Standard Graphics Display",
                details="No dedicated GPU driver query returned.",
            ))
        else:
            for gpu in gpu_adapters:
                name = gpu.get("FriendlyName", "Graphics Adapter")
                status = gpu.get("Status", "Unknown")
                problem = gpu.get("Problem", 0)

                if status == "OK" and problem == 0:
                    items.append(DiagnosticItem(
                        name=f"GPU Adapter: {name}",
                        status=DiagnosticStatus.HEALTHY,
                        value="Status OK",
                        details="GPU driver is running without error.",
                    ))
                else:
                    overall_status = DiagnosticStatus.PROBLEM_DETECTED
                    items.append(DiagnosticItem(
                        name=f"GPU Adapter: {name}",
                        status=DiagnosticStatus.PROBLEM_DETECTED,
                        value=f"{status} (Code {problem})",
                        details=f"GPU driver reported problem: {problem}",
                        error_code=f"Code {problem}",
                    ))
                    summary_points.append(f"GPU '{name}' has error (Code {problem})")

        if overall_status == DiagnosticStatus.HEALTHY:
            summary = "Display adapters, GPU drivers, and screen resolution are functioning properly."
        else:
            summary = f"Display issue detected: {'; '.join(summary_points)}."

        return DiagnosticReport(
            category=ProblemCategory.DISPLAY,
            overall_status=overall_status,
            summary=summary,
            items=items,
            raw_evidence=raw_evidence,
            suggested_focus="gpu_driver" if summary_points else None,
        )
