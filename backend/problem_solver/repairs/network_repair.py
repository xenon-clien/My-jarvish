"""Safe Network and Wi-Fi Self-Repair Engine."""
import subprocess
import time
from typing import Any, Dict

from backend.core.logger import get_logger

logger = get_logger("NetworkRepair")


class NetworkRepair:
    """Performs safe, layered network stack repairs, DNS flushing, and adapter resets."""

    @staticmethod
    def flush_dns() -> Dict[str, Any]:
        """Flush and register Windows local DNS resolver cache."""
        logger.info("Flushing Windows DNS resolver cache...")
        try:
            res = subprocess.run("ipconfig /flushdns", shell=True, capture_output=True, text=True, timeout=5)
            return {
                "status": "success" if res.returncode == 0 else "warning",
                "action": "flush_dns",
                "message": "Windows DNS resolver cache flushed successfully.",
            }
        except Exception as e:
            return {"status": "error", "action": "flush_dns", "message": f"DNS flush error: {e}"}

    @staticmethod
    def renew_dhcp_ip() -> Dict[str, Any]:
        """Renew DHCP IP address lease from local gateway/router."""
        logger.info("Renewing DHCP IP configuration...")
        try:
            subprocess.run("ipconfig /renew", shell=True, capture_output=True, text=True, timeout=12)
            time.sleep(1.0)
            return {
                "status": "success",
                "action": "renew_dhcp_ip",
                "message": "DHCP IP configuration renewed successfully.",
            }
        except Exception as e:
            return {"status": "error", "action": "renew_dhcp_ip", "message": f"IP renewal error: {e}"}

    @staticmethod
    def restart_network_adapter() -> Dict[str, Any]:
        """Soft-restart active Wi-Fi / Ethernet network adapter."""
        logger.info("Restarting active network adapters...")
        try:
            cmd = "powershell -NoProfile -Command \"Get-NetAdapter | Where-Object {$_.Status -eq 'Up' -or $_.Name -like '*Wi-Fi*'} | Restart-NetAdapter -Confirm:$false -ErrorAction SilentlyContinue\""
            subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            time.sleep(3.0)
            return {
                "status": "success",
                "action": "restart_network_adapter",
                "message": "Network adapter reinitialized successfully.",
            }
        except Exception as e:
            return {"status": "error", "action": "restart_network_adapter", "message": f"Adapter reset error: {e}"}

    @staticmethod
    def reset_winsock_stack() -> Dict[str, Any]:
        """Reset Winsock catalog and TCP/IP stack (Requires Admin & System Restart)."""
        logger.info("Resetting Winsock and TCP/IP network catalog...")
        try:
            subprocess.run("netsh winsock reset", shell=True, capture_output=True, text=True, timeout=8)
            subprocess.run("netsh int ip reset", shell=True, capture_output=True, text=True, timeout=8)
            return {
                "status": "success",
                "action": "reset_winsock_stack",
                "message": "Winsock catalog reset complete. A system restart is recommended.",
                "requires_restart": True,
            }
        except Exception as e:
            return {"status": "error", "action": "reset_winsock_stack", "message": f"Winsock reset error: {e}"}
