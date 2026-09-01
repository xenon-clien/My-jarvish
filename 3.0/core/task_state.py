"""JARVIS 3.0 - Task State Machine & Task Models.

Enforces strict lifecycle state transitions for tasks in JARVIS.
Never uses boolean `isRunning = True` for multi-command flows.
"""
from datetime import datetime
from enum import Enum, IntEnum
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TaskState(str, Enum):
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    RECOVERING = "RECOVERING"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"


class TaskPriority(IntEnum):
    EMERGENCY = 100   # Stop, cancel, safety interrupts
    HIGH = 50         # User active voice/direct command
    NORMAL = 10       # Standard automation steps
    LOW = 1           # Background health check, telemetry cleanup


class TaskItem(BaseModel):
    """Represents a single atomic or composite planned task."""
    id: str
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    state: TaskState = TaskState.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    dependencies: List[str] = Field(default_factory=list)  # IDs of tasks that must succeed first
    required_resources: List[str] = Field(default_factory=list) # e.g. ["youtube", "browser"]
    timeout_seconds: float = 15.0
    retry_count: int = 0
    max_retries: int = 2
    execution_strategy: str = "primary"
    result: Optional[Any] = None
    message: Optional[str] = None
    verification_message: Optional[str] = None
    error: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    cancellable: bool = True

    def is_finished(self) -> bool:
        """Return True if task has reached a terminal state."""
        return self.state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED]

    def is_successful(self) -> bool:
        """Return True if task completed and verified successfully."""
        return self.state == TaskState.COMPLETED

    def execution_duration_ms(self) -> float:
        """Calculate execution duration in milliseconds."""
        if not self.started_at:
            return 0.0
        end_t = self.completed_at or time.time()
        return round((end_t - self.started_at) * 1000, 2)
