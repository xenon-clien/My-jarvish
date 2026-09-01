"""Vision Plugin for JARVIS (Local Screen / Document Understanding Framework)."""
from typing import Any, Dict, List
from backend.core.permissions import PermissionLevel, ToolCategory
from backend.plugins.base import BasePlugin, PluginActionResult


class VisionPlugin(BasePlugin):
    """Plugin framework for future local OCR and document understanding capabilities."""

    def __init__(self):
        super().__init__(
            name="vision",
            description="Local OCR, screen spatial analysis, and document understanding hooks.",
            category=ToolCategory.SYSTEM,
            required_permissions=[PermissionLevel.LEVEL_0_SAFE],
        )

    def get_actions(self) -> List[str]:
        return ["local_ocr", "spatial_understand"]

    def validate(self, action: str, params: Dict[str, Any]) -> bool:
        return action in self.get_actions()

    async def execute(self, action: str, params: Dict[str, Any]) -> PluginActionResult:
        return PluginActionResult(
            success=True,
            message=f"Vision plugin action '{action}' is ready for local execution.",
            data={"status": "ready", "action": action},
        )
