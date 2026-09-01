"""JARVIS Plugin Manager for dynamic plugin discovery, registration, and lifecycle."""
from typing import Dict, List, Optional, Type
from backend.core.logger import get_logger
from backend.plugins.base import BasePlugin, PluginActionResult

logger = get_logger("PluginManager")


class PluginManager:
    """Manages loading, lifecycle, and invocation of JARVIS plugins."""

    def __init__(self):
        self._plugins: Dict[str, BasePlugin] = {}

    def _ensure_default_plugins(self) -> None:
        """Register built-in plugins lazily on first access if empty."""
        if not self._plugins:
            try:
                from backend.plugins.browser import BrowserPlugin
                from backend.plugins.youtube import YouTubePlugin
                from backend.plugins.messaging import MessagingPlugin
                from backend.plugins.media import MediaPlugin
                from backend.plugins.system import SystemPlugin
                from backend.plugins.memory import MemoryPlugin
                from backend.plugins.vision import VisionPlugin

                for p in [BrowserPlugin(), YouTubePlugin(), MessagingPlugin(), MediaPlugin(), SystemPlugin(), MemoryPlugin(), VisionPlugin()]:
                    self.register_plugin(p)
            except Exception as exc:
                logger.warning(f"Error loading default plugins: {exc}")

    def register_plugin(self, plugin: BasePlugin) -> None:
        """Register a plugin instance."""
        self._plugins[plugin.name.lower()] = plugin
        logger.info(f"Registered plugin '{plugin.name}' ({len(plugin.get_actions())} actions)")

    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """Get a plugin by name."""
        self._ensure_default_plugins()
        return self._plugins.get(name.lower())

    def list_plugins(self) -> List[Dict[str, str]]:
        """List metadata of registered plugins."""
        self._ensure_default_plugins()
        return [
            {
                "name": p.name,
                "description": p.description,
                "category": p.category.value,
                "enabled": p.enabled,
                "actions": p.get_actions(),
            }
            for p in self._plugins.values()
        ]

    async def execute_action(self, plugin_name: str, action: str, params: Dict[str, str]) -> PluginActionResult:
        """Execute an action on a specific plugin."""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return PluginActionResult(success=False, message=f"Plugin '{plugin_name}' not found.")
        if not plugin.enabled:
            return PluginActionResult(success=False, message=f"Plugin '{plugin_name}' is disabled.")
        if not plugin.validate(action, params):
            return PluginActionResult(success=False, message=f"Action '{action}' validation failed for plugin '{plugin_name}'.")

        return await plugin.execute(action, params)


# Singleton instance
plugin_manager = PluginManager()
