"""JARVIS 3.0 - Centralized Memory Subsystems.

Provides ShortTermMemory (active conversation & window state),
TaskMemory (multi-step plan execution data), and PreferenceMemory (persistent user preferences).
"""
from datetime import datetime
import json
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from core.logger import get_logger

logger = get_logger("Memory")


class ShortTermMemory:
    """Manages ephemeral in-memory state for active conversation turns."""

    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self.history: List[Dict[str, str]] = []
        self.active_application: Optional[str] = None
        self.last_tool_executed: Optional[str] = None
        self.last_correlation_id: Optional[str] = None
        self._lock = threading.Lock()

    def add_turn(self, role: str, content: str) -> None:
        with self._lock:
            self.history.append({"role": role, "content": content, "timestamp": datetime.now().isoformat()})
            if len(self.history) > self.max_turns * 2:
                self.history = self.history[-(self.max_turns * 2):]

    def get_recent_history(self, turns: int = 5) -> List[Dict[str, str]]:
        with self._lock:
            return [{"role": h["role"], "content": h["content"]} for h in self.history[-(turns * 2):]]

    def set_active_app(self, app_name: str) -> None:
        with self._lock:
            self.active_application = app_name

    def clear(self) -> None:
        with self._lock:
            self.history.clear()
            self.active_application = None
            self.last_tool_executed = None


class TaskMemory:
    """Tracks plans, tasks, intermediate values, and execution checkpoints."""

    def __init__(self):
        self.completed_tasks: List[Dict[str, Any]] = []
        self.saved_variables: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def record_completed_task(self, task_id: str, tool_name: str, result: Any) -> None:
        with self._lock:
            self.completed_tasks.append({
                "task_id": task_id,
                "tool": tool_name,
                "result": result,
                "timestamp": time.time(),
            })

    def set_variable(self, key: str, value: Any) -> None:
        with self._lock:
            self.saved_variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self.saved_variables.get(key, default)

    def clear(self) -> None:
        with self._lock:
            self.completed_tasks.clear()
            self.saved_variables.clear()


class PreferenceMemory:
    """Manages persistent user preferences (e.g. preferred browser, favorite contacts)."""

    DEFAULT_PREFERENCES = {
        "user_name": "Shivam",
        "default_browser": "chrome",
        "default_search_engine": "google",
        "default_volume": 40,
        "language": "hinglish",
        "favorite_apps": ["chrome", "youtube", "whatsapp", "vscode", "spotify"],
    }

    def __init__(self, storage_path: str = "user_preferences.json"):
        self.storage_path = Path(storage_path)
        self.preferences = dict(self.DEFAULT_PREFERENCES)
        self._lock = threading.RLock()
        self._load()

    def _load(self) -> None:
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                self.preferences.update(data)
            except Exception as e:
                logger.warning(f"Error loading preferences: {e}")

    def save(self) -> None:
        with self._lock:
            try:
                self.storage_path.write_text(json.dumps(self.preferences, indent=2), encoding="utf-8")
            except Exception as e:
                logger.warning(f"Error saving preferences: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self.preferences.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self.preferences[key] = value
            self.save()


class JarvisMemoryManager:
    """Unified memory controller for JARVIS 3.0."""

    def __init__(self):
        self.short_term = ShortTermMemory()
        self.task_memory = TaskMemory()
        self.preferences = PreferenceMemory()

    def reset(self) -> None:
        self.short_term.clear()
        self.task_memory.clear()


memory_manager = JarvisMemoryManager()
