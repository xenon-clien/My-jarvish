"""Wi-Fi and Internet Diagnostic Engine with Multi-layer Root Cause Isolation."""
import socket
import subprocess
import time
from typing import Any, Dict, List, Optional
import psutil

from backend.core.logger import get_logger
from backend.problem_solver.models import (
    DiagnosticItem, DiagnosticReport, DiagnosticStatus, ProblemCategory
)

logger = get_logger("WiFiNetworkDiagnostic")


class WiFiNetworkDiagnostic:
    """Performs deep 6-layer network troubleshooting to isolate Wi-Fi and internet failures."""

    @staticmethod
    def run_diagnostic(target_url: Optional[str] = None) -> DiagnosticReport:
        """Execute comprehensive network stack diagnostic."""
        items: List[DiagnosticItem] = []
        raw_evidence: Dict[str, Any] = {}
        overall_status = DiagnosticStatus.HEALTHY
        summary_points = []
        failed_layer: Optional[str] = None

        # -------------------------------------------------------------
        # Layer 1: Network Adapters & Interface Status
        # -------------------------------------------------------------
        net_stats = psutil.net_if_stats()
        net_addrs = psutil.net_if_addrs()
        active_adapters = []
        wifi_adapter_found = False
        wifi_is_up = False

        for iface_name, stats in net_stats.items():
            is_up = stats.isup
            speed = stats.speed
            is_wifi = any(w in iface_name.lower() for w in ["wi-fi", "wifi", "wireless", "wlan"])
            if is_wifi:
                wifi_adapter_found = True
                if is_up:
                    wifi_is_up = True

            addrs = net_addrs.get(iface_name, [])
            ip_v4 = [a.address for a in addrs if a.family == socket.AF_INET and not a.address.startswith("127.")]
            if is_up and ip_v4:
                active_adapters.append({
                    "name": iface_name,
                    "ip": ip_v4[0],
                    "speed_mbps": speed,
                    "is_wifi": is_wifi,
                })

        raw_evidence["adapters"] = active_adapters
        raw_evidence["wifi_found"] = wifi_adapter_found
        raw_evidence["wifi_up"] = wifi_is_up

        if not active_adapters:
            items.append(DiagnosticItem(
                name="Network Interfaces",
                status=DiagnosticStatus.PROBLEM_DETECTED,
                value="No Active Connected Network Interface",
                details="No network adapter has an active IP address or cable/radio connection.",
            ))
            overall_status = DiagnosticStatus.PROBLEM_DETECTED
            summary_points.append("No active network adapter connected")
            failed_layer = failed_layer or "adapter"
        else:
            primary = active_adapters[0]
            items.append(DiagnosticItem(
                name="Active Network Adapter",
                status=DiagnosticStatus.HEALTHY,
                value=f"{primary['name']} ({primary['ip']})",
                details=f"Connected at {primary['speed_mbps']} Mbps.",
            ))

        # -------------------------------------------------------------
        # Layer 2: Default Gateway Reachability
        # -------------------------------------------------------------
        gateway_ip = None
        gateway_reachable = False
        try:
            # Get default gateway via netsh / route
            res = subprocess.run("powershell -NoProfile -Command \"Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Select-Object -ExpandProperty NextHop\"", shell=True, capture_output=True, text=True, timeout=4)
            if res.returncode == 0 and res.stdout.strip():
                gateway_ip = res.stdout.strip().split("\n")[0].strip()
        except Exception:
            pass

        raw_evidence["gateway_ip"] = gateway_ip

        if gateway_ip and gateway_ip not in ["0.0.0.0", ""]:
            # Test socket or ping to gateway
            try:
                ping_res = subprocess.run(f"ping -n 1 -w 1000 {gateway_ip}", shell=True, capture_output=True, text=True, timeout=2)
                if ping_res.returncode == 0 and "TTL=" in ping_res.stdout.upper():
                    gateway_reachable = True
            except Exception:
                gateway_reachable = False

            if gateway_reachable:
                items.append(DiagnosticItem(
                    name="Default Gateway (Router)",
                    status=DiagnosticStatus.HEALTHY,
                    value=f"Reachable ({gateway_ip})",
                    details="Local router gateway responded successfully.",
                ))
            else:
                items.append(DiagnosticItem(
                    name="Default Gateway (Router)",
                    status=DiagnosticStatus.WARNING,
                    value=f"Unreachable ({gateway_ip})",
                    details="Router gateway did not respond to local ping.",
                ))
                overall_status = DiagnosticStatus.PROBLEM_DETECTED
                summary_points.append("Default Gateway / Router is unreachable")
                failed_layer = failed_layer or "gateway"
        else:
            items.append(DiagnosticItem(
                name="Default Gateway (Router)",
                status=DiagnosticStatus.WARNING,
                value="Not Configured",
                details="No default route gateway found in Windows routing table.",
            ))

        # -------------------------------------------------------------
        # Layer 3: Direct DNS Resolution
        # -------------------------------------------------------------
        dns_working = False
        try:
            resolved_ip = socket.gethostbyname("google.com")
            dns_working = bool(resolved_ip)
            raw_evidence["resolved_google"] = resolved_ip
        except Exception:
            dns_working = False

        if dns_working:
            items.append(DiagnosticItem(
                name="DNS Resolution",
                status=DiagnosticStatus.HEALTHY,
                value="Working",
                details="DNS successfully resolved domain names to IP addresses.",
            ))
        else:
            items.append(DiagnosticItem(
                name="DNS Resolution",
                status=DiagnosticStatus.PROBLEM_DETECTED,
                value="Failing",
                details="Cannot resolve domain names. DNS servers may be unresponsive.",
            ))
            overall_status = DiagnosticStatus.PROBLEM_DETECTED
            summary_points.append("DNS Resolution failure")
            failed_layer = failed_layer or "dns"

        # -------------------------------------------------------------
        # Layer 4: Global Internet Connectivity (Direct Socket to 8.8.8.8:53 & 1.1.1.1:53)
        # -------------------------------------------------------------
        internet_direct = False
        for test_ip in ["8.8.8.8", "1.1.1.1"]:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2.0)
                s.connect((test_ip, 53))
                s.close()
                internet_direct = True
                break
            except Exception:
                continue

        raw_evidence["internet_direct"] = internet_direct

        if internet_direct:
            items.append(DiagnosticItem(
                name="Global Internet Connection",
                status=DiagnosticStatus.HEALTHY,
                value="Connected (Online)",
                details="Direct IP connection to global internet DNS root established.",
            ))
        else:
            items.append(DiagnosticItem(
                name="Global Internet Connection",
                status=DiagnosticStatus.PROBLEM_DETECTED,
                value="No Internet Access (Offline)",
                details="Direct IP packet communication to global internet failed.",
            ))
            overall_status = DiagnosticStatus.PROBLEM_DETECTED
            summary_points.append("No global internet access")
            failed_layer = failed_layer or "internet"

        # -------------------------------------------------------------
        # Layer 5: Target Site Reachability (if specific site was requested)
        # -------------------------------------------------------------
        if target_url:
            clean_host = target_url.replace("https://", "").replace("http://", "").split("/")[0]
            site_ok = False
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(3.0)
                s.connect((clean_host, 443))
                s.close()
                site_ok = True
            except Exception:
                site_ok = False

            if site_ok:
                items.append(DiagnosticItem(
                    name=f"Target Site: {clean_host}",
                    status=DiagnosticStatus.HEALTHY,
                    value="Reachable",
                    details=f"Successfully connected to {clean_host}:443.",
                ))
            else:
                items.append(DiagnosticItem(
                    name=f"Target Site: {clean_host}",
                    status=DiagnosticStatus.PROBLEM_DETECTED,
                    value="Unreachable",
                    details=f"Connection to {clean_host} failed while internet is {'online' if internet_direct else 'offline'}.",
                ))
                if internet_direct:
                    summary_points.append(f"Only the specific website '{clean_host}' is unavailable")
                    failed_layer = "website_specific"

        if overall_status == DiagnosticStatus.HEALTHY:
            summary = "Wi-Fi network connection and global internet access are fully functional."
        else:
            summary = f"Network issue detected: {'; '.join(summary_points)}."

        return DiagnosticReport(
            category=ProblemCategory.INTERNET if failed_layer in ["internet", "dns", "website_specific"] else ProblemCategory.WIFI_NETWORK,
            overall_status=overall_status,
            summary=summary,
            items=items,
            raw_evidence=raw_evidence,
            suggested_focus=failed_layer or "network_adapter",
        )
