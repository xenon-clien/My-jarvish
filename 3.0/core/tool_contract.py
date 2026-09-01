"""JARVIS 3.0 - Standard Tool Contract.

Defines the contract that every tool in JARVIS must implement.
No arbitrary functions are ever called directly by LLMs or Routers without
going through this standardized interface.
"""
from abc import ABC, abstractmethod
import asyncio
import inspect
import time
from typing import Any, Callable, Dict, List, Optional, Type
from pydantic import BaseModel, ValidationError

from core.logger import get_logger
from core.models import (
    PermissionLevel,
    PermissionType,
    RetryPolicy,
    ToolCategory,
    ToolExecutionResult,
    VerificationResult,
)

logger = get_logger("ToolContract")


class BaseTool(ABC):
    """Abstract Base Class for all JARVIS Tools."""

    def __init__(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        permission_level: PermissionLevel = PermissionLevel.LEVEL_0_SAFE,
        required_permissions: Optional[List[PermissionType]] = None,
        parameters_schema: Optional[Type[BaseModel]] = None,
        timeout_seconds: float = 15.0,
        retry_policy: Optional[RetryPolicy] = None,
        dependencies: Optional[List[str]] = None,
    ):
        self.name = name.strip()
        self.description = description.strip()
        self.category = category
        self.permission_level = permission_level
        self.required_permissions = required_permissions or [PermissionType.EXECUTE]
        self.parameters_schema = parameters_schema
        self.timeout_seconds = timeout_seconds
        self.retry_policy = retry_policy or RetryPolicy()
        self.dependencies = dependencies or []
        self.is_enabled = True

    @abstractmethod
    async def execute(self, **kwargs) -> ToolExecutionResult:
        """Primary deterministic execution logic."""
        pass

    async def verify(
        self,
        pre_state: Optional[Dict[str, Any]],
        post_state: Optional[Dict[str, Any]],
        tool_result: ToolExecutionResult,
        **kwargs,
    ) -> VerificationResult:
        """Closed-loop verification logic. Subclasses should override with specific checks."""
        # Default verification checks if result was explicitly successful
        if tool_result.success:
            return VerificationResult(
                is_verified=True,
                verification_type="basic_success",
                message=f"Tool '{self.name}' returned success: {tool_result.message}",
            )
        return VerificationResult(
            is_verified=False,
            verification_type="basic_failure",
            message=f"Tool '{self.name}' returned error: {tool_result.error}",
            needs_recovery=True,
        )

    async def fallback(self, attempt_number: int, **kwargs) -> ToolExecutionResult:
        """Secondary / tertiary fallback execution logic when primary method fails."""
        return ToolExecutionResult(
            success=False,
            error=f"No fallback implementation available for tool '{self.name}' (attempt {attempt_number}).",
            strategy_used="none",
        )

    def get_schema(self) -> Dict[str, Any]:
        """Return standardized JSON schema for LLM function calling."""
        parameters = {"type": "object", "properties": {}}
        if self.parameters_schema:
            try:
                parameters = self.parameters_schema.model_json_schema()
            except Exception as e:
                logger.warning(f"Error generating JSON schema for '{self.name}': {e}")

        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "permission_level": self.permission_level.value,
            "required_permissions": [p.value for p in self.required_permissions],
            "parameters": parameters,
            "dependencies": self.dependencies,
            "timeout_seconds": self.timeout_seconds,
        }

    def get_openai_tool_schema(self) -> Dict[str, Any]:
        """Return OpenAI / Gemini-compatible tool declaration."""
        schema = self.get_schema()
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema.get("parameters", {"type": "object", "properties": {}}),
            },
        }

    def validate_args(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate input arguments against Pydantic schema."""
        if self.parameters_schema:
            validated = self.parameters_schema(**kwargs)
            return validated.model_dump()
        return kwargs


class FunctionalTool(BaseTool):
    """Wrapper that converts standalone functions / methods into full BaseTool instances."""

    def __init__(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        func: Callable,
        verify_func: Optional[Callable] = None,
        fallback_func: Optional[Callable] = None,
        permission_level: PermissionLevel = PermissionLevel.LEVEL_0_SAFE,
        required_permissions: Optional[List[PermissionType]] = None,
        parameters_schema: Optional[Type[BaseModel]] = None,
        timeout_seconds: float = 15.0,
        retry_policy: Optional[RetryPolicy] = None,
        dependencies: Optional[List[str]] = None,
    ):
        super().__init__(
            name=name,
            description=description,
            category=category,
            permission_level=permission_level,
            required_permissions=required_permissions,
            parameters_schema=parameters_schema,
            timeout_seconds=timeout_seconds,
            retry_policy=retry_policy,
            dependencies=dependencies,
        )
        self._func = func
        self._verify_func = verify_func
        self._fallback_func = fallback_func

    async def execute(self, **kwargs) -> ToolExecutionResult:
        start_time = time.time()
        try:
            call_args = self.validate_args(kwargs)
            if inspect.iscoroutinefunction(self._func):
                res = await asyncio.wait_for(self._func(**call_args), timeout=self.timeout_seconds)
            else:
                loop = asyncio.get_event_loop()
                res = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: self._func(**call_args)),
                    timeout=self.timeout_seconds,
                )

            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            if isinstance(res, ToolExecutionResult):
                res.execution_time_ms = elapsed_ms
                return res
            elif isinstance(res, dict):
                if "success" in res:
                    is_succ = bool(res["success"])
                elif "status" in res:
                    is_succ = (res["status"] == "success")
                else:
                    is_succ = True
                msg = res.get("message", "Executed successfully." if is_succ else "Execution failed.")
                return ToolExecutionResult(
                    success=is_succ,
                    data=res,
                    message=msg,
                    error=res.get("error") if not is_succ else None,
                    execution_time_ms=elapsed_ms,
                    strategy_used="primary",
                )
            else:
                return ToolExecutionResult(
                    success=True,
                    data=res,
                    message=str(res) if res is not None else "Executed successfully.",
                    execution_time_ms=elapsed_ms,
                    strategy_used="primary",
                )
        except ValidationError as val_err:
            return ToolExecutionResult(
                success=False,
                error=f"Invalid arguments for tool '{self.name}': {val_err}",
                execution_time_ms=round((time.time() - start_time) * 1000, 2),
            )
        except asyncio.TimeoutError:
            return ToolExecutionResult(
                success=False,
                error=f"Tool '{self.name}' timed out after {self.timeout_seconds}s",
                execution_time_ms=round((time.time() - start_time) * 1000, 2),
            )
        except Exception as exc:
            return ToolExecutionResult(
                success=False,
                error=f"Error executing tool '{self.name}': {str(exc)}",
                execution_time_ms=round((time.time() - start_time) * 1000, 2),
            )

    async def verify(
        self,
        pre_state: Optional[Dict[str, Any]],
        post_state: Optional[Dict[str, Any]],
        tool_result: ToolExecutionResult,
        **kwargs,
    ) -> VerificationResult:
        if self._verify_func:
            try:
                if inspect.iscoroutinefunction(self._verify_func):
                    return await self._verify_func(pre_state=pre_state, post_state=post_state, tool_result=tool_result, **kwargs)
                else:
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(
                        None,
                        lambda: self._verify_func(pre_state=pre_state, post_state=post_state, tool_result=tool_result, **kwargs),
                    )
            except Exception as e:
                logger.warning(f"Verification error in tool '{self.name}': {e}")
                return VerificationResult(
                    is_verified=False,
                    verification_type="verification_exception",
                    message=f"Verification function failed: {e}",
                    needs_recovery=True,
                )
        return await super().verify(pre_state, post_state, tool_result, **kwargs)

    async def fallback(self, attempt_number: int, **kwargs) -> ToolExecutionResult:
        if self._fallback_func:
            try:
                if inspect.iscoroutinefunction(self._fallback_func):
                    return await self._fallback_func(attempt_number=attempt_number, **kwargs)
                else:
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(
                        None, lambda: self._fallback_func(attempt_number=attempt_number, **kwargs)
                    )
            except Exception as exc:
                return ToolExecutionResult(
                    success=False,
                    error=f"Fallback execution error for '{self.name}': {exc}",
                    strategy_used=f"fallback_{attempt_number}",
                )
        return await super().fallback(attempt_number, **kwargs)
