"""System & Browser Application Adapter for JARVIS.

Non-destructively wraps OS power controls, media volume, window manager,
and browser scrolling with resource locking and verification.
"""
from typing import Any, Dict, Optional
from backend.core.logger import get_logger
from backend.core.task_manager import task_manager

logger = get_logger("SystemAdapter")


class SystemAdapter:
    """Standardized, verifiable adapter for Windows system & browser actions."""

    RESOURCE_LOCK = "system"

    def volume_up(self, step: int = 5) -> Dict[str, Any]:
        """Increase system volume."""
        from backend.tools.media_tools import control_media
        task = task_manager.create_task(
            command="volume badhao",
            tool_name="system.volume_up",
            arguments={"action": "volume_up", "level": step},
            required_locks=[self.RESOURCE_LOCK],
            immediate_response="Ji Boss, volume badha diya.",
        )
        return task_manager.execute_task_sync(task=task, executor_fn=control_media).result or {"status": "success"}

    def volume_down(self, step: int = 5) -> Dict[str, Any]:
        """Decrease system volume."""
        from backend.tools.media_tools import control_media
        task = task_manager.create_task(
            command="volume kam karo",
            tool_name="system.volume_down",
            arguments={"action": "volume_down", "level": step},
            required_locks=[self.RESOURCE_LOCK],
            immediate_response="Ji Boss, volume kam kar diya.",
        )
        return task_manager.execute_task_sync(task=task, executor_fn=control_media).result or {"status": "success"}

    def mute_toggle(self) -> Dict[str, Any]:
        """Toggle system volume mute."""
        from backend.tools.media_tools import control_media
        task = task_manager.create_task(
            command="volume mute/unmute",
            tool_name="system.mute",
            arguments={"action": "mute"},
            required_locks=[self.RESOURCE_LOCK],
            immediate_response="Ji Boss, audio mute/unmute toggle kar diya.",
        )
        return task_manager.execute_task_sync(task=task, executor_fn=control_media).result or {"status": "success"}

    def scroll_page(self, direction: str = "down", amount: int = 400) -> Dict[str, Any]:
        """Scroll active browser page smoothly."""
        from backend.tools.browser_tools import scroll_page
        task = task_manager.create_task(
            command=f"page scroll {direction}",
            tool_name="browser.scroll",
            arguments={"direction": direction, "amount": amount},
            required_locks=["browser"],
            immediate_response=f"Ji Boss, {direction} scroll kar diya.",
        )
        return task_manager.execute_task_sync(task=task, executor_fn=scroll_page).result or {"status": "success"}

    def clean_junk(self) -> Dict[str, Any]:
        """Clean temporary files, memory, and idle tabs."""
        from backend.tools.cleaner_tools import clean_system_junk
        task = task_manager.create_task(
            command="junk files clean karo",
            tool_name="system.clean_junk",
            arguments={},
            required_locks=[self.RESOURCE_LOCK],
            immediate_response="Ji Boss, system junk clean kar diya.",
        )
        return task_manager.execute_task_sync(task=task, executor_fn=clean_system_junk).result or {"status": "success"}

    def lock_pc(self) -> Dict[str, Any]:
        """Lock Windows workstation."""
        from backend.tools.power_tools import control_system_power
        task = task_manager.create_task(
            command="laptop lock karo",
            tool_name="system.lock",
            arguments={"action": "lock"},
            required_locks=[self.RESOURCE_LOCK],
            immediate_response="Ji Boss, system lock kar diya.",
        )
        return task_manager.execute_task_sync(task=task, executor_fn=control_system_power).result or {"status": "success"}

    def emergency_stop(self) -> Dict[str, Any]:
        """Emergency stop all ongoing tasks and release locks."""
        return task_manager.emergency_stop()


# Global Singleton System Adapter
system_adapter = SystemAdapter()
