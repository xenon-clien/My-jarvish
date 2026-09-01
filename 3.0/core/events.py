"""JARVIS 3.0 - Event Bus Architecture.

Provides an asynchronous pub/sub event bus so modules can communicate
without tight coupling or circular dependencies.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
from typing import Any, Callable, Dict, List, Optional
from core.logger import get_logger

logger = get_logger("EventBus")


class EventType(str, Enum):
    # Task Lifecycle Events
    TASK_CREATED = "TASK_CREATED"
    TASK_PLANNING = "TASK_PLANNING"
    TASK_STARTED = "TASK_STARTED"
    TASK_EXECUTING = "TASK_EXECUTING"
    TASK_VERIFYING = "TASK_VERIFYING"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    TASK_RETRYING = "TASK_RETRYING"
    TASK_RECOVERING = "TASK_RECOVERING"
    TASK_CANCELLED = "TASK_CANCELLED"

    # Application & Tool Events
    TOOL_REGISTERED = "TOOL_REGISTERED"
    TOOL_DISABLED = "TOOL_DISABLED"
    APP_OPENED = "APP_OPENED"
    APP_CLOSED = "APP_CLOSED"

    # AI & Brain Events
    AI_REQUEST_STARTED = "AI_REQUEST_STARTED"
    AI_REQUEST_COMPLETED = "AI_REQUEST_COMPLETED"
    AI_REQUEST_FAILED = "AI_REQUEST_FAILED"

    # Voice & Interaction Events
    VOICE_COMMAND_RECEIVED = "VOICE_COMMAND_RECEIVED"
    TTS_SPEAK_STARTED = "TTS_SPEAK_STARTED"
    TTS_SPEAK_COMPLETED = "TTS_SPEAK_COMPLETED"

    # Health & System Events
    FEATURE_HEALTH_CHANGED = "FEATURE_HEALTH_CHANGED"
    EMERGENCY_STOP_TRIGGERED = "EMERGENCY_STOP_TRIGGERED"


@dataclass
class JarvisEvent:
    event_type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class EventBus:
    """Thread-safe, async-compatible Event Bus."""

    def __init__(self):
        self._listeners: Dict[EventType, List[Callable[[JarvisEvent], Any]]] = {}
        self._lock = threading.RLock()

    def subscribe(self, event_type: EventType, callback: Callable[[JarvisEvent], Any]) -> None:
        """Register a subscriber for a specific event type."""
        with self._lock:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            if callback not in self._listeners[event_type]:
                self._listeners[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable[[JarvisEvent], Any]) -> None:
        """Remove a subscriber."""
        with self._lock:
            if event_type in self._listeners and callback in self._listeners[event_type]:
                self._listeners[event_type].remove(callback)

    def publish(self, event: JarvisEvent) -> None:
        """Publish an event synchronously or schedule on event loop."""
        with self._lock:
            callbacks = list(self._listeners.get(event.event_type, []))

        for cb in callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(cb(event))
                    except RuntimeError:
                        # No running event loop in this thread
                        asyncio.run(cb(event))
                else:
                    cb(event)
            except Exception as exc:
                logger.error(f"Error in event handler for {event.event_type}: {exc}")


# Global EventBus singleton
event_bus = EventBus()
