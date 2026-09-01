"""JARVIS 3.0 - Prioritized Task Queue & Cancellation System.

Manages task ordering, priority dispatching, background queue processing,
and immediate cancellation on user request ("stop", "ruk jao").
"""
import asyncio
import heapq
from typing import Any, Dict, List, Optional
import time

from core.events import EventType, JarvisEvent, event_bus
from core.logger import get_logger
from core.resource_manager import resource_manager
from core.task_manager import task_manager
from core.task_state import TaskItem, TaskPriority, TaskState

logger = get_logger("TaskQueue")


class PrioritizedQueueItem:
    """Wrapper to allow heapq ordering by priority descending, timestamp ascending."""

    def __init__(self, task: TaskItem):
        self.task = task

    def __lt__(self, other: "PrioritizedQueueItem") -> bool:
        # Higher numerical priority comes first (-priority is smaller)
        if self.task.priority != other.task.priority:
            return self.task.priority > other.task.priority
        return self.task.created_at < other.task.created_at


class TaskQueue:
    """Async Priority Queue for JARVIS tasks with cancellation support."""

    def __init__(self):
        self._queue: List[PrioritizedQueueItem] = []
        self._current_task: Optional[TaskItem] = None
        self._current_asyncio_task: Optional[asyncio.Task] = None
        self._is_running = False
        self._lock = asyncio.Lock()

    def enqueue(self, task: TaskItem) -> None:
        """Add a task to the priority queue."""
        heapq.heappush(self._queue, PrioritizedQueueItem(task))
        logger.info(f"Enqueued task '{task.id}' [{task.tool_name}] with priority {task.priority.name}")

    def cancel_all(self, reason: str = "User cancelled command") -> Dict[str, Any]:
        """Cancel the currently executing task and purge all pending tasks."""
        cancelled_count = 0

        # 1. Cancel currently executing asyncio task
        if self._current_asyncio_task and not self._current_asyncio_task.done():
            self._current_asyncio_task.cancel()
            logger.info(f"Cancelled active task '{self._current_task.id if self._current_task else 'unknown'}'")

        if self._current_task and not self._current_task.is_finished():
            self._current_task.state = TaskState.CANCELLED
            self._current_task.error = reason
            resource_manager.release_all_for_task(self._current_task.id)
            cancelled_count += 1

        # 2. Purge pending items in queue
        while self._queue:
            item = heapq.heappop(self._queue)
            item.task.state = TaskState.CANCELLED
            item.task.error = reason
            cancelled_count += 1

        # 3. Release any lingering resource locks
        resource_manager.release_all_for_task("*")

        event_bus.publish(JarvisEvent(
            event_type=EventType.TASK_CANCELLED,
            data={"reason": reason, "cancelled_count": cancelled_count},
        ))

        return {
            "status": "cancelled",
            "cancelled_count": cancelled_count,
            "message": "Ji Boss, saare tasks stop aur cancel kar diye.",
        }

    async def process_next(self) -> Optional[TaskItem]:
        """Process the highest priority task currently in the queue."""
        if not self._queue:
            return None

        async with self._lock:
            if not self._queue:
                return None
            item = heapq.heappop(self._queue)
            self._current_task = item.task

        # Run task execution wrapped in a cancellable asyncio task
        self._current_asyncio_task = asyncio.create_task(
            task_manager.execute_task(self._current_task.id)
        )
        try:
            executed_task = await self._current_asyncio_task
            return executed_task
        except asyncio.CancelledError:
            logger.info(f"Task '{self._current_task.id}' was cleanly cancelled.")
            self._current_task.state = TaskState.CANCELLED
            return self._current_task
        finally:
            self._current_task = None
            self._current_asyncio_task = None


# Global TaskQueue singleton
task_queue = TaskQueue()
