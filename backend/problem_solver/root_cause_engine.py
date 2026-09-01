"""Root Cause Analysis (RCA) and Hypothesis Ranking Engine."""
import re
from typing import Any, Dict, List, Optional
from datetime import datetime

from backend.core.logger import get_logger
from backend.problem_solver.models import (
    DiagnosticReport, DiagnosticStatus, ProblemCategory,
    RootCauseAnalysis, RootCauseHypothesis
)
from backend.problem_solver.safety import CommandSafetyEngine

logger = get_logger("RootCauseEngine")


class RootCauseEngine:
    """Formulates, ranks, and synthesizes root-cause hypotheses from collected diagnostic evidence."""

    @staticmethod
    def analyze_error_text(error_text: str) -> RootCauseHypothesis:
        """Analyze copied terminal or Windows error strings to extract root cause."""
        cleaned = CommandSafetyEngine.redact_sensitive_data(error_text)
        lowered = cleaned.lower()

        if "econnrefused" in lowered or "connection refused" in lowered:
            return RootCauseHypothesis(
                rank=1,
                title="Connection Refused / Port Offline",
                confidence=0.92,
                explanation="The target server or localhost port is not running or rejecting TCP handshakes.",
                evidence_keys=["error_text"],
                recommended_repair_type="restart_network_adapter",
            )
        elif "module_not_found" in lowered or "cannot find module" in lowered or "no module named" in lowered:
            return RootCauseHypothesis(
                rank=1,
                title="Missing Dependency / Package Not Installed",
                confidence=0.95,
                explanation="A required software dependency or module is missing from the environment.",
                evidence_keys=["error_text"],
                recommended_repair_type="verify_clean_npm_cache",
            )
        elif "enospc" in lowered or "no space left on device" in lowered or "disk full" in lowered:
            return RootCauseHypothesis(
                rank=1,
                title="Disk Storage Full",
                confidence=0.98,
                explanation="No disk space left on the target partition to write files.",
                evidence_keys=["error_text"],
                recommended_repair_type="clean_temporary_files",
            )
        elif "code 43" in lowered or "error 43" in lowered:
            return RootCauseHypothesis(
                rank=1,
                title="Device Driver Fault (Code 43)",
                confidence=0.95,
                explanation="Windows Device Manager stopped the device because it reported a driver/hardware crash.",
                evidence_keys=["error_text"],
                recommended_repair_type="reinitialize_bluetooth_adapter",
            )
        else:
            return RootCauseHypothesis(
                rank=1,
                title="Runtime Error Detected",
                confidence=0.75,
                explanation=cleaned[:180],
                evidence_keys=["error_text"],
                recommended_repair_type="system_health_check",
            )

    @staticmethod
    def analyze(report: DiagnosticReport, raw_error_text: Optional[str] = None) -> RootCauseAnalysis:
        """Derive prioritized root cause hypotheses from a DiagnosticReport."""
        cat = report.category
        evidence = report.raw_evidence
        items = report.items
        hypotheses: List[RootCauseHypothesis] = []

        if raw_error_text and len(raw_error_text.strip()) > 10:
            hypotheses.append(RootCauseEngine.analyze_error_text(raw_error_text))

        if cat == ProblemCategory.BLUETOOTH:
            bth_srv = evidence.get("services", {}).get("bthserv", {}).get("status")
            pnp_devs = evidence.get("pnp_devices", [])
            adapter_errors = [d for d in pnp_devs if d.get("Status") != "OK" or d.get("Problem", 0) != 0]

            if bth_srv != "running":
                hypotheses.append(RootCauseHypothesis(
                    rank=len(hypotheses) + 1,
                    title="Windows Bluetooth Service Stopped",
                    confidence=0.95,
                    explanation="The core 'bthserv' Windows service is stopped or failed to initialize.",
                    evidence_keys=["services.bthserv"],
                    recommended_repair_type="restart_bluetooth_service",
                ))
            if adapter_errors:
                err_code = adapter_errors[0].get("Problem", 43)
                hypotheses.append(RootCauseHypothesis(
                    rank=len(hypotheses) + 1,
                    title=f"Bluetooth Hardware / Driver Error (Code {err_code})",
                    confidence=0.90,
                    explanation=f"Device Manager is reporting error Code {err_code} on adapter '{adapter_errors[0].get('FriendlyName')}'.",
                    evidence_keys=["pnp_devices"],
                    recommended_repair_type="reinitialize_bluetooth_adapter",
                ))
            if not pnp_devs:
                hypotheses.append(RootCauseHypothesis(
                    rank=len(hypotheses) + 1,
                    title="Bluetooth Hardware Disabled or Radio Off",
                    confidence=0.85,
                    explanation="No Bluetooth PnP controller is responding on the system bus.",
                    evidence_keys=["pnp_devices"],
                    recommended_repair_type="reinitialize_bluetooth_adapter",
                ))

        elif cat in [ProblemCategory.WIFI_NETWORK, ProblemCategory.INTERNET]:
            adapters = evidence.get("adapters", [])
            gateway_ip = evidence.get("gateway_ip")
            internet_direct = evidence.get("internet_direct", False)
            resolved_google = evidence.get("resolved_google")

            if not adapters:
                hypotheses.append(RootCauseHypothesis(
                    rank=len(hypotheses) + 1,
                    title="Network Adapter Disconnected or Disabled",
                    confidence=0.95,
                    explanation="No network interface has an active link or valid IP address.",
                    evidence_keys=["adapters"],
                    recommended_repair_type="restart_network_adapter",
                ))
            elif not internet_direct and gateway_ip:
                hypotheses.append(RootCauseHypothesis(
                    rank=len(hypotheses) + 1,
                    title="Router / ISP Internet Link Down",
                    confidence=0.90,
                    explanation="Connected to local router gateway, but upstream internet packets are blocked.",
                    evidence_keys=["gateway_ip", "internet_direct"],
                    recommended_repair_type="renew_dhcp_ip",
                ))
            elif internet_direct and not resolved_google:
                hypotheses.append(RootCauseHypothesis(
                    rank=len(hypotheses) + 1,
                    title="DNS Resolver Failure",
                    confidence=0.95,
                    explanation="Direct IP internet connection works, but domain names cannot be resolved.",
                    evidence_keys=["resolved_google", "internet_direct"],
                    recommended_repair_type="flush_dns",
                ))
            else:
                hypotheses.append(RootCauseHypothesis(
                    rank=len(hypotheses) + 1,
                    title="Network Adapter Cache / Routing Stale",
                    confidence=0.80,
                    explanation="Adapter is active but experiencing packet loss or stale DHCP leases.",
                    evidence_keys=["adapters"],
                    recommended_repair_type="restart_network_adapter",
                ))

        elif cat == ProblemCategory.AUDIO:
            audio_srv = evidence.get("audio_services", {})
            if audio_srv.get("Audiosrv") != "running" or audio_srv.get("AudioEndpointBuilder") != "running":
                hypotheses.append(RootCauseHypothesis(
                    rank=len(hypotheses) + 1,
                    title="Windows Audio Service Disabled",
                    confidence=0.95,
                    explanation="The Windows Audiosrv or AudioEndpointBuilder service is inactive.",
                    evidence_keys=["audio_services"],
                    recommended_repair_type="restart_audio_services",
                ))
            else:
                hypotheses.append(RootCauseHypothesis(
                    rank=len(hypotheses) + 1,
                    title="Audio Output Muted or Wrong Default Device",
                    confidence=0.85,
                    explanation="Windows Audio services are running; output may be muted or directed to an offline device.",
                    evidence_keys=["audio_devices"],
                    recommended_repair_type="unmute_system_audio",
                ))

        elif cat in [ProblemCategory.PERFORMANCE_HANG, ProblemCategory.SLOW_SYSTEM]:
            cpu_pct = evidence.get("cpu_percent", 0)
            ram_pct = evidence.get("ram_percent", 0)
            if cpu_pct >= 85:
                hypotheses.append(RootCauseHypothesis(
                    rank=len(hypotheses) + 1,
                    title="CPU Overload / Hung Background Task",
                    confidence=0.90,
                    explanation=f"CPU usage is at {cpu_pct}%, likely from runaway background threads.",
                    evidence_keys=["cpu_percent"],
                    recommended_repair_type="terminate_hung_processes",
                ))
            elif ram_pct >= 85:
                hypotheses.append(RootCauseHypothesis(
                    rank=len(hypotheses) + 1,
                    title="RAM Memory Exhaustion / Heavy Multitasking",
                    confidence=0.88,
                    explanation=f"RAM saturation at {ram_pct}% is causing page file thrashing.",
                    evidence_keys=["ram_percent"],
                    recommended_repair_type="terminate_hung_processes",
                ))
            else:
                hypotheses.append(RootCauseHypothesis(
                    rank=len(hypotheses) + 1,
                    title="High Startup Load / Idle Cache Accumulation",
                    confidence=0.75,
                    explanation="Excessive startup programs and background services slowing down response times.",
                    evidence_keys=["startup_count"],
                    recommended_repair_type="terminate_hung_processes",
                ))

        elif cat == ProblemCategory.STORAGE:
            hypotheses.append(RootCauseHypothesis(
                rank=len(hypotheses) + 1,
                title="Temporary File and Cache Accumulation",
                confidence=0.90,
                explanation="Significant space occupied by temporary directory caches and deleted files.",
                evidence_keys=["temp_files"],
                recommended_repair_type="clean_temporary_files",
            ))

        elif cat == ProblemCategory.DEV_ENVIRONMENT:
            hypotheses.append(RootCauseHypothesis(
                rank=len(hypotheses) + 1,
                title="Tool Not Found in PATH / NPM Cache Corruption",
                confidence=0.90,
                explanation="Required CLI executable is missing from Windows PATH or NPM cache is locked.",
                evidence_keys=["tools"],
                recommended_repair_type="verify_clean_npm_cache",
            ))

        if not hypotheses:
            hypotheses.append(RootCauseHypothesis(
                rank=1,
                title="General System Component Status",
                confidence=0.70,
                explanation=report.summary,
                evidence_keys=[],
                recommended_repair_type="system_health_check",
            ))

        primary = hypotheses[0]
        secondaries = hypotheses[1:] if len(hypotheses) > 1 else []

        summary_text = (
            f"Likely Root Cause: {primary.title} (Confidence: {int(primary.confidence * 100)}%). {primary.explanation}"
            if primary else "No clear root cause isolated."
        )

        return RootCauseAnalysis(
            category=cat,
            timestamp=datetime.now(),
            primary_cause=primary,
            secondary_hypotheses=secondaries,
            summary=summary_text,
            requires_gemini_reasoning=primary.confidence < 0.80 if primary else True,
        )
