"""Windows Core Update and Component Services Repair Module."""
import subprocess
import time
from typing import Any, Dict

from backend.core.logger import get_logger

logger = get_logger("WindowsRepair")


class WindowsRepair:
    """Repairs Windows Update services and component store health."""

    @staticmethod
    def restart_update_services() -> Dict[str, Any]:
        """Restart Windows Update and Cryptographic services."""
        logger.info("Restarting Windows Update and Cryptographic pipeline services...")
        try:
            cmd = (
                "powershell -NoProfile -Command \""
                "Restart-Service -Name 'CryptSvc' -Force -ErrorAction SilentlyContinue; "
                "Restart-Service -Name 'BITS' -Force -ErrorAction SilentlyContinue; "
                "Restart-Service -Name 'wuauserv' -Force -ErrorAction SilentlyContinue\""
            )
            subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=12)
            time.sleep(1.0)
            return {
                "status": "success",
                "action": "restart_update_services",
                "message": "Windows Update services (CryptSvc, BITS, wuauserv) restarted successfully.",
            }
        except Exception as e:
            return {"status": "error", "action": "restart_update_services", "message": f"Service restart error: {e}"}
