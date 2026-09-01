"""Structured Knowledge Base for Common PC Hardware, Windows OS, and Software Problems."""
from typing import Any, Dict, List, Optional
from backend.problem_solver.models import ProblemCategory, RiskLevel


class ProblemKnowledgeBase:
    """Extensible structured registry of symptoms, possible root causes, diagnostics, safe fixes, and risk levels."""

    _knowledge_map: Dict[ProblemCategory, Dict[str, Any]] = {
        ProblemCategory.BLUETOOTH: {
            "symptoms": ["Bluetooth not connecting", "Bluetooth toggle missing", "Device Manager Code 43", "Bluetooth audio lag"],
            "possible_causes": ["bthserv service stopped", "Adapter disabled in Device Manager", "Driver initialization fault", "Airplane mode active"],
            "diagnostic_engine": "BluetoothDiagnostic",
            "safe_fixes": ["Restart Bluetooth services", "Re-enable PnP adapter", "Hardware rescan"],
            "risk_level": RiskLevel.LOW,
            "verification": "Check bthserv running and adapter status OK",
            "rollback_support": True,
        },
        ProblemCategory.WIFI_NETWORK: {
            "symptoms": ["Wi-Fi disconnected", "No internet access", "DNS probe finished bad config", "Default gateway unreachable"],
            "possible_causes": ["Adapter disabled", "Stale DHCP lease", "DNS cache corruption", "WlanSvc stopped"],
            "diagnostic_engine": "WiFiNetworkDiagnostic",
            "safe_fixes": ["Flush DNS cache", "Renew DHCP IP", "Soft-restart Wi-Fi adapter"],
            "risk_level": RiskLevel.LOW,
            "verification": "Socket ping to 8.8.8.8 and DNS query google.com",
            "rollback_support": True,
        },
        ProblemCategory.AUDIO: {
            "symptoms": ["No sound from speakers", "Microphone not picking voice", "Red X on speaker icon", "Audiosrv stopped"],
            "possible_causes": ["Windows Audio service dead", "Master output muted", "AudioEndpointBuilder crash", "Wrong default playback device"],
            "diagnostic_engine": "AudioDiagnostic",
            "safe_fixes": ["Restart Audiosrv & AudioEndpointBuilder", "Unmute system volume", "Adjust master volume"],
            "risk_level": RiskLevel.LOW,
            "verification": "Audiosrv status running and endpoint unmuted",
            "rollback_support": True,
        },
        ProblemCategory.PERFORMANCE_HANG: {
            "symptoms": ["Laptop freezing", "High CPU spikes", "RAM 90% saturated", "System sluggish on multitasking"],
            "possible_causes": ["Zombie background processes", "Excessive startup applications", "Thermal throttling", "Memory leaks"],
            "diagnostic_engine": "PerformanceDiagnostic",
            "safe_fixes": ["Terminate hung zombie processes", "Clean background standby caches"],
            "risk_level": RiskLevel.LOW,
            "verification": "Check CPU and RAM percentage drops",
            "rollback_support": True,
        },
        ProblemCategory.STORAGE: {
            "symptoms": ["Disk space full", "Low disk space warning on C: drive", "Windows update failed due to storage"],
            "possible_causes": ["Accumulated %TEMP% caches", "Unemptied Recycle Bin", "Large old installer files in Downloads"],
            "diagnostic_engine": "StorageDiagnostic",
            "safe_fixes": ["Clean Windows & User temporary directories", "Empty Recycle Bin"],
            "risk_level": RiskLevel.LOW,
            "verification": "Check free space increase on system drives",
            "rollback_support": False,
        },
        ProblemCategory.DEV_ENVIRONMENT: {
            "symptoms": ["npm command not found", "python not recognized", "git command failed", "node version conflict"],
            "possible_causes": ["Executable missing from PATH", "Corrupted npm cache", "Permission denied in node_modules"],
            "diagnostic_engine": "DevEnvDiagnostic",
            "safe_fixes": ["npm cache verify", "Environment PATH guidance"],
            "risk_level": RiskLevel.LOW,
            "verification": "Check CLI --version command returns 0 exit code",
            "rollback_support": False,
        },
    }

    @classmethod
    def get_info_for_category(cls, category: ProblemCategory) -> Optional[Dict[str, Any]]:
        """Retrieve structured troubleshooting guidelines for a category."""
        return cls._knowledge_map.get(category)
