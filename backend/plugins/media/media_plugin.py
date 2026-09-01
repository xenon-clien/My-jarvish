"""Media Plugin for JARVIS."""
from typing import Any, Dict, List
from backend.core.permissions import PermissionLevel, ToolCategory
from backend.plugins.base import BasePlugin, PluginActionResult
from backend.tools.media_tools import control_media


class MediaPlugin(BasePlugin):
    """Plugin for Windows system media playback, volume, and seeking."""

    def __init__(self):
        super().__init__(
            name="media",
            description="System media playback, seeking, speed adjustment, and volume control.",
            category=ToolCategory.MEDIA,
            required_permissions=[PermissionLevel.LEVEL_0_SAFE],
        )

    def get_actions(self) -> List[str]:
        return ["control_media"]

    def validate(self, action: str, params: Dict[str, Any]) -> bool:
        return action in self.get_actions()

    async def execute(self, action: str, params: Dict[str, Any]) -> PluginActionResult:
        try:
            act = params.get("action", "play_pause")
            lvl = params.get("level")
            t_str = params.get("time_str")
            res = control_media(action=act, level=lvl, time_str=t_str)
            return PluginActionResult(success=True, message=res.get("message", "Media action executed."), data=res)
        except Exception as e:
            return PluginActionResult(success=False, message=str(e))
