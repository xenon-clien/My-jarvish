"""Unit tests for Resource Manager and Concurrency Locks."""
import asyncio
import pytest
from core.resource_manager import ResourceManager


@pytest.mark.asyncio
async def test_ordered_resource_locking():
    rm = ResourceManager()

    # Task 1 acquires browser and youtube locks
    succ1 = await rm.acquire_resources(["youtube", "browser"], task_id="TASK-001", timeout_seconds=1.0)
    assert succ1 is True

    # Inspect status
    status = rm.get_resource_status()
    assert status["browser"]["is_locked"] is True
    assert status["browser"]["locked_by"] == "TASK-001"
    assert status["youtube"]["is_locked"] is True

    # Task 2 trying to acquire youtube lock should timeout
    succ2 = await rm.acquire_resources(["youtube"], task_id="TASK-002", timeout_seconds=0.2)
    assert succ2 is False

    # Task 3 can still independently acquire WhatsApp lock (no conflict!)
    succ3 = await rm.acquire_resources(["whatsapp"], task_id="TASK-003", timeout_seconds=0.5)
    assert succ3 is True

    # Release Task 1 locks
    rm.release_all_for_task("TASK-001")
    status_after = rm.get_resource_status()
    assert status_after["browser"]["is_locked"] is False
    assert status_after["youtube"]["is_locked"] is False

    # Cleanup Task 3
    rm.release_all_for_task("TASK-003")
