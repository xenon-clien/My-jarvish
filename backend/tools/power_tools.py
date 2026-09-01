"""Windows Power Management and Session tools (Shutdown, Restart, Sleep, Lock) for JARVIS AI."""
import os
import subprocess
import time
from typing import Any, Dict
from pydantic import BaseModel, Field

from backend.core.logger import get_logger
from backend.core.permissions import PermissionLevel, ToolCategory
from backend.tools.app_tools import clean_unused_apps
from backend.tools.registry import tool

logger = get_logger("PowerTools")


# ==========================================
# Input Schemas
# ==========================================

class ShutdownArgs(BaseModel):
    close_all_apps: bool = Field(True, description="Whether to close all open tabs and applications before shutting down.")
    delay_seconds: int = Field(5, description="Countdown delay in seconds before shutdown executes.")


class RestartArgs(BaseModel):
    close_all_apps: bool = Field(True, description="Whether to close all open tabs and applications before restarting.")
    delay_seconds: int = Field(5, description="Countdown delay in seconds before restart executes.")


# ==========================================
# Power Management Tools
# ==========================================

@tool(
    name="shutdown_pc",
    description="Safely close all open tabs/apps and shut down the Windows laptop/PC. (e.g. 'Laptop shutdown karo', 'Shutdown PC', 'Turn off computer').",
    permission_level=PermissionLevel.LEVEL_1_NORMAL,
    category=ToolCategory.SYSTEM,
    args_schema=ShutdownArgs,
)
def shutdown_pc(close_all_apps: bool = True, delay_seconds: int = 5) -> Dict[str, Any]:
    """Gracefully close all applications and execute Windows shutdown."""
    closed_summary = "None"
    if close_all_apps:
        try:
            cleanup_res = clean_unused_apps(close_browsers=True)
            closed_summary = cleanup_res.get("message", "Closed active applications.")
        except Exception as e:
            logger.warning(f"Error during pre-shutdown app cleanup: {e}")

    try:
        # Windows shutdown command with countdown timer
        os.system(f"shutdown /s /t {delay_seconds}")
        logger.info(f"Initiated system shutdown in {delay_seconds} seconds.")
        return {
            "status": "success",
            "delay_seconds": delay_seconds,
            "cleanup": closed_summary,
            "message": f"Closed active applications. Shutting down your computer in {delay_seconds} seconds. Goodbye!",
        }
    except Exception as exc:
        raise RuntimeError(f"Failed to initiate shutdown: {exc}")


@tool(
    name="restart_pc",
    description="Safely close all open tabs/apps and restart the Windows laptop/PC. (e.g. 'Laptop restart karo', 'Restart computer').",
    permission_level=PermissionLevel.LEVEL_1_NORMAL,
    category=ToolCategory.SYSTEM,
    args_schema=RestartArgs,
)
def restart_pc(close_all_apps: bool = True, delay_seconds: int = 5) -> Dict[str, Any]:
    """Gracefully close all applications and execute Windows restart."""
    if close_all_apps:
        try:
            clean_unused_apps(close_browsers=True)
        except Exception as e:
            logger.warning(f"Error during pre-restart app cleanup: {e}")

    try:
        os.system(f"shutdown /r /t {delay_seconds}")
        logger.info(f"Initiated system restart in {delay_seconds} seconds.")
        return {
            "status": "success",
            "delay_seconds": delay_seconds,
            "message": f"Closed active applications. Restarting your computer in {delay_seconds} seconds.",
        }
    except Exception as exc:
        raise RuntimeError(f"Failed to initiate restart: {exc}")


@tool(
    name="sleep_pc",
    description="Put the Windows laptop/PC into Sleep Mode. (e.g. 'Sleep mode mein daalo', 'Sleep computer', 'Go to sleep').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.SYSTEM,
)
def sleep_pc() -> Dict[str, Any]:
    """Put the system into sleep state."""
    try:
        # Windows API call to trigger suspend/sleep state
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        logger.info("Triggered system sleep mode.")
        return {
            "status": "success",
            "message": "Entering Sleep Mode now.",
        }
    except Exception as exc:
        raise RuntimeError(f"Failed to enter sleep mode: {exc}")


@tool(
    name="lock_pc",
    description="Lock the Windows desktop session immediately. (e.g. 'Laptop lock karo', 'Lock PC', 'Lock screen').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.SYSTEM,
)
def lock_pc() -> Dict[str, Any]:
    """Lock the Windows workstation."""
    try:
        os.system("rundll32.exe user32.dll,LockWorkStation")
        logger.info("Locked Windows workstation.")
        return {
            "status": "success",
            "message": "Locked your Windows session.",
        }
    except Exception as exc:
        raise RuntimeError(f"Failed to lock workstation: {exc}")


@tool(
    name="cancel_shutdown",
    description="Cancel or abort any scheduled/pending Windows shutdown or restart. (e.g. 'Shutdown cancel karo', 'Abort shutdown').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.SYSTEM,
)
def cancel_shutdown() -> Dict[str, Any]:
    """Abort a pending shutdown command."""
    try:
        os.system("shutdown /a")
        logger.info("Aborted pending shutdown/restart.")
        return {
            "status": "success",
            "message": "Cancelled scheduled shutdown/restart successfully.",
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Could not cancel shutdown: {exc}",
        }
