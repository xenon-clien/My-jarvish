"""JARVIS 3.0 - Resource Manager & Concurrency Locks.

Prevents multi-command conflicts over applications and hardware devices
(e.g., YouTube playback and WhatsApp calls simultaneously stealing active window focus).
"""
import asyncio
from datetime import datetime
import threading
import time
from typing import Dict, List, Optional, Set
from core.logger import get_logger

logger = get_logger("ResourceManager")


class ResourceLock:
    """Represents a lock on an individual hardware/application resource."""

    def __init__(self, name: str):
        self.name = name
        self.locked_by: Optional[str] = None  # task_id
        self.locked_at: Optional[float] = None
        self._async_lock = asyncio.Lock()

    def is_locked(self) -> bool:
        return self.locked_by is not None


class ResourceManager:
    """Coordinates acquisition and safe release of application & hardware resource locks."""

    DEFAULT_RESOURCES = [
        "browser",
        "youtube",
        "whatsapp",
        "spotify",
        "microphone",
        "speaker",
        "camera",
        "clipboard",
        "filesystem",
        "system_controls",
    ]

    def __init__(self):
        self._locks: Dict[str, ResourceLock] = {
            r: ResourceLock(r) for r in self.DEFAULT_RESOURCES
        }
        self._thread_lock = threading.RLock()

    def _get_or_create_lock(self, resource_name: str) -> ResourceLock:
        res = resource_name.lower().strip()
        with self._thread_lock:
            if res not in self._locks:
                self._locks[res] = ResourceLock(res)
            return self._locks[res]

    async def acquire_resources(
        self,
        resources: List[str],
        task_id: str,
        timeout_seconds: float = 10.0,
    ) -> bool:
        """Acquire locks for all requested resources without deadlocks (ordered acquisition)."""
        if not resources:
            return True

        # Sort resource names to guarantee strict global lock ordering and prevent AB-BA deadlocks
        ordered = sorted(list(set([r.lower().strip() for r in resources])))
        acquired: List[str] = []
        start_time = time.time()

        try:
            for r_name in ordered:
                remaining_time = max(0.1, timeout_seconds - (time.time() - start_time))
                lock = self._get_or_create_lock(r_name)

                # Wait for lock with timeout
                await asyncio.wait_for(lock._async_lock.acquire(), timeout=remaining_time)
                with self._thread_lock:
                    lock.locked_by = task_id
                    lock.locked_at = time.time()
                    acquired.append(r_name)
                    logger.debug(f"Task '{task_id}' acquired resource '{r_name}'")

            return True

        except (asyncio.TimeoutError, Exception) as exc:
            logger.warning(f"Task '{task_id}' failed to acquire all resources {resources}: {exc}")
            # Rollback any locks acquired so far
            for r_name in acquired:
                self._release_single(r_name, task_id)
            return False

    def _release_single(self, resource_name: str, task_id: str) -> None:
        res = resource_name.lower().strip()
        with self._thread_lock:
            if res in self._locks:
                lock = self._locks[res]
                if lock.locked_by == task_id or task_id == "*":
                    lock.locked_by = None
                    lock.locked_at = None
                    if lock._async_lock.locked():
                        try:
                            lock._async_lock.release()
                            logger.debug(f"Released lock on '{res}' by task '{task_id}'")
                        except RuntimeError:
                            pass

    def release_resources(self, resources: List[str], task_id: str) -> None:
        """Release specific resources held by task."""
        for r_name in resources:
            self._release_single(r_name, task_id)

    def release_all_for_task(self, task_id: str) -> None:
        """Safely release ALL resources held by a specific task (e.g. on completion or crash)."""
        with self._thread_lock:
            for r_name, lock in list(self._locks.items()):
                if lock.locked_by == task_id:
                    self._release_single(r_name, task_id)

    def get_resource_status(self) -> Dict[str, Dict[str, Any]]:
        """Inspect current state of all resource locks."""
        with self._thread_lock:
            status = {}
            for name, lock in self._locks.items():
                status[name] = {
                    "is_locked": lock.is_locked(),
                    "locked_by": lock.locked_by,
                    "locked_duration_sec": round(time.time() - lock.locked_at, 2) if lock.locked_at else 0.0,
                }
            return status


# Global ResourceManager singleton
resource_manager = ResourceManager()
