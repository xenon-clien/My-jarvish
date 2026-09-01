"""Unit tests for Memory Subsystems."""
import pytest
from memory.memory_manager import JarvisMemoryManager, memory_manager


def test_short_term_memory():
    mem = JarvisMemoryManager()
    mem.short_term.add_turn("user", "Hello")
    mem.short_term.add_turn("assistant", "Hi Boss!")

    history = mem.short_term.get_recent_history(turns=2)
    assert len(history) == 2
    assert history[0]["content"] == "Hello"
    assert history[1]["content"] == "Hi Boss!"


def test_task_memory():
    mem = JarvisMemoryManager()
    mem.task_memory.record_completed_task("TASK-001", "youtube.play_first_short", {"success": True})
    assert len(mem.task_memory.completed_tasks) == 1
    assert mem.task_memory.completed_tasks[0]["tool"] == "youtube.play_first_short"


def test_preference_memory():
    mem = JarvisMemoryManager()
    mem.preferences.set("theme", "glassmorphic_cyan")
    assert mem.preferences.get("theme") == "glassmorphic_cyan"
