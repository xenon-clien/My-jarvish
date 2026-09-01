"""JARVIS 3.0 - Centralized Tool & Feature Registry.

Single source of truth for all registered tools, their categories, permissions,
health status, schemas, and execution policies.
"""
from typing import Any, Callable, Dict, List, Optional, Type
from pydantic import BaseModel

from core.events import EventType, JarvisEvent, event_bus
from core.logger import get_logger
from core.models import PermissionLevel, PermissionType, RetryPolicy, ToolCategory, ToolExecutionResult
from core.tool_contract import BaseTool, FunctionalTool

logger = get_logger("ToolRegistry")


class ToolRegistry:
    """Central registry maintaining all active JARVIS tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a BaseTool instance."""
        name = tool.name.lower().strip()
        if name in self._tools:
            logger.info(f"Overwriting existing tool registration: '{name}'")
        self._tools[name] = tool
        logger.debug(f"Registered tool '{name}' [{tool.category.value} / Level {tool.permission_level.value}]")
        event_bus.publish(JarvisEvent(
            event_type=EventType.TOOL_REGISTERED,
            data={"tool_name": name, "category": tool.category.value},
        ))

    def unregister(self, tool_name: str) -> bool:
        """Unregister a tool by name."""
        name = tool_name.lower().strip()
        if name in self._tools:
            del self._tools[name]
            event_bus.publish(JarvisEvent(
                event_type=EventType.TOOL_DISABLED,
                data={"tool_name": name},
            ))
            return True
        return False

    def get(self, tool_name: str) -> Optional[BaseTool]:
        """Retrieve tool by canonical name."""
        return self._tools.get(tool_name.lower().strip())

    def has_tool(self, tool_name: str) -> bool:
        """Check if tool is registered."""
        return tool_name.lower().strip() in self._tools

    def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        only_enabled: bool = True,
    ) -> List[BaseTool]:
        """Return list of all registered tools with optional filters."""
        tools = list(self._tools.values())
        if only_enabled:
            tools = [t for t in tools if t.is_enabled]
        if category:
            tools = [t for t in tools if t.category == category]
        return tools

    def get_summary_by_category(self) -> Dict[str, List[str]]:
        """Return a structured summary of all registered tools grouped by category."""
        summary: Dict[str, List[str]] = {}
        for tool in self._tools.values():
            cat = tool.category.value
            if cat not in summary:
                summary[cat] = []
            summary[cat].append(tool.name)
        return summary

    def get_schemas(self, only_enabled: bool = True) -> List[Dict[str, Any]]:
        """Return full list of tool schemas."""
        tools = self.list_tools(only_enabled=only_enabled)
        return [t.get_schema() for t in tools]

    def get_openai_tool_schemas(self, only_enabled: bool = True) -> List[Dict[str, Any]]:
        """Return function calling declarations for AI providers (Gemini / OpenAI)."""
        tools = self.list_tools(only_enabled=only_enabled)
        return [t.get_openai_tool_schema() for t in tools]

    def set_tool_enabled(self, tool_name: str, enabled: bool) -> bool:
        """Enable or disable a specific tool."""
        tool = self.get(tool_name)
        if tool:
            tool.is_enabled = enabled
            logger.info(f"Tool '{tool_name}' enabled status set to: {enabled}")
            return True
        return False

    async def execute(self, tool_name: str, **kwargs) -> ToolExecutionResult:
        """Execute a tool by name with safety checks."""
        tool = self.get(tool_name)
        if not tool:
            return ToolExecutionResult(
                success=False,
                error=f"That capability is not currently installed: '{tool_name}'",
            )
        if not tool.is_enabled:
            return ToolExecutionResult(
                success=False,
                error=f"Tool '{tool_name}' is currently disabled.",
            )
        return await tool.execute(**kwargs)


# Global default ToolRegistry singleton
default_registry = ToolRegistry()


def tool(
    name: str,
    description: str,
    category: ToolCategory = ToolCategory.SYSTEM,
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_SAFE,
    required_permissions: Optional[List[PermissionType]] = None,
    parameters_schema: Optional[Type[BaseModel]] = None,
    verify_func: Optional[Callable] = None,
    fallback_func: Optional[Callable] = None,
    timeout_seconds: float = 15.0,
    retry_policy: Optional[RetryPolicy] = None,
    dependencies: Optional[List[str]] = None,
    registry: Optional[ToolRegistry] = None,
):
    """Decorator to register a Python function into the JARVIS Tool Registry."""
    target_registry = registry or default_registry

    def decorator(func: Callable):
        tool_instance = FunctionalTool(
            name=name,
            description=description,
            category=category,
            func=func,
            verify_func=verify_func,
            fallback_func=fallback_func,
            permission_level=permission_level,
            required_permissions=required_permissions,
            parameters_schema=parameters_schema,
            timeout_seconds=timeout_seconds,
            retry_policy=retry_policy,
            dependencies=dependencies,
        )
        target_registry.register(tool_instance)
        return func

    return decorator
