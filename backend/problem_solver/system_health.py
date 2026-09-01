"""Master System Health Diagnostic Engine for Universal PC Health Overview."""
from datetime import datetime
from typing import Any, Dict, List, Optional
import psutil

from backend.core.logger import get_logger
from backend.problem_solver.models import (
    DiagnosticItem, DiagnosticReport, DiagnosticStatus, ProblemCategory
)
from backend.problem_solver.diagnostics.bluetooth_diagnostic import BluetoothDiagnostic
from backend.problem_solver.diagnostics.wifi_network_diagnostic import WiFiNetworkDiagnostic
from backend.problem_solver.diagnostics.audio_diagnostic import AudioDiagnostic
from backend.problem_solver.diagnostics.performance_diagnostic import PerformanceDiagnostic
from backend.problem_solver.diagnostics.storage_diagnostic import StorageDiagnostic
from backend.problem_solver.diagnostics.display_diagnostic import DisplayDiagnostic
from backend.problem_solver.diagnostics.windows_update_diagnostic import WindowsUpdateDiagnostic

logger = get_logger("SystemHealthEngine")


class SystemHealthEngine:
    """Orchestrates full-system hardware, Windows OS, network, and driver health scans."""

    @staticmethod
    def get_full_health_report() -> Dict[str, Any]:
        """Run comprehensive system health inspection across all hardware and OS subsystems."""
        logger.info("Initiating full JARVIS System Health scan...")

        # 1. Run all sub-diagnostics
        perf_rep = PerformanceDiagnostic.run_diagnostic()
        storage_rep = StorageDiagnostic.run_diagnostic()
        net_rep = WiFiNetworkDiagnostic.run_diagnostic()
        bt_rep = BluetoothDiagnostic.run_diagnostic()
        audio_rep = AudioDiagnostic.run_diagnostic()
        disp_rep = DisplayDiagnostic.run_diagnostic()
        update_rep = WindowsUpdateDiagnostic.run_diagnostic()

        # 2. Battery & Power Check
        battery = psutil.sensors_battery()
        bat_info = "Desktop / AC Power"
        bat_pct = 100
        if battery:
            bat_pct = battery.percent
            plug_str = "Charging" if battery.power_plugged else "On Battery"
            bat_info = f"{bat_pct}% ({plug_str})"

        # 3. Aggregate Component Summaries
        components = {
            "CPU": "High Load" if perf_rep.raw_evidence.get("cpu_percent", 0) >= 85 else "Normal",
            "RAM": f"{perf_rep.raw_evidence.get('ram_percent', 0)}% Usage",
            "Storage": f"{storage_rep.raw_evidence.get('drives', [{}])[0].get('free_gb', 'N/A')} GB Free" if storage_rep.raw_evidence.get("drives") else "Normal",
            "Bluetooth": "Problem Detected" if bt_rep.overall_status == DiagnosticStatus.PROBLEM_DETECTED else "Normal",
            "Wi-Fi & Internet": "Online" if net_rep.overall_status == DiagnosticStatus.HEALTHY else "Offline / Issue Detected",
            "Audio": "Normal" if audio_rep.overall_status == DiagnosticStatus.HEALTHY else "Problem Detected",
            "GPU & Display": "Normal" if disp_rep.overall_status == DiagnosticStatus.HEALTHY else "Warning",
            "Windows Update": "Restart Pending" if update_rep.raw_evidence.get("reboot_pending") else "Normal",
            "Battery": bat_info,
        }

        # 4. Count detected issues
        issues_found = []
        if bt_rep.overall_status == DiagnosticStatus.PROBLEM_DETECTED:
            issues_found.append(("Bluetooth", bt_rep.summary))
        if net_rep.overall_status == DiagnosticStatus.PROBLEM_DETECTED:
            issues_found.append(("Network/Internet", net_rep.summary))
        if audio_rep.overall_status == DiagnosticStatus.PROBLEM_DETECTED:
            issues_found.append(("Audio", audio_rep.summary))
        if perf_rep.overall_status == DiagnosticStatus.PROBLEM_DETECTED:
            issues_found.append(("Performance", perf_rep.summary))
        if storage_rep.overall_status == DiagnosticStatus.PROBLEM_DETECTED:
            issues_found.append(("Storage", storage_rep.summary))

        # 5. Build Human-Readable Clean Summary
        report_lines = [
            "🛡️ **JARVIS SYSTEM HEALTH REPORT**",
            f"• **CPU:** {components['CPU']}",
            f"• **RAM:** {components['RAM']}",
            f"• **Storage:** {components['Storage']}",
            f"• **Bluetooth:** {components['Bluetooth']}",
            f"• **Wi-Fi & Internet:** {components['Wi-Fi & Internet']}",
            f"• **Audio:** {components['Audio']}",
            f"• **GPU & Display:** {components['GPU & Display']}",
            f"• **Windows Update:** {components['Windows Update']}",
            f"• **Battery:** {components['Battery']}",
        ]

        if issues_found:
            report_lines.append(f"\n⚠️ **Detected {len(issues_found)} issue(s):**")
            for comp, iss in issues_found:
                report_lines.append(f"  - **{comp}**: {iss}")
            report_lines.append("\nKya aap chahte hain ki main in problems ko step-by-step diagnose aur repair karu?")
        else:
            report_lines.append("\n✅ **All systems are functioning normally and healthy!**")

        full_text = "\n".join(report_lines)

        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "components": components,
            "issues_count": len(issues_found),
            "issues": [{"component": c, "summary": s} for c, s in issues_found],
            "formatted_report": full_text,
            "sub_reports": {
                "performance": perf_rep.model_dump(),
                "storage": storage_rep.model_dump(),
                "network": net_rep.model_dump(),
                "bluetooth": bt_rep.model_dump(),
                "audio": audio_rep.model_dump(),
                "display": disp_rep.model_dump(),
                "windows_update": update_rep.model_dump(),
            }
        }
