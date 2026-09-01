"""System Plugin for JARVIS."""
from typing import Any, Dict, List
from backend.core.permissions import PermissionLevel, ToolCategory
from backend.plugins.base import BasePlugin, PluginActionResult
from backend.tools.app_tools import open_application, close_application
from backend.tools.ui_automation import manage_window, switch_window


class SystemPlugin(BasePlugin):
    """Plugin for Windows application management, process control, and window state management."""

    def __init__(self):
        super().__init__(
            name="system",
            description="Application launch, process termination, window state management.",
            category=ToolCategory.SYSTEM,
            required_permissions=[PermissionLevel.LEVEL_1_NORMAL],
        )

    def get_actions(self) -> List[str]:
        return ["open_app", "close_app", "manage_window", "switch_window"]

    def validate(self, action: str, params: Dict[str, Any]) -> bool:
        return action in self.get_actions()

    async def execute(self, action: str, params: Dict[str, Any]) -> PluginActionResult:
        try:
            if action == "open_app":
                res = open_application(app_name=params.get("app_name", ""))
                return PluginActionResult(success=True, message=res.get("message", "App launched."), data=res)
            elif action == "close_app":
                res = close_application(app_name=params.get("app_name", ""))
                return PluginActionResult(success=True, message=res.get("message", "App closed."), data=res)
            elif action == "manage_window":
                act = params.get("action", "minimize")
                app = params.get("target_app")
                res = manage_window(action=act, target_app=app)
                return PluginActionResult(success=True, message=res.get("message", "Window managed."), data=res)
            elif action == "switch_window":
                app = params.get("target_app", "")
                res = switch_window(target_app=app)
                return PluginActionResult(success=True, message=res.get("message", "Switched window."), data=res)
        except Exception as e:
            return PluginActionResult(success=False, message=str(e))
        return PluginActionResult(success=False, message=f"Action '{action}' not handled.")
