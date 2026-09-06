"""Tools module for JARVIS AI."""
from backend.tools.registry import ToolRegistry, BaseTool, ToolResult, tool, default_registry
import backend.tools.system_tools   # Register system diagnostic tools
import backend.tools.file_tools     # Register sandboxed file tools
import backend.tools.app_tools      # Register safe application control tools
import backend.tools.browser_tools  # Register YouTube, Web search & browser tools
import backend.tools.media_tools    # Register Windows hardware media controls (Play/Pause/Volume)
import backend.tools.whatsapp_tools # Register WhatsApp messaging & address book tools
import backend.tools.power_tools    # Register Windows power controls (Shutdown/Restart/Sleep/Lock)
import backend.tools.cleaner_tools  # Register junk file and cache cleaners
import backend.tools.ui_automation   # Register universal UI automation & window switching tools
import backend.tools.skill_tools     # Register universal app discovery & health testing tools
import backend.tools.youtube_tools   # Register canonical YouTube V2 tools

__all__ = [
    "ToolRegistry",
    "BaseTool",
    "ToolResult",
    "tool",
    "default_registry",
]
