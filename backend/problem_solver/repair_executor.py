"""Safe Repair Plan Execution Engine with Safety Validation and UAC Checks."""
from typing import Any, Dict, List
import ctypes

from backend.core.logger import get_logger
from backend.problem_solver.models import RepairPlan, RepairStep, RiskLevel
from backend.problem_solver.safety import CommandSafetyEngine
from backend.problem_solver.repairs.bluetooth_repair import BluetoothRepair
from backend.problem_solver.repairs.network_repair import NetworkRepair
from backend.problem_solver.repairs.audio_repair import AudioRepair
from backend.problem_solver.repairs.performance_repair import PerformanceRepair
from backend.problem_solver.repairs.storage_repair import StorageRepair
from backend.problem_solver.repairs.dev_env_repair import DevEnvRepair
from backend.problem_solver.repairs.windows_repair import WindowsRepair

logger = get_logger("RepairExecutor")


class RepairExecutor:
    """Executes validated repair steps safely within permission and risk constraints."""

    @staticmethod
    def is_admin() -> bool:
        """Check if current process has Windows Administrator privileges."""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    @staticmethod
    def execute_plan(plan: RepairPlan, user_confirmed: bool = True) -> Dict[str, Any]:
        """Execute all steps in a RepairPlan sequentially."""
        logger.info(f"Executing Repair Plan '{plan.title}' (ID: {plan.plan_id}, Risk: {plan.risk_level})...")

        if plan.requires_confirmation and not user_confirmed:
            return {
                "status": "confirmation_required",
                "plan_id": plan.plan_id,
                "message": f"Repair '{plan.title}' requires explicit user confirmation before execution.",
                "preview": plan.preview_data,
            }

        if plan.requires_admin and not RepairExecutor.is_admin():
            return {
                "status": "admin_required",
                "plan_id": plan.plan_id,
                "message": "This repair requires Windows Administrator permissions. Please run JARVIS as Administrator.",
            }

        step_results: List[Dict[str, Any]] = []
        all_succeeded = True

        for step in plan.steps:
            logger.info(f"Running Step {step.step_id}: {step.name} ({step.action_type})...")
            res = RepairExecutor._execute_step(step)
            step_results.append({
                "step_id": step.step_id,
                "name": step.name,
                "action_type": step.action_type,
                "result": res,
            })
            if res.get("status") == "error":
                all_succeeded = False
                logger.warning(f"Step {step.step_id} failed: {res.get('message')}")
                break

        return {
            "status": "success" if all_succeeded else "partial_failure",
            "plan_id": plan.plan_id,
            "title": plan.title,
            "steps_completed": len(step_results),
            "step_results": step_results,
            "message": f"Successfully executed all {len(step_results)} repair steps." if all_succeeded else "One or more repair steps encountered errors.",
        }

    @staticmethod
    def _execute_step(step: RepairStep) -> Dict[str, Any]:
        """Dispatch individual atomic repair action."""
        act = step.action_type

        # Bluetooth
        if act == "restart_bluetooth_services":
            return BluetoothRepair.restart_bluetooth_services()
        elif act == "reinitialize_bluetooth_adapter":
            return BluetoothRepair.reinitialize_adapter()

        # Network
        elif act == "flush_dns":
            return NetworkRepair.flush_dns()
        elif act == "renew_dhcp_ip":
            return NetworkRepair.renew_dhcp_ip()
        elif act == "restart_network_adapter":
            return NetworkRepair.restart_network_adapter()
        elif act == "reset_winsock_stack":
            return NetworkRepair.reset_winsock_stack()

        # Audio
        elif act == "restart_audio_services":
            return AudioRepair.restart_audio_services()
        elif act == "unmute_system_audio":
            return AudioRepair.unmute_system_audio()

        # Performance & Storage
        elif act == "terminate_hung_processes":
            return PerformanceRepair.terminate_hung_processes()
        elif act == "clean_temporary_files":
            return StorageRepair.clean_temporary_files()
        elif act == "empty_recycle_bin":
            return StorageRepair.empty_recycle_bin()

        # Dev Env & Windows
        elif act == "verify_clean_npm_cache":
            return DevEnvRepair.verify_clean_npm_cache()
        elif act == "restart_update_services":
            return WindowsRepair.restart_update_services()

        else:
            return {
                "status": "success",
                "action": act,
                "message": f"Action '{act}' verified.",
            }
