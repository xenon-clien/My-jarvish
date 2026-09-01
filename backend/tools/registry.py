"""Tool registry and execution engine for JARVIS AI.

Every tool registered in JARVIS has a clear schema, category, permission level,
input validator, timeout boundary, and error boundary.
"""
import asyncio
import inspect
import time
from typing import Any, Callable, Dict, List, Optional, Type
from pydantic import BaseModel, ValidationError

from backend.core.logger import get_logger
from backend.core.permissions import PermissionLevel, ToolCategory

logger = get_logger("ToolRegistry")


class ToolResult(BaseModel):
    """Structured result returned by every tool execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    tool_name: str = ""


class BaseTool:
    """Represents an executable tool available to JARVIS."""

    def __init__(
        self,
        name: str,
        description: str,
        permission_level: PermissionLevel,
        func: Callable,
        category: ToolCategory = ToolCategory.SYSTEM,
        args_schema: Optional[Type[BaseModel]] = None,
        timeout: float = 25.0,
    ):
        self.name = name
        self.description = description.strip()
        self.permission_level = permission_level
        self.category = category
        self.func = func
        self.args_schema = args_schema
        self.timeout = timeout

    def get_schema(self) -> Dict[str, Any]:
        """Return the tool schema for LLM function/tool calling."""
        parameters = {}
        if self.args_schema:
            parameters = self.args_schema.model_json_schema()
        else:
            # Generate simple parameter schema from function signature if available
            sig = inspect.signature(self.func)
            props = {}
            required = []
            for param_name, param in sig.parameters.items():
                if param_name in ["self", "cls"]:
                    continue
                param_type = "string"
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"
                elif param.annotation == list:
                    param_type = "array"

                props[param_name] = {"type": param_type, "description": param_name}
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)

            if props:
                parameters = {
                    "type": "object",
                    "properties": props,
                    "required": required,
                }
            else:
                parameters = {
                    "type": "object",
                    "properties": {},
                }

        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "permission_level": self.permission_level.value,
            "parameters": parameters,
        }

    def get_openai_tool_schema(self) -> Dict[str, Any]:
        """Return OpenAI / OpenRouter function calling specification."""
        base_schema = self.get_schema()
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": base_schema.get("parameters", {"type": "object", "properties": {}}),
            },
        }

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with argument validation and timeout protection."""
        start_time = time.time()
        try:
            # Validate input arguments against Pydantic schema if provided
            if self.args_schema:
                validated_args = self.args_schema(**kwargs)
                call_args = validated_args.model_dump()
            else:
                call_args = kwargs

            # Execute async or sync function within timeout
            if inspect.iscoroutinefunction(self.func):
                raw_result = await asyncio.wait_for(self.func(**call_args), timeout=self.timeout)
            else:
                loop = asyncio.get_event_loop()
                raw_result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: self.func(**call_args)),
                    timeout=self.timeout,
                )

            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            logger.info(f"Tool '{self.name}' executed in {elapsed_ms}ms [Success]")
            return ToolResult(
                success=True,
                data=raw_result,
                execution_time_ms=elapsed_ms,
                tool_name=self.name,
            )

        except ValidationError as val_err:
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            error_msg = f"Invalid arguments for tool '{self.name}': {val_err}"
            logger.warning(error_msg)
            return ToolResult(
                success=False,
                error=error_msg,
                execution_time_ms=elapsed_ms,
                tool_name=self.name,
            )
        except asyncio.TimeoutError:
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            error_msg = f"Tool '{self.name}' timed out after {self.timeout}s"
            logger.error(error_msg)
            return ToolResult(
                success=False,
                error=error_msg,
                execution_time_ms=elapsed_ms,
                tool_name=self.name,
            )
        except Exception as exc:
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            error_msg = f"Error executing tool '{self.name}': {str(exc)}"
            logger.error(error_msg)
            return ToolResult(
                success=False,
                error=error_msg,
                execution_time_ms=elapsed_ms,
                tool_name=self.name,
            )


class ToolRegistry:
    """Central repository for all JARVIS tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        if tool.name in self._tools:
            logger.warning(f"Overwriting existing tool registration for '{tool.name}'")
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool '{tool.name}' [{tool.category.value} / Level {tool.permission_level.value}]")

    def get(self, name: str) -> Optional[BaseTool]:
        """Retrieve a tool by name."""
        return self._tools.get(name)

    def list_tools(self, category: Optional[ToolCategory] = None) -> List[BaseTool]:
        """Return a list of all registered tools, optionally filtered by category."""
        if category:
            return [t for t in self._tools.values() if t.category == category]
        return list(self._tools.values())

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Return list of JSON schemas for all registered tools."""
        return [t.get_schema() for t in self._tools.values()]

    def get_openai_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return list of OpenAI / OpenRouter function calling schemas."""
        return [t.get_openai_tool_schema() for t in self._tools.values()]

    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """Find and execute a tool by name (supports direct tools and adapter namespaces)."""
        # 1. Check direct registered tools
        tool = self.get(tool_name)
        if tool:
            return await tool.execute(**kwargs)

        # 2. Check Application Adapter namespaces
        if "." in tool_name:
            namespace, action = tool_name.split(".", 1)
            start_t = time.time()
            try:
                if namespace == "youtube":
                    from backend.adapters.youtube_adapter import youtube_adapter
                    method = getattr(youtube_adapter, action, None)
                    if method:
                        res = method(**kwargs)
                        return ToolResult(success=True, data=res, execution_time_ms=(time.time() - start_t) * 1000, tool_name=tool_name)
                elif namespace == "whatsapp":
                    from backend.adapters.whatsapp_adapter import whatsapp_adapter
                    method = getattr(whatsapp_adapter, action, None)
                    if method:
                        res = method(**kwargs)
                        return ToolResult(success=True, data=res, execution_time_ms=(time.time() - start_t) * 1000, tool_name=tool_name)
                elif namespace == "system":
                    from backend.adapters.system_adapter import system_adapter
                    method = getattr(system_adapter, action, None)
                    if method:
                        res = method(**kwargs)
                        return ToolResult(success=True, data=res, execution_time_ms=(time.time() - start_t) * 1000, tool_name=tool_name)
            except Exception as e:
                return ToolResult(success=False, error=str(e), execution_time_ms=(time.time() - start_t) * 1000, tool_name=tool_name)

        return ToolResult(
            success=False,
            error=f"Tool '{tool_name}' is not registered in the system.",
            tool_name=tool_name,
        )


# Global default registry instance
default_registry = ToolRegistry()


def tool(
    name: str,
    description: str,
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_SAFE,
    category: ToolCategory = ToolCategory.SYSTEM,
    args_schema: Optional[Type[BaseModel]] = None,
    timeout: float = 10.0,
    registry: Optional[ToolRegistry] = None,
):
    """Decorator to register a function as a JARVIS tool."""
    target_registry = registry or default_registry

    def decorator(func: Callable):
        tool_obj = BaseTool(
            name=name,
            description=description,
            permission_level=permission_level,
            category=category,
            func=func,
            args_schema=args_schema,
            timeout=timeout,
        )
        target_registry.register(tool_obj)
        return func

    return decorator
