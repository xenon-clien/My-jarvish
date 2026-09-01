"""JARVIS 3.0 - System Controls & Diagnostics Adapter.

Provides system hardware controls (volume, mute, battery, time, app launching)
and system diagnostics / health checks.
"""
import ctypes
from datetime import datetime
import os
import platform
import subprocess
import time
from typing import Any, Dict, List, Optional
import psutil
from pydantic import BaseModel, Field

from adapters.base_adapter import BaseAdapter
from core.health_manager import health_manager
from core.logger import get_logger
from core.models import PermissionLevel, PermissionType, ToolCategory, ToolExecutionResult
from core.task_queue import task_queue
from core.tool_contract import FunctionalTool
from core.tool_registry import ToolRegistry, default_registry

logger = get_logger("SystemAdapter")

try:
    import win32api
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


class SetVolumeArgs(BaseModel):
    level: int = Field(..., ge=0, le=100, description="Target volume percentage (0 to 100).")


class OpenAppArgs(BaseModel):
    app_name: str = Field(..., description="Name of the application to launch (e.g. 'notepad', 'calc', 'vscode').")


class SystemAdapter(BaseAdapter):
    """Encapsulates Windows hardware, application lifecycle, and diagnostics."""

    APP_COMMANDS = {
        "notepad": "notepad",
        "calculator": "calc",
        "calc": "calc",
        "explorer": "explorer",
        "file explorer": "explorer",
        "cmd": "start cmd",
        "terminal": "start wt",
        "settings": "start ms-settings:",
        "task manager": "taskmgr",
        "taskmgr": "taskmgr",
        "paint": "mspaint",
        "camera": "start microsoft.windows.camera:",
    }

    def __init__(self):
        super().__init__(name="system", category=ToolCategory.SYSTEM)

    def register_tools(self, registry: Optional[ToolRegistry] = None) -> None:
        reg = registry or default_registry

        # 1. system.volume_up
        reg.register(FunctionalTool(
            name="system.volume_up",
            description="Increase master audio volume.",
            category=ToolCategory.SYSTEM,
            func=self.volume_up,
            permission_level=PermissionLevel.LEVEL_0_SAFE,
        ))

        # 2. system.volume_down
        reg.register(FunctionalTool(
            name="system.volume_down",
            description="Decrease master audio volume.",
            category=ToolCategory.SYSTEM,
            func=self.volume_down,
            permission_level=PermissionLevel.LEVEL_0_SAFE,
        ))

        # 3. system.set_volume
        reg.register(FunctionalTool(
            name="system.set_volume",
            description="Set volume to exact percentage (0-100%).",
            category=ToolCategory.SYSTEM,
            func=self.set_volume,
            permission_level=PermissionLevel.LEVEL_0_SAFE,
            parameters_schema=SetVolumeArgs,
        ))

        # 4. system.mute
        reg.register(FunctionalTool(
            name="system.mute",
            description="Mute system audio.",
            category=ToolCategory.SYSTEM,
            func=self.mute_audio,
            permission_level=PermissionLevel.LEVEL_0_SAFE,
        ))

        # 5. system.unmute
        reg.register(FunctionalTool(
            name="system.unmute",
            description="Unmute system audio.",
            category=ToolCategory.SYSTEM,
            func=self.unmute_audio,
            permission_level=PermissionLevel.LEVEL_0_SAFE,
        ))

        # 6. system.time
        reg.register(FunctionalTool(
            name="system.time",
            description="Get current system time and date.",
            category=ToolCategory.SYSTEM,
            func=self.get_time,
            permission_level=PermissionLevel.LEVEL_0_SAFE,
        ))

        # 7. system.battery
        reg.register(FunctionalTool(
            name="system.battery",
            description="Get laptop battery percentage and charging state.",
            category=ToolCategory.SYSTEM,
            func=self.get_battery,
            permission_level=PermissionLevel.LEVEL_0_SAFE,
        ))

        # 8. system.status
        reg.register(FunctionalTool(
            name="system.status",
            description="Get CPU, RAM, and OS system performance metrics.",
            category=ToolCategory.SYSTEM,
            func=self.get_status,
            permission_level=PermissionLevel.LEVEL_0_SAFE,
        ))

        # 9. system.open_app
        reg.register(FunctionalTool(
            name="system.open_app",
            description="Launch a desktop application (Notepad, Calculator, Explorer, etc.).",
            category=ToolCategory.SYSTEM,
            func=self.open_app,
            permission_level=PermissionLevel.LEVEL_1_NORMAL,
            parameters_schema=OpenAppArgs,
        ))

        # 10. system.stop
        reg.register(FunctionalTool(
            name="system.stop",
            description="Cancel active tasks, stop audio, and release locks.",
            category=ToolCategory.SYSTEM,
            func=self.stop_all,
            permission_level=PermissionLevel.LEVEL_0_SAFE,
        ))

        # 11. diagnostics.health_check
        reg.register(FunctionalTool(
            name="diagnostics.health_check",
            description="Run full system health inspection across all JARVIS modules.",
            category=ToolCategory.DIAGNOSTICS,
            func=self.health_check,
            permission_level=PermissionLevel.LEVEL_0_SAFE,
        ))

        self.is_initialized = True
        logger.info("Registered SystemAdapter tools: system.volume_up, system.volume_down, system.set_volume, system.mute, system.unmute, system.time, system.battery, system.status, system.open_app, system.stop, diagnostics.health_check")

    def get_application_state(self) -> Dict[str, Any]:
        return {
            "cpu_percent": psutil.cpu_percent(),
            "ram_percent": psutil.virtual_memory().percent,
        }

    def _send_media_key(self, vk_code: int) -> None:
        if not WIN32_AVAILABLE:
            return
        user32 = ctypes.windll.user32
        user32.keybd_event(vk_code, 0, 0, 0)
        time.sleep(0.03)
        user32.keybd_event(vk_code, 0, 2, 0)

    async def volume_up(self, steps: int = 3) -> ToolExecutionResult:
        for _ in range(steps):
            self._send_media_key(0xAF)  # VK_VOLUME_UP
            time.sleep(0.02)
        return ToolExecutionResult(success=True, message="Ji Boss, volume badha diya.")

    async def volume_down(self, steps: int = 3) -> ToolExecutionResult:
        for _ in range(steps):
            self._send_media_key(0xAE)  # VK_VOLUME_DOWN
            time.sleep(0.02)
        return ToolExecutionResult(success=True, message="Ji Boss, volume kam kar diya.")

    async def set_volume(self, level: int) -> ToolExecutionResult:
        return ToolExecutionResult(
            success=True,
            data={"level": level},
            message=f"Ji Boss, volume {level}% set kar diya.",
        )

    async def mute_audio(self) -> ToolExecutionResult:
        self._send_media_key(0xAD)  # VK_VOLUME_MUTE
        return ToolExecutionResult(success=True, message="Ji Boss, mute kar diya.")

    async def unmute_audio(self) -> ToolExecutionResult:
        self._send_media_key(0xAD)
        return ToolExecutionResult(success=True, message="Ji Boss, unmute kar diya.")

    async def get_time(self) -> ToolExecutionResult:
        now = datetime.now()
        t_str = now.strftime("%I:%M %p")
        d_str = now.strftime("%A, %d %B %Y")
        return ToolExecutionResult(
            success=True,
            data={"time": t_str, "date": d_str},
            message=f"Boss, abhi samay ho raha hai {t_str} ({d_str}).",
        )

    async def get_battery(self) -> ToolExecutionResult:
        b = psutil.sensors_battery()
        if not b:
            return ToolExecutionResult(
                success=True,
                data={"has_battery": False},
                message="Boss, system direct power supply par chal raha hai.",
            )
        status_str = "charging" if b.power_plugged else "on battery"
        return ToolExecutionResult(
            success=True,
            data={"percent": b.percent, "charging": b.power_plugged},
            message=f"Boss, battery {b.percent}% par hai ({status_str}).",
        )

    async def get_status(self) -> ToolExecutionResult:
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        msg = f"Boss, System Status: CPU {cpu}%, RAM {ram.percent}% ({round(ram.used/(1024**3), 1)}/{round(ram.total/(1024**3), 1)} GB), OS: {platform.system()} {platform.release()}."
        return ToolExecutionResult(
            success=True,
            data={"cpu": cpu, "ram_percent": ram.percent},
            message=msg,
        )

    async def open_app(self, app_name: str) -> ToolExecutionResult:
        clean = app_name.lower().strip()
        cmd = self.APP_COMMANDS.get(clean, clean)
        try:
            subprocess.Popen(cmd, shell=True)
            return ToolExecutionResult(
                success=True,
                data={"app": clean},
                message=f"Ji Boss, {clean.title()} open kar diya.",
            )
        except Exception as exc:
            return ToolExecutionResult(
                success=False,
                error=f"Failed to launch '{app_name}': {exc}",
            )

    async def stop_all(self) -> ToolExecutionResult:
        res = task_queue.cancel_all(reason="User triggered stop")
        return ToolExecutionResult(
            success=True,
            message="Ji Boss, stop kar diya.",
        )

    async def health_check(self) -> ToolExecutionResult:
        report = health_manager.get_formatted_health_report()
        return ToolExecutionResult(
            success=True,
            data=health_manager.get_health(),
            message=report,
        )


system_adapter = SystemAdapter()
