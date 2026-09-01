"""Repair Planner Engine for Generating Safe, Ordered Repair Action Plans."""
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

from backend.core.logger import get_logger
from backend.problem_solver.models import (
    ProblemCategory, RepairPlan, RepairStep, RiskLevel, RootCauseAnalysis
)

logger = get_logger("RepairPlanner")


class RepairPlanner:
    """Transforms RootCauseAnalysis into safe, sequenced, risk-assessed RepairPlans."""

    @staticmethod
    def create_plan(rca: RootCauseAnalysis, custom_preview: Optional[Dict[str, Any]] = None) -> RepairPlan:
        """Construct an ordered, verified RepairPlan."""
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        cat = rca.category
        primary = rca.primary_cause
        repair_type = primary.recommended_repair_type if primary else "generic_check"

        steps: List[RepairStep] = []
        requires_confirmation = False
        requires_restart = False
        requires_admin = False
        overall_risk = RiskLevel.LOW
        title = f"Repair: {primary.title if primary else 'System Check'}"
        summary = f"Plan to address {primary.title if primary else 'detected issues'}."

        if repair_type == "restart_bluetooth_service":
            steps.append(RepairStep(
                step_id=1,
                name="Restart Bluetooth Services",
                description="Restart Windows Bluetooth Support Service (bthserv).",
                risk_level=RiskLevel.LOW,
                requires_admin=False,
                action_type="restart_bluetooth_services",
            ))
            steps.append(RepairStep(
                step_id=2,
                name="Reinitialize Adapter",
                description="Re-enable Bluetooth hardware adapter device.",
                risk_level=RiskLevel.LOW,
                requires_admin=False,
                action_type="reinitialize_bluetooth_adapter",
            ))
            summary = "Restart Windows Bluetooth services and re-enable hardware adapter."

        elif repair_type == "reinitialize_bluetooth_adapter":
            steps.append(RepairStep(
                step_id=1,
                name="Reinitialize Adapter",
                description="Cycle Bluetooth adapter device state in Windows Device Manager.",
                risk_level=RiskLevel.LOW,
                requires_admin=False,
                action_type="reinitialize_bluetooth_adapter",
            ))
            steps.append(RepairStep(
                step_id=2,
                name="Restart Bluetooth Services",
                description="Restart bthserv to re-bind device stack.",
                risk_level=RiskLevel.LOW,
                requires_admin=False,
                action_type="restart_bluetooth_services",
            ))
            summary = "Reinitialize Bluetooth adapter and reload Windows services."

        elif repair_type == "flush_dns":
            steps.append(RepairStep(
                step_id=1,
                name="Flush DNS Resolver Cache",
                description="Clear and re-register Windows DNS resolver entries.",
                risk_level=RiskLevel.LOW,
                requires_admin=False,
                action_type="flush_dns",
            ))
            summary = "Flush local DNS cache and refresh domain name resolution."

        elif repair_type == "renew_dhcp_ip":
            steps.append(RepairStep(
                step_id=1,
                name="Flush DNS Resolver Cache",
                description="Clear stale DNS cache.",
                risk_level=RiskLevel.LOW,
                requires_admin=False,
                action_type="flush_dns",
            ))
            steps.append(RepairStep(
                step_id=2,
                name="Renew DHCP IP Lease",
                description="Request a fresh IP lease from local gateway router.",
                risk_level=RiskLevel.LOW,
                requires_admin=False,
                action_type="renew_dhcp_ip",
            ))
            summary = "Flush DNS and request fresh IP address configuration from router."

        elif repair_type == "restart_network_adapter":
            steps.append(RepairStep(
                step_id=1,
                name="Restart Network Adapter",
                description="Soft-restart Wi-Fi/Ethernet network interface.",
                risk_level=RiskLevel.MEDIUM,
                requires_admin=False,
                action_type="restart_network_adapter",
            ))
            steps.append(RepairStep(
                step_id=2,
                name="Flush DNS Cache",
                description="Flush resolver cache after adapter restart.",
                risk_level=RiskLevel.LOW,
                requires_admin=False,
                action_type="flush_dns",
            ))
            overall_risk = RiskLevel.MEDIUM
            summary = "Soft-restart active network adapter and refresh DNS cache."

        elif repair_type == "restart_audio_services":
            steps.append(RepairStep(
                step_id=1,
                name="Restart Windows Audio Services",
                description="Restart Audiosrv and AudioEndpointBuilder.",
                risk_level=RiskLevel.LOW,
                requires_admin=False,
                action_type="restart_audio_services",
            ))
            steps.append(RepairStep(
                step_id=2,
                name="Unmute Audio Endpoint",
                description="Ensure system master volume is unmuted.",
                risk_level=RiskLevel.LOW,
                requires_admin=False,
                action_type="unmute_system_audio",
            ))
            summary = "Restart Windows Audio subsystem services and verify volume levels."

        elif repair_type == "unmute_system_audio":
            steps.append(RepairStep(
                step_id=1,
                name="Unmute Master Audio",
                description="Unmute audio endpoint and restore audible volume.",
                risk_level=RiskLevel.LOW,
                requires_admin=False,
                action_type="unmute_system_audio",
            ))
            summary = "Restore audio output volume and unmute speakers."

        elif repair_type == "terminate_hung_processes":
            steps.append(RepairStep(
                step_id=1,
                name="Terminate Hung Processes",
                description="Safely terminate unresponsive background zombie tasks.",
                risk_level=RiskLevel.LOW,
                requires_admin=False,
                action_type="terminate_hung_processes",
            ))
            summary = "Close hung background tasks to relieve CPU and memory load."

        elif repair_type == "clean_temporary_files":
            steps.append(RepairStep(
                step_id=1,
                name="Clean Temporary Files",
                description="Safely purge temporary cache files without touching user files.",
                risk_level=RiskLevel.LOW,
                requires_admin=False,
                action_type="clean_temporary_files",
            ))
            summary = "Clean temporary system files and free up disk space."

        elif repair_type == "verify_clean_npm_cache":
            steps.append(RepairStep(
                step_id=1,
                name="Verify NPM Cache",
                description="Run npm cache verification and garbage collection.",
                risk_level=RiskLevel.LOW,
                requires_admin=False,
                action_type="verify_clean_npm_cache",
            ))
            summary = "Verify and clean corrupted NPM package manager cache."

        else:
            steps.append(RepairStep(
                step_id=1,
                name="System Diagnostic Health Check",
                description="Verify component health metrics.",
                risk_level=RiskLevel.LOW,
                action_type="system_health_check",
            ))

        return RepairPlan(
            plan_id=plan_id,
            category=cat,
            created_at=datetime.now(),
            title=title,
            summary=summary,
            risk_level=overall_risk,
            requires_confirmation=requires_confirmation or overall_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL],
            requires_restart=requires_restart,
            requires_admin=requires_admin,
            steps=steps,
            preview_data=custom_preview,
            rollback_available=True,
        )
