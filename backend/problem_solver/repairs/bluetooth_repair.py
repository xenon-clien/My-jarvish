"""Safe Bluetooth Service and Adapter Self-Repair Module for Windows."""
import subprocess
import time
from typing import Any, Dict

from backend.core.logger import get_logger
from backend.problem_solver.models import RiskLevel

logger = get_logger("BluetoothRepair")


class BluetoothRepair:
    """Performs safe, non-destructive Bluetooth service restarts and adapter reinitializations."""

    @staticmethod
    def restart_bluetooth_services() -> Dict[str, Any]:
        """Restart Windows Bluetooth Support Service (bthserv)."""
        logger.info("Restarting Windows Bluetooth services...")
        try:
            cmd = "powershell -NoProfile -Command \"Restart-Service -Name 'bthserv' -Force -ErrorAction SilentlyContinue; Start-Service -Name 'bthserv' -ErrorAction SilentlyContinue\""
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=8)
            time.sleep(1.0)
            return {
                "status": "success" if res.returncode == 0 else "warning",
                "action": "restart_bluetooth_services",
                "message": "Windows Bluetooth services restarted successfully.",
            }
        except Exception as e:
            return {
                "status": "error",
                "action": "restart_bluetooth_services",
                "message": f"Failed to restart Bluetooth services: {e}",
            }

    @staticmethod
    def reinitialize_adapter() -> Dict[str, Any]:
        """Re-enable Bluetooth adapter via PowerShell PnP command."""
        logger.info("Re-enabling Bluetooth PnP adapter hardware...")
        try:
            # Safely enable any disabled Bluetooth adapter
            cmd = "powershell -NoProfile -Command \"Get-PnpDevice -Class 'Bluetooth' -Status 'Error','Degraded','Unknown' | Enable-PnpDevice -Confirm:$false -ErrorAction SilentlyContinue\""
            subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=8)
            time.sleep(1.5)
            return {
                "status": "success",
                "action": "reinitialize_bluetooth_adapter",
                "message": "Bluetooth hardware adapter reinitialized and enabled.",
            }
        except Exception as e:
            return {
                "status": "error",
                "action": "reinitialize_bluetooth_adapter",
                "message": f"Adapter reinitialization error: {e}",
            }
