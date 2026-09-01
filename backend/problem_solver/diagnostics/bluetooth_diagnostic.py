"""Bluetooth Hardware, Driver, and Service Diagnostic Engine for Windows."""
import subprocess
from typing import Any, Dict, List, Optional
import psutil

from backend.core.logger import get_logger
from backend.problem_solver.models import (
    DiagnosticItem, DiagnosticReport, DiagnosticStatus, ProblemCategory
)

logger = get_logger("BluetoothDiagnostic")


class BluetoothDiagnostic:
    """Diagnoses Windows Bluetooth hardware adapters, drivers, and background services."""

    @staticmethod
    def run_diagnostic() -> DiagnosticReport:
        """Execute full Bluetooth inspection on Windows."""
        items: List[DiagnosticItem] = []
        raw_evidence: Dict[str, Any] = {}
        overall_status = DiagnosticStatus.HEALTHY
        summary_points = []

        # 1. Inspect Bluetooth Services (bthserv, BTAGService, bthHFSrv)
        target_services = ["bthserv", "BTAGService", "bthHFSrv"]
        service_statuses = {}
        for s_name in target_services:
            try:
                srv = psutil.win_service_get(s_name)
                status = srv.status()
                start_type = srv.start_type()
                service_statuses[s_name] = {"status": status, "start_type": start_type}
            except Exception:
                service_statuses[s_name] = {"status": "not_found", "start_type": "unknown"}

        raw_evidence["services"] = service_statuses

        bthserv_status = service_statuses.get("bthserv", {}).get("status", "unknown")
        if bthserv_status == "running":
            items.append(DiagnosticItem(
                name="Bluetooth Support Service (bthserv)",
                status=DiagnosticStatus.HEALTHY,
                value="Running",
                details="Main Windows Bluetooth service is running properly.",
            ))
        else:
            items.append(DiagnosticItem(
                name="Bluetooth Support Service (bthserv)",
                status=DiagnosticStatus.PROBLEM_DETECTED,
                value=bthserv_status,
                details="Main Windows Bluetooth service is stopped or not running.",
            ))
            overall_status = DiagnosticStatus.PROBLEM_DETECTED
            summary_points.append("Bluetooth Support Service is not running")

        # 2. Inspect Bluetooth Adapters via PowerShell Get-PnpDevice
        adapters_found = []
        try:
            cmd = "powershell -NoProfile -Command \"Get-PnpDevice -Class 'Bluetooth' | Select-Object -Property FriendlyName, Status, Class, Problem, Present | ConvertTo-Json -Compress\""
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                import json
                try:
                    data = json.loads(res.stdout.strip())
                    if isinstance(data, dict):
                        adapters_found = [data]
                    elif isinstance(data, list):
                        adapters_found = data
                except Exception:
                    adapters_found = []
        except Exception as e:
            logger.debug(f"PnP Bluetooth query error: {e}")

        raw_evidence["pnp_devices"] = adapters_found

        if not adapters_found:
            items.append(DiagnosticItem(
                name="Bluetooth Adapter Hardware",
                status=DiagnosticStatus.PROBLEM_DETECTED,
                value="Not Detected",
                details="No Bluetooth adapter hardware found in Device Manager.",
            ))
            overall_status = DiagnosticStatus.PROBLEM_DETECTED
            summary_points.append("No Bluetooth adapter detected in Device Manager")
        else:
            has_ok_adapter = False
            for dev in adapters_found:
                name = dev.get("FriendlyName", "Unknown Adapter")
                status = dev.get("Status", "Unknown")
                problem = dev.get("Problem", 0)
                present = dev.get("Present", True)

                # Ignore generic virtual or RFCOMM devices for main adapter health
                if "radio" in name.lower() or "adapter" in name.lower() or "intel" in name.lower() or "realtek" in name.lower() or "qualcomm" in name.lower():
                    if status == "OK" and problem == 0 and present:
                        has_ok_adapter = True
                        items.append(DiagnosticItem(
                            name=f"Adapter: {name}",
                            status=DiagnosticStatus.HEALTHY,
                            value="Status OK",
                            details="Adapter is present and functioning normally.",
                        ))
                    else:
                        overall_status = DiagnosticStatus.PROBLEM_DETECTED
                        err_code = f"Code {problem}" if problem else "Status Error"
                        items.append(DiagnosticItem(
                            name=f"Adapter: {name}",
                            status=DiagnosticStatus.PROBLEM_DETECTED,
                            value=f"{status} ({err_code})",
                            details=f"Device reporting status: {status}, problem code: {problem}",
                            error_code=err_code,
                        ))
                        summary_points.append(f"Bluetooth adapter '{name}' has error ({err_code})")

            if not has_ok_adapter and not summary_points:
                # All detected devices might be peripheral endpoints
                items.append(DiagnosticItem(
                    name="Bluetooth Hardware State",
                    status=DiagnosticStatus.WARNING,
                    value="Peripheral Only / Adapter Inactive",
                    details="Only Bluetooth endpoints or virtual devices found.",
                ))

        if overall_status == DiagnosticStatus.HEALTHY:
            summary = "Bluetooth hardware adapter and Windows services are functioning normally."
        else:
            summary = f"Bluetooth issue detected: {'; '.join(summary_points)}."

        return DiagnosticReport(
            category=ProblemCategory.BLUETOOTH,
            overall_status=overall_status,
            summary=summary,
            items=items,
            raw_evidence=raw_evidence,
            suggested_focus="bluetooth_service" if bthserv_status != "running" else "bluetooth_adapter",
        )
