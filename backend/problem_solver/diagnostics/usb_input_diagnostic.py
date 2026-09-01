"""USB Controllers, Keyboard, Mouse, and Touchpad Diagnostic Engine."""
import subprocess
from typing import Any, Dict, List, Optional

from backend.core.logger import get_logger
from backend.problem_solver.models import (
    DiagnosticItem, DiagnosticReport, DiagnosticStatus, ProblemCategory
)

logger = get_logger("USBInputDiagnostic")


class USBInputDiagnostic:
    """Diagnoses USB bus controllers, Keyboards, Mice, Touchpads, and HID devices."""

    @staticmethod
    def run_diagnostic() -> DiagnosticReport:
        """Execute USB and HID device diagnostic."""
        items: List[DiagnosticItem] = []
        raw_evidence: Dict[str, Any] = {}
        overall_status = DiagnosticStatus.HEALTHY
        summary_points = []

        # Query USB and Input classes (USB, Keyboard, Mouse, HIDClass)
        pnp_devices = []
        try:
            cmd = "powershell -NoProfile -Command \"Get-PnpDevice -Class 'USB', 'Keyboard', 'Mouse', 'HIDClass' | Select-Object -Property FriendlyName, Status, Class, Problem | ConvertTo-Json -Compress\""
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                import json
                try:
                    data = json.loads(res.stdout.strip())
                    if isinstance(data, dict):
                        pnp_devices = [data]
                    elif isinstance(data, list):
                        pnp_devices = data
                except Exception:
                    pnp_devices = []
        except Exception as e:
            logger.debug(f"USB/Input PnP query error: {e}")

        raw_evidence["devices"] = pnp_devices

        usb_count = 0
        kb_count = 0
        mouse_count = 0
        err_devices = []

        for d in pnp_devices:
            cls = d.get("Class", "")
            name = d.get("FriendlyName", "") or "HID Device"
            status = d.get("Status", "Unknown")
            problem = d.get("Problem", 0)

            if cls == "USB":
                usb_count += 1
            elif cls == "Keyboard":
                kb_count += 1
            elif cls == "Mouse":
                mouse_count += 1

            if status != "OK" or problem != 0:
                err_devices.append((name, cls, status, problem))

        items.append(DiagnosticItem(
            name="USB Host Controllers & Root Hubs",
            status=DiagnosticStatus.HEALTHY if usb_count > 0 else DiagnosticStatus.WARNING,
            value=f"{usb_count} USB Devices/Controllers active",
            details="USB subsystem root hubs detected.",
        ))

        items.append(DiagnosticItem(
            name="Keyboard & Touchpad Subsystem",
            status=DiagnosticStatus.HEALTHY if kb_count > 0 else DiagnosticStatus.WARNING,
            value=f"{kb_count} Keyboard/Input devices active",
            details="Internal and external keyboard interfaces detected.",
        ))

        items.append(DiagnosticItem(
            name="Mouse & Pointing Devices",
            status=DiagnosticStatus.HEALTHY if mouse_count > 0 else DiagnosticStatus.WARNING,
            value=f"{mouse_count} Pointing devices active",
            details="Touchpad and external mouse interfaces detected.",
        ))

        if err_devices:
            overall_status = DiagnosticStatus.PROBLEM_DETECTED
            for name, cls, status, problem in err_devices[:5]:
                items.append(DiagnosticItem(
                    name=f"Device Error: {name}",
                    status=DiagnosticStatus.PROBLEM_DETECTED,
                    value=f"{status} (Code {problem})",
                    details=f"Class: {cls}, problem code: {problem}",
                    error_code=f"Code {problem}",
                ))
                summary_points.append(f"Device '{name}' has error (Code {problem})")

        if overall_status == DiagnosticStatus.HEALTHY:
            summary = "USB ports, Keyboard, Mouse, and Touchpad subsystems are functioning normally."
        else:
            summary = f"USB/Input device issue detected: {'; '.join(summary_points)}."

        return DiagnosticReport(
            category=ProblemCategory.USB_INPUT,
            overall_status=overall_status,
            summary=summary,
            items=items,
            raw_evidence=raw_evidence,
            suggested_focus="usb_controller" if any(e[1] == "USB" for e in err_devices) else "input_device",
        )
