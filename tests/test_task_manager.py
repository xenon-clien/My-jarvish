"""Tests for TaskManager and ResourceLockManager."""
import pytest
import time
from backend.core.task_manager import TaskManager, ResourceLockManager, TaskState, TaskPriority


def test_resource_lock_acquisition_and_release():
    lm = ResourceLockManager()
    
    # Acquire lock for task 1
    assert lm.acquire(["youtube", "browser"], "TASK-1") is True
    held = lm.get_held_locks()
    assert held["youtube"] == "TASK-1"
    assert held["browser"] == "TASK-1"
    
    # Task 2 cannot acquire already locked resource
    assert lm.acquire(["youtube"], "TASK-2", timeout=0.1) is False
    
    # Release task 1 locks
    lm.release(["youtube"], "TASK-1")
    assert "youtube" not in lm.get_held_locks()
    
    # Task 2 can now acquire
    assert lm.acquire(["youtube"], "TASK-2", timeout=0.1) is True
    
    # Clean release all
    lm.release_all_for_task("TASK-2")
    assert len(lm.get_held_locks()) == 1  # browser still held by TASK-1
    lm.force_release_all()
    assert len(lm.get_held_locks()) == 0


def test_task_lifecycle_execution_success():
    tm = TaskManager()
    
    def dummy_executor(val: int):
        return {"output": val * 2}
    
    def dummy_verifier(task, result):
        return result.get("output") == 20
    
    task = tm.create_task(
        command="double 10",
        tool_name="math.double",
        arguments={"val": 10},
        required_locks=["calc"],
    )
    
    assert task.state == TaskState.PENDING
    
    completed_task = tm.execute_task_sync(
        task=task,
        executor_fn=dummy_executor,
        verifier_fn=dummy_verifier,
    )
    
    assert completed_task.state == TaskState.COMPLETED
    assert completed_task.verified is True
    assert completed_task.result == {"output": 20}
    assert completed_task.error is None
    # Locks must be released automatically
    assert len(tm.lock_manager.get_held_locks()) == 0


def test_task_emergency_stop():
    tm = TaskManager()
    
    # Acquire locks
    tm.lock_manager.acquire(["youtube", "browser", "whatsapp"], "TASK-EMG")
    assert len(tm.lock_manager.get_held_locks()) == 3
    
    resp = tm.emergency_stop()
    assert resp["status"] == "stopped"
    assert len(tm.lock_manager.get_held_locks()) == 0
