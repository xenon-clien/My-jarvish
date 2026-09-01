"""JARVIS 3.0 - Task Manager & Dependency Planner.

Manages task creation, dependency graphs, state transitions,
and execution scheduling without cascading failure traps.
"""
import asyncio
from datetime import datetime
import time
from typing import Any, Dict, List, Optional
import uuid

from core.events import EventType, JarvisEvent, event_bus
from core.logger import get_logger
from core.models import ToolExecutionResult, VerificationResult
from core.permissions import permission_manager
from core.recovery_engine import recovery_engine
from core.resource_manager import resource_manager
from core.task_state import TaskItem, TaskPriority, TaskState
from core.tool_registry import default_registry
from core.verification_engine import verification_engine

logger = get_logger("TaskManager")


class TaskManager:
    """Orchestrates individual tasks and multi-step dependency graphs."""

    def __init__(self):
        self._tasks: Dict[str, TaskItem] = {}

    def create_task(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        dependencies: Optional[List[str]] = None,
        required_resources: Optional[List[str]] = None,
        timeout_seconds: float = 15.0,
    ) -> TaskItem:
        """Create a new tracked task."""
        t_id = f"TASK-{uuid.uuid4().hex[:6].upper()}"
        tool_obj = default_registry.get(tool_name)

        # Automatically determine required resource locks from tool category/name
        resources = required_resources or []
        if not resources and tool_obj:
            cat = tool_obj.category.value.lower()
            if cat in ["media", "browser", "youtube"]:
                resources.extend(["browser", "youtube"])
            elif cat in ["communication", "whatsapp"]:
                resources.append("whatsapp")

        task = TaskItem(
            id=t_id,
            tool_name=tool_name,
            arguments=arguments or {},
            state=TaskState.PENDING,
            priority=priority,
            dependencies=dependencies or [],
            required_resources=resources,
            timeout_seconds=timeout_seconds,
            max_retries=tool_obj.retry_policy.max_retries if tool_obj else 2,
        )
        self._tasks[t_id] = task
        event_bus.publish(JarvisEvent(
            event_type=EventType.TASK_CREATED,
            data={"task_id": t_id, "tool_name": tool_name},
        ))
        return task

    def get_task(self, task_id: str) -> Optional[TaskItem]:
        return self._tasks.get(task_id)

    def list_tasks(self, limit: int = 50) -> List[TaskItem]:
        return list(self._tasks.values())[-limit:]

    async def execute_task(self, task_id: str) -> TaskItem:
        """Execute a single task with dependency checks, resource locks, permissions, and verification."""
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task '{task_id}' not found.")

        # 1. Dependency Resolution
        for dep_id in task.dependencies:
            dep_task = self.get_task(dep_id)
            if not dep_task or not dep_task.is_successful():
                logger.warning(f"Task '{task_id}' is BLOCKED because prerequisite '{dep_id}' did not succeed.")
                task.state = TaskState.BLOCKED
                task.error = f"Prerequisite task '{dep_id}' was not successful."
                return task

        tool = default_registry.get(task.tool_name)
        if not tool:
            task.state = TaskState.FAILED
            task.error = f"Tool '{task.tool_name}' is not registered."
            return task

        # 2. Permission Evaluation
        perm_check = permission_manager.evaluate_tool_permission(
            tool_name=tool.name,
            level=tool.permission_level,
            required_permissions=tool.required_permissions,
            arguments=task.arguments,
        )
        if not perm_check.allowed:
            task.state = TaskState.FAILED
            task.error = f"Permission denied: {perm_check.reason}"
            return task

        # 3. Resource Lock Acquisition
        acquired = await resource_manager.acquire_resources(
            resources=task.required_resources,
            task_id=task.id,
            timeout_seconds=task.timeout_seconds,
        )
        if not acquired:
            task.state = TaskState.FAILED
            task.error = f"Could not acquire required resources: {task.required_resources}"
            return task

        # 4. State: RUNNING
        task.state = TaskState.RUNNING
        task.started_at = time.time()
        event_bus.publish(JarvisEvent(
            event_type=EventType.TASK_STARTED,
            data={"task_id": task.id, "tool_name": task.tool_name},
        ))

        try:
            # Custom verification callback integrating VerificationEngine
            async def _verify_cb(res: ToolExecutionResult) -> VerificationResult:
                task.state = TaskState.VERIFYING
                return await verification_engine.verify_tool_execution(
                    tool_name=task.tool_name,
                    arguments=task.arguments,
                    tool_result=res,
                )

            # 5. Execute with Bounded Retries and Multi-Tier Recovery
            res = await recovery_engine.execute_with_recovery(
                tool=tool,
                arguments=task.arguments,
                verify_callback=_verify_cb,
            )

            task.completed_at = time.time()
            task.result = res.data
            task.message = res.message
            task.execution_strategy = res.strategy_used

            if res.success:
                task.state = TaskState.COMPLETED
                event_bus.publish(JarvisEvent(
                    event_type=EventType.TASK_COMPLETED,
                    data={"task_id": task.id, "duration_ms": task.execution_duration_ms()},
                ))
            else:
                task.state = TaskState.FAILED
                task.error = res.error
                event_bus.publish(JarvisEvent(
                    event_type=EventType.TASK_FAILED,
                    data={"task_id": task.id, "error": task.error},
                ))

        except Exception as exc:
            task.completed_at = time.time()
            task.state = TaskState.FAILED
            task.error = str(exc)
            logger.error(f"Unexpected task exception in '{task.id}': {exc}")
        finally:
            # 6. Always safely release resource locks
            resource_manager.release_all_for_task(task.id)

        return task

    async def execute_plan(self, tasks: List[TaskItem]) -> List[TaskItem]:
        """Execute an ordered sequence or DAG of tasks with partial success tracking."""
        results = []
        for task in tasks:
            executed = await self.execute_task(task.id)
            results.append(executed)
            # If a prerequisite in sequential plan fails, mark subsequent dependent tasks BLOCKED
            if not executed.is_successful() and task.dependencies:
                break
        return results


# Global TaskManager singleton
task_manager = TaskManager()
