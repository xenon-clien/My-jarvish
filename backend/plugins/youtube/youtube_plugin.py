"""YouTube Plugin for JARVIS."""
from typing import Any, Dict, List
from backend.core.permissions import PermissionLevel, ToolCategory
from backend.plugins.base import BasePlugin, PluginActionResult
from backend.tools.browser_tools import play_youtube_video, click_screen_video


class YouTubePlugin(BasePlugin):
    """Plugin for YouTube video playback and structured navigation."""

    def __init__(self):
        super().__init__(
            name="youtube",
            description="Structured YouTube video search and ordinal playback.",
            category=ToolCategory.MEDIA,
            required_permissions=[PermissionLevel.LEVEL_0_SAFE],
        )

    def get_actions(self) -> List[str]:
        return ["play_video", "click_video"]

    def validate(self, action: str, params: Dict[str, Any]) -> bool:
        return action in self.get_actions()

    async def execute(self, action: str, params: Dict[str, Any]) -> PluginActionResult:
        try:
            if action == "play_video":
                res = play_youtube_video(query=params.get("query", ""))
                return PluginActionResult(success=True, message=res.get("message", "Played YouTube video."), data=res)
            elif action == "click_video":
                idx = int(params.get("index", 1))
                is_s = bool(params.get("is_short", False))
                res = click_screen_video(index=idx, is_short=is_s)
                return PluginActionResult(success=True, message=res.get("message", "Clicked video."), data=res)
        except Exception as e:
            return PluginActionResult(success=False, message=str(e))
        return PluginActionResult(success=False, message=f"Action '{action}' not handled.")
