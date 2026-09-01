"""Browser Plugin for JARVIS."""
from typing import Any, Dict, List
from backend.core.permissions import PermissionLevel, ToolCategory
from backend.plugins.base import BasePlugin, PluginActionResult
from backend.tools.browser_tools import open_website, close_browser_tab, search_web


class BrowserPlugin(BasePlugin):
    """Plugin handling web browsing and navigation."""

    def __init__(self):
        super().__init__(
            name="browser",
            description="Web browser navigation, search, and tab management.",
            category=ToolCategory.BROWSER,
            required_permissions=[PermissionLevel.LEVEL_0_SAFE, PermissionLevel.LEVEL_1_NORMAL],
        )

    def get_actions(self) -> List[str]:
        return ["open_website", "close_tab", "search_web"]

    def validate(self, action: str, params: Dict[str, Any]) -> bool:
        return action in self.get_actions()

    async def execute(self, action: str, params: Dict[str, Any]) -> PluginActionResult:
        try:
            if action == "open_website":
                res = open_website(url=params.get("url", "https://google.com"))
                return PluginActionResult(success=True, message=res.get("message", "Opened website."), data=res)
            elif action == "close_tab":
                res = close_browser_tab()
                return PluginActionResult(success=True, message=res.get("message", "Closed tab."), data=res)
            elif action == "search_web":
                res = search_web(query=params.get("query", "Google"))
                return PluginActionResult(success=True, message=res.get("message", "Searched web."), data=res)
        except Exception as e:
            return PluginActionResult(success=False, message=str(e))
        return PluginActionResult(success=False, message=f"Action '{action}' not handled.")
