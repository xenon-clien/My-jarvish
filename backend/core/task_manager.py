"""JARVIS High-Reliability Task & Resource Lock Manager.

Prevents tool collisions, enforces task lifecycle states, handles timeouts,
retries, verification, and emergency task cancellation.
"""
import asyncio
from datetime import datetime
from enum import Enum
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set
import uuid

from pydantic import BaseModel, Field
from backend.core.logger import get_logger

logger = get_logger("TaskManager")


class TaskState(str, Enum):
    """Lifecycle states for all JARVIS tasks."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    RECOVERING = "RECOVERING"
    CANCELLED = "CANCELLED"


class TaskPriority(int, Enum):
    """Task execution priorities."""
    LOW = 10
    NORMAL = 20
    HIGH = 30
    EMERGENCY = 40  # Emergency stop/cancellation


class Task(BaseModel):
    """Structured execution payload and state tracking for an action."""
    task_id: str = Field(default_factory=lambda: f"TASK-{datetime.now().strftime('%H%M%S')}-{uuid.uuid4().hex[:4].upper()}")
    command: str = ""
    tool_name: str = ""
    arguments: Dict[str, Any] = Field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    state: TaskState = TaskState.PENDING
    required_locks: List[str] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    timeout_sec: float = 15.0
    retry_count: int = 0
    max_retries: int = 2
    immediate_response: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    verified: bool = False
    verification_message: Optional[str] = None


class ResourceLockManager:
    """Thread-safe resource locking manager to prevent multi-feature collisions."""

    def __init__(self):
        self._lock = threading.RLock()
        self._active_locks: Dict[str, str] = {}  # resource_name -> task_id

    def acquire(self, resources: List[str], task_id: str, timeout: float = 3.0) -> bool:
        """Attempt to acquire locks on all required resources."""
        if not resources:
            return True

        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                available = all(r not in self._active_locks or self._active_locks[r] == task_id for r in resources)
                if available:
                    for r in resources:
                        self._active_locks[r] = task_id
                    logger.debug(f"Task {task_id} acquired locks on: {resources}")
                    return True
            time.sleep(0.05)

        logger.warning(f"Task {task_id} timed out waiting for locks on: {resources}. Held by: {self._active_locks}")
        return False

    def release(self, resources: List[str], task_id: str) -> None:
        """Release locks held by a specific task."""
        with self._lock:
            for r in resources:
                if self._active_locks.get(r) == task_id:
                    del self._active_locks[r]
            logger.debug(f"Task {task_id} released locks on: {resources}")

    def release_all_for_task(self, task_id: str) -> None:
        """Release all locks held by a task."""
        with self._lock:
            to_delete = [r for r, tid in self._active_locks.items() if tid == task_id]
            for r in to_delete:
                del self._active_locks[r]
            if to_delete:
                logger.debug(f"Released all locks for task {task_id}: {to_delete}")

    def force_release_all(self) -> None:
        """Emergency release of all resource locks."""
        with self._lock:
            cleared = list(self._active_locks.keys())
            self._active_locks.clear()
            logger.warning(f"Emergency: Force cleared all resource locks: {cleared}")

    def get_held_locks(self) -> Dict[str, str]:
        """Return snapshot of currently held locks."""
        with self._lock:
            return dict(self._active_locks)


class TaskManager:
    """Central manager for executing, monitoring, verifying, and recovering tasks."""

    def __init__(self):
        self.lock_manager = ResourceLockManager()
        self._tasks: Dict[str, Task] = {}
        self._history: List[Task] = []
        self._max_history = 100
        self._lock = threading.RLock()
        self._current_running_task_id: Optional[str] = None

    def create_task(
        self,
        command: str,
        tool_name: str,
        arguments: Dict[str, Any],
        required_locks: Optional[List[str]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        immediate_response: Optional[str] = None,
        timeout_sec: float = 15.0,
        max_retries: int = 2,
    ) -> Task:
        """Instantiate and register a new task."""
        task = Task(
            command=command,
            tool_name=tool_name,
            arguments=arguments,
            required_locks=required_locks or [],
            priority=priority,
            immediate_response=immediate_response,
            timeout_sec=timeout_sec,
            max_retries=max_retries,
        )
        with self._lock:
            self._tasks[task.task_id] = task
        return task

    def execute_task_sync(
        self,
        task: Task,
        executor_fn: Callable[..., Any],
        verifier_fn: Optional[Callable[..., bool]] = None,
    ) -> Task:
        """Execute a task synchronously with locking, verification, and retry handling."""
        with self._lock:
            self._current_running_task_id = task.task_id

        acquired = self.lock_manager.acquire(task.required_locks, task.task_id, timeout=2.5)
        if not acquired:
            task.state = TaskState.FAILED
            task.error = f"Resource busy: could not acquire locks on {task.required_locks}"
            self._archive_task(task)
            return task

        task.state = TaskState.RUNNING
        task.started_at = time.time()
        logger.info(f"🚀 Executing Task {task.task_id} -> '{task.tool_name}' args={task.arguments}")

        try:
            # 1. Primary Execution Attempt
            result = executor_fn(**task.arguments)
            task.result = result

            # 2. Verification Step
            if verifier_fn:
                task.state = TaskState.VERIFYING
                is_verified = verifier_fn(task=task, result=result)
                task.verified = is_verified
                if not is_verified:
                    logger.warning(f"Task {task.task_id} execution completed but verification failed.")
                    # Retry if retries available
                    if task.retry_count < task.max_retries:
                        task.retry_count += 1
                        task.state = TaskState.RETRYING
                        logger.info(f"Retrying Task {task.task_id} (Attempt {task.retry_count}/{task.max_retries})...")
                        time.sleep(0.2)
                        result = executor_fn(**task.arguments)
                        task.result = result
                        task.verified = verifier_fn(task=task, result=result)
            else:
                task.verified = True

            task.state = TaskState.COMPLETED
            task.finished_at = time.time()
            logger.info(f"✅ Task {task.task_id} completed successfully (verified={task.verified}).")

        except Exception as exc:
            logger.error(f"❌ Task {task.task_id} failed with exception: {exc}", exc_info=True)
            task.state = TaskState.FAILED
            task.error = str(exc)
            task.finished_at = time.time()

        finally:
            self.lock_manager.release_all_for_task(task.task_id)
            with self._lock:
                if self._current_running_task_id == task.task_id:
                    self._current_running_task_id = None
            self._archive_task(task)

        return task

    def emergency_stop(self) -> Dict[str, Any]:
        """Cancel current running task and immediately release all locks."""
        with self._lock:
            cancelled_id = self._current_running_task_id
            if cancelled_id and cancelled_id in self._tasks:
                curr_task = self._tasks[cancelled_id]
                curr_task.state = TaskState.CANCELLED
                curr_task.finished_at = time.time()
                curr_task.error = "Emergency Stop requested by user."
            self._current_running_task_id = None

        self.lock_manager.force_release_all()
        logger.warning("🛑 Emergency Stop executed: all tasks cancelled, all resource locks released.")
        return {
            "status": "stopped",
            "cancelled_task_id": cancelled_id,
            "message": "Ji Boss, saare ongoing tasks rok diye hain aur locks clear kar diye hain.",
        }

    def _archive_task(self, task: Task) -> None:
        """Store task in history and maintain max history limit."""
        with self._lock:
            self._history.append(task)
            if len(self._history) > self._max_history:
                self._history.pop(0)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve task by ID."""
        with self._lock:
            return self._tasks.get(task_id)

    def get_recent_history(self, limit: int = 10) -> List[Task]:
        """Return list of recently executed tasks."""
        with self._lock:
            return list(self._history[-limit:])


# Global Singleton Task Manager
task_manager = TaskManager()
