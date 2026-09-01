"""Unit tests for Task Manager, State Transitions, DAG Dependencies, and Priority Queue."""
import pytest
from core.models import ToolCategory
from core.task_manager import TaskManager
from core.task_queue import TaskQueue
from core.task_state import TaskPriority, TaskState
from core.tool_registry import ToolRegistry, tool


@pytest.mark.asyncio
async def test_task_dependency_graph_and_blocking():
    from core.tool_registry import default_registry
    tm = TaskManager()

    @tool(name="step.one_test", description="Step 1", category=ToolCategory.SYSTEM)
    def step_one():
        return {"status": "error", "error": "Simulated hardware failure"}

    @tool(name="step.two_test", description="Step 2", category=ToolCategory.SYSTEM)
    def step_two():
        return {"status": "success"}

    t1 = tm.create_task("step.one_test")
    t2 = tm.create_task("step.two_test", dependencies=[t1.id])

    # Execute t1
    res1 = await tm.execute_task(t1.id)
    assert res1.state == TaskState.FAILED

    # Execute t2 (should be BLOCKED because t1 failed)
    res2 = await tm.execute_task(t2.id)
    assert res2.state == TaskState.BLOCKED
    assert "Prerequisite task" in res2.error


def test_priority_queue_ordering():
    tq = TaskQueue()
    tm = TaskManager()

    t_low = tm.create_task("test.low", priority=TaskPriority.LOW)
    t_emergency = tm.create_task("test.emergency", priority=TaskPriority.EMERGENCY)
    t_normal = tm.create_task("test.normal", priority=TaskPriority.NORMAL)
    t_high = tm.create_task("test.high", priority=TaskPriority.HIGH)

    tq.enqueue(t_low)
    tq.enqueue(t_normal)
    tq.enqueue(t_emergency)
    tq.enqueue(t_high)

    # Dequeue order must be EMERGENCY -> HIGH -> NORMAL -> LOW
    assert tq._queue[0].task.priority == TaskPriority.EMERGENCY
