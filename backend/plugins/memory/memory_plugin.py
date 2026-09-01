"""Memory Plugin for JARVIS."""
from typing import Any, Dict, List
from backend.core.permissions import PermissionLevel, ToolCategory
from backend.plugins.base import BasePlugin, PluginActionResult
from backend.ai.context_memory import user_memory


class MemoryPlugin(BasePlugin):
    """Plugin for safe long-term structured user memory management."""

    def __init__(self):
        super().__init__(
            name="memory",
            description="Safe structured user memory management (preferences, preferred apps, contacts, clear memory).",
            category=ToolCategory.SYSTEM,
            required_permissions=[PermissionLevel.LEVEL_0_SAFE],
        )

    def get_actions(self) -> List[str]:
        return ["get_preferences", "forget_item", "clear_memory"]

    def validate(self, action: str, params: Dict[str, Any]) -> bool:
        return action in self.get_actions()

    async def execute(self, action: str, params: Dict[str, Any]) -> PluginActionResult:
        try:
            if action == "get_preferences":
                prefs = user_memory.get_stored_preferences()
                return PluginActionResult(success=True, message="Retrieved stored preferences.", data=prefs)
            elif action == "forget_item":
                k = params.get("key", "")
                msg = user_memory.forget_item(k)
                return PluginActionResult(success=True, message=msg)
            elif action == "clear_memory":
                msg = user_memory.clear_memory()
                return PluginActionResult(success=True, message=msg)
        except Exception as e:
            return PluginActionResult(success=False, message=str(e))
        return PluginActionResult(success=False, message=f"Action '{action}' not handled.")
