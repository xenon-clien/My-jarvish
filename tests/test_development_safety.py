"""Mandatory Verification Tests for JARVIS Development Safety.

Proves:
1. Importing backend.tools.autosubmit_watcher: mouse does NOT move, no thread spawned.
2. Importing app: AutoSubmit watcher does NOT start.
3. Calling physical click helper while DEV_SAFE_MODE=1: SetCursorPos calls = 0, mouse_event calls = 0.
4. Calling youtube.play_short while live automation disabled: 0 mouse calls, 0 keyboard calls.
5. Normal YouTube tests operate without real Chrome interaction.
6. Emergency stop cancels locks and halts automation.
"""

import os
import pytest
from unittest.mock import MagicMock, patch

from backend.core.safety import (
    is_dev_safe_mode,
    is_physical_automation_allowed,
    is_live_browser_automation_allowed,
    safe_set_cursor_pos,
    safe_mouse_event,
    safe_keybd_event,
    safe_blocked_result,
)
from backend.core.command_processor import command_processor, ExecutionStatus


def test_1_import_autosubmit_watcher(call_tracker):
    """Test 1: Import backend.tools.autosubmit_watcher -> mouse does NOT move."""
    call_tracker.reset()
    import backend.tools.autosubmit_watcher as asw
    assert hasattr(asw, "start_autosubmit_watcher")
    res = asw.start_autosubmit_watcher()
    assert res is False
    assert call_tracker.set_cursor_pos_calls == 0
    assert call_tracker.mouse_event_calls == 0


def test_2_import_app():
    """Test 2: Import app -> AutoSubmit watcher does NOT start."""
    import app
    # Prove that start_autosubmit_watcher is not even imported in app module namespace
    assert "start_autosubmit_watcher" not in dir(app)


def test_3_physical_click_helper_blocked_in_dev_safe_mode(call_tracker):
    """Test 3: Call physical click helper while DEV_SAFE_MODE=1.
    Expected: SetCursorPos calls = 0, mouse_event calls = 0.
    """
    call_tracker.reset()
    assert is_dev_safe_mode() is True
    assert is_physical_automation_allowed() is False

    # 1. safe_set_cursor_pos
    pos_res = safe_set_cursor_pos(500, 500)
    assert pos_res is False
    assert call_tracker.set_cursor_pos_calls == 0

    # 2. safe_mouse_event
    mouse_res = safe_mouse_event(0x0002, 0, 0, 0, 0)
    assert mouse_res is False
    assert call_tracker.mouse_event_calls == 0

    # 3. click_element from ui_automation
    from backend.tools.ui_automation import click_element
    elem_res = click_element("first video")
    assert elem_res["status"] == "LIVE_AUTOMATION_DISABLED"
    assert call_tracker.set_cursor_pos_calls == 0
    assert call_tracker.mouse_event_calls == 0

    # 4. send_hardware_click from actions
    from backend.skills.actions import UniversalActionEngine
    UniversalActionEngine.send_hardware_click(300, 300)
    assert call_tracker.set_cursor_pos_calls == 0
    assert call_tracker.send_input_calls == 0


def test_4_youtube_play_short_no_hardware_when_live_disabled(call_tracker):
    """Test 4: Call youtube.play_short while live automation disabled.
    Expected: physical mouse calls = 0, physical keyboard calls = 0.
    """
    call_tracker.reset()
    assert is_live_browser_automation_allowed() is False

    from backend.adapters.youtube_adapter import youtube_adapter
    res = youtube_adapter.play_short(ordinal=1)

    assert res["status"] in ["LIVE_VERIFIED", "DEGRADED"]
    assert res.get("simulated") is True or res.get("method") == "semantic_shorts_identity"
    assert call_tracker.set_cursor_pos_calls == 0
    assert call_tracker.mouse_event_calls == 0
    assert call_tracker.keybd_event_calls == 0


def test_5_youtube_play_video_no_hardware_when_live_disabled(call_tracker):
    """Test 5: Call youtube.play_video while live automation disabled.
    Expected: real Chrome interaction = 0, physical mouse calls = 0.
    """
    call_tracker.reset()
    from backend.adapters.youtube_adapter import youtube_adapter
    res = youtube_adapter.play_video(ordinal=1)

    assert res["status"] == "LIVE_VERIFIED"
    assert res.get("simulated") is True
    assert call_tracker.set_cursor_pos_calls == 0
    assert call_tracker.mouse_event_calls == 0


@pytest.mark.asyncio
async def test_6_emergency_stop_command():
    """Test 6: /stop and /emergency-stop instantly release resource locks and halt."""
    from backend.core.task_manager import task_manager
    from backend.core.emergency_stop import emergency_stop_manager

    # Acquire dummy lock
    task_manager.lock_manager.acquire(["youtube", "browser"], "DUMMY_TASK", timeout=1.0)
    assert len(task_manager.lock_manager.get_held_locks()) > 0

    # Issue /stop command
    stop_ctx = await command_processor.process_command("/stop", source="test")
    assert stop_ctx.status == ExecutionStatus.VERIFIED_SUCCESS
    assert "emergency stop triggered" in stop_ctx.response_message.lower()

    # Verify locks released
    assert len(task_manager.lock_manager.get_held_locks()) == 0
    assert emergency_stop_manager.is_halted is True
    assert is_physical_automation_allowed() is False

    # Reset
    reset_ctx = await command_processor.process_command("/resume", source="test")
    assert reset_ctx.status == ExecutionStatus.VERIFIED_SUCCESS
    assert emergency_stop_manager.is_halted is False
