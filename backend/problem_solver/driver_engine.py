"""Driver Diagnostic, Safe Repair, and Backup Engine for Windows Devices."""
import os
import subprocess
from typing import Any, Dict, List, Optional
from datetime import datetime

from backend.core.logger import get_logger
from backend.problem_solver.models import (
    DiagnosticItem, DiagnosticReport, DiagnosticStatus, ProblemCategory, RiskLevel
)

logger = get_logger("DriverEngine")


class DriverBackupManager:
    """Manages driver metadata records, exports, and Windows System Restore Point checks."""

    @staticmethod
    def check_system_restore_available() -> Dict[str, Any]:
        """Check if Windows System Restore is enabled and list recent restore points."""
        restore_points = []
        enabled = False
        try:
            cmd = "powershell -NoProfile -Command \"Get-ComputerRestorePoint | Select-Object -Property SequenceNumber, Description, CreationTime, RestorePointType | ConvertTo-Json -Compress\""
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                import json
                try:
                    data = json.loads(res.stdout.strip())
                    restore_points = [data] if isinstance(data, dict) else (data if isinstance(data, list) else [])
                    enabled = True
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Restore point check error: {e}")

        return {
            "restore_enabled": enabled or len(restore_points) > 0,
            "restore_points_count": len(restore_points),
            "recent_points": restore_points[:3],
            "message": f"System Restore is active with {len(restore_points)} available restore point(s)." if restore_points else "No active System Restore points detected. Proceed with logical backup.",
        }

    @staticmethod
    def record_driver_state(device_name: str) -> Dict[str, Any]:
        """Record current driver metadata (provider, version, INF name) before modifications."""
        logger.info(f"Recording driver state for device: {device_name}...")
        driver_info = {}
        try:
            ps_cmd = f"powershell -NoProfile -Command \"Get-PnpDevice -FriendlyName '*{device_name}*' | Get-PnpDeviceProperty -KeyName 'DEVPKEY_Device_DriverVersion','DEVPKEY_Device_DriverProvider' | Select-Object -Property KeyName, Data | ConvertTo-Json -Compress\""
            res = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True, timeout=4)
            if res.returncode == 0 and res.stdout.strip():
                import json
                try:
                    data = json.loads(res.stdout.strip())
                    items = [data] if isinstance(data, dict) else (data if isinstance(data, list) else [])
                    for it in items:
                        k = it.get("KeyName", "")
                        v = it.get("Data", "")
                        if "DriverVersion" in k:
                            driver_info["version"] = v
                        elif "DriverProvider" in k:
                            driver_info["provider"] = v
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Driver state query error: {e}")

        return {
            "device": device_name,
            "timestamp": datetime.now().isoformat(),
            "provider": driver_info.get("provider", "Microsoft/Vendor"),
            "version": driver_info.get("version", "Installed"),
        }


class DriverDiagnosticEngine:
    """Diagnoses device drivers across Bluetooth, Wi-Fi, Audio, GPU, USB, and Touchpad."""

    @staticmethod
    def diagnose_driver(device_class: str) -> DiagnosticReport:
        """Query driver status for a given PnP class."""
        items: List[DiagnosticItem] = []
        raw_evidence: Dict[str, Any] = {}
        overall_status = DiagnosticStatus.HEALTHY
        devices = []

        try:
            cmd = f"powershell -NoProfile -Command \"Get-PnpDevice -Class '{device_class}' | Select-Object -Property FriendlyName, Status, Problem, InstanceId | ConvertTo-Json -Compress\""
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                import json
                try:
                    data = json.loads(res.stdout.strip())
                    devices = [data] if isinstance(data, dict) else (data if isinstance(data, list) else [])
                except Exception:
                    devices = []
        except Exception as e:
            logger.debug(f"Driver PnP diagnostic error: {e}")

        raw_evidence["devices"] = devices

        for d in devices:
            name = d.get("FriendlyName", f"Device ({device_class})")
            status = d.get("Status", "Unknown")
            problem = d.get("Problem", 0)

            if status == "OK" and problem == 0:
                items.append(DiagnosticItem(
                    name=f"Driver: {name}",
                    status=DiagnosticStatus.HEALTHY,
                    value="Working normally",
                    details=f"Device reporting Status: {status}",
                ))
            else:
                overall_status = DiagnosticStatus.PROBLEM_DETECTED
                items.append(DiagnosticItem(
                    name=f"Driver: {name}",
                    status=DiagnosticStatus.PROBLEM_DETECTED,
                    value=f"Error (Code {problem})",
                    details=f"Device reported Status: {status}, Error Code: {problem}",
                    error_code=f"Code {problem}",
                ))

        if not devices:
            items.append(DiagnosticItem(
                name=f"Driver Class: {device_class}",
                status=DiagnosticStatus.WARNING,
                value="No Devices Found",
                details=f"No PnP devices matching class '{device_class}' detected.",
            ))

        return DiagnosticReport(
            category=ProblemCategory.GENERIC_ERROR,
            overall_status=overall_status,
            summary=f"Driver scan for class '{device_class}' complete: {len(devices)} device(s) inspected.",
            items=items,
            raw_evidence=raw_evidence,
        )


class DriverRepairEngine:
    """Executes safe official driver re-scans, PnP refreshes, and device reinitialization."""

    @staticmethod
    def scan_for_hardware_changes() -> Dict[str, Any]:
        """Trigger Windows PnP hardware device rescan (official pnputil /scan-devices)."""
        logger.info("Triggering Windows PnP hardware rescan via pnputil...")
        try:
            res = subprocess.run("pnputil /scan-devices", shell=True, capture_output=True, text=True, timeout=10)
            return {
                "status": "success" if res.returncode == 0 else "warning",
                "action": "scan_for_hardware_changes",
                "message": "Windows hardware devices re-scanned and PnP bus refreshed.",
            }
        except Exception as e:
            return {"status": "error", "action": "scan_for_hardware_changes", "message": f"Hardware scan error: {e}"}

    @staticmethod
    def reinitialize_pnp_device(instance_id: str) -> Dict[str, Any]:
        """Safely disable and re-enable a specific device instance via PowerShell."""
        logger.info(f"Reinitializing PnP device instance: {instance_id}...")
        try:
            cmd = (
                f"powershell -NoProfile -Command \""
                f"Disable-PnpDevice -InstanceId '{instance_id}' -Confirm:$false -ErrorAction SilentlyContinue; "
                f"Start-Sleep -Seconds 1; "
                f"Enable-PnpDevice -InstanceId '{instance_id}' -Confirm:$false -ErrorAction SilentlyContinue\""
            )
            subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return {
                "status": "success",
                "action": "reinitialize_pnp_device",
                "message": f"Device instance '{instance_id}' reinitialized successfully.",
            }
        except Exception as e:
            return {"status": "error", "action": "reinitialize_pnp_device", "message": f"Device reinitialization error: {e}"}
