"""Regression tests specifically proving the fix for the 'Open YouTube' false-success bug.

Tests:
1. Safe/dev mode: Open YouTube -> verified=False, NO LIVE_VERIFIED, NO success claim.
2. Normal runtime: Actuation succeeds + observer confirms youtube.com -> LIVE_VERIFIED, verified=True, success message allowed.
3. Actuation returns but observer never confirms YouTube -> DEGRADED, verified=False, NO false success speech.
4. Observer raises exception -> verified=False.
5. Generic Chrome exists but no YouTube tab -> verified=False.
6. Physical input disabled -> youtube.open works without SetCursorPos, mouse_event, or keybd_event.
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.adapters.youtube_adapter import youtube_adapter
from backend.core.command_processor import command_processor, ExecutionStatus


def test_1_safe_dev_mode_open_youtube_no_false_success():
    """TEST 1: In safe/dev mode, Open YouTube must return verified=False, NO LIVE_VERIFIED, and NO success claim."""
    with patch("backend.core.safety.is_live_browser_automation_allowed", return_value=False):
        res = youtube_adapter.open()

        assert res["status"] in ["LIVE_AUTOMATION_DISABLED", "SIMULATED"]
        assert res["status"] != "LIVE_VERIFIED"
        assert res.get("verified") is False
        assert "open kar diya" not in res.get("message", "").lower()

        canonical_res = youtube_adapter.execute_canonical("youtube.open")
        assert canonical_res["status"] in ["LIVE_AUTOMATION_DISABLED", "SIMULATED"]
        assert canonical_res["status"] != "LIVE_VERIFIED"
        assert canonical_res["verified"] is False
        assert "open kar diya" not in canonical_res.get("message", "").lower()


@pytest.mark.asyncio
async def test_1b_safe_dev_mode_command_processor_no_success_speech():
    """TEST 1b: Command processor under safe/dev mode must NOT mark VERIFIED_SUCCESS or speak success."""
    with patch("backend.core.safety.is_live_browser_automation_allowed", return_value=False):
        ctx = await command_processor.process_command("Open YouTube", source="voice")
        assert ctx.status != ExecutionStatus.VERIFIED_SUCCESS
        assert ctx.verified is False
        assert "open kar diya" not in ctx.response_message.lower()


def test_2_normal_runtime_confirmed_youtube_live_verified():
    """TEST 2: Normal runtime + browser actuation succeeds + observer confirms youtube.com -> LIVE_VERIFIED."""
    mock_state = {
        "browser_running": True,
        "is_youtube": True,
        "current_url": "https://www.youtube.com/",
        "window_title": "YouTube - Google Chrome",
        "page_type": "HOME",
    }

    with patch("backend.core.safety.is_live_browser_automation_allowed", return_value=True), \
         patch("backend.tools.browser_tools.launch_in_google_chrome") as mock_launch, \
         patch.object(youtube_adapter, "observe_browser_state", return_value=mock_state):

        res = youtube_adapter.open()

        assert res["status"] == "LIVE_VERIFIED"
        assert res["verified"] is True
        assert "Haan Shivam, YouTube open kar diya hai." in res["message"]

        # Verify _verify_youtube_active also confirms
        assert youtube_adapter._verify_youtube_active() is True


def test_3_actuation_returns_but_observer_never_confirms_degraded():
    """TEST 3: Actuation returns but observer never confirms YouTube -> DEGRADED, verified=False, no success claim."""
    unconfirmed_state = {
        "browser_running": True,
        "is_youtube": False,
        "current_url": "about:blank",
        "window_title": "New Tab - Google Chrome",
        "page_type": "UNKNOWN",
    }

    with patch("backend.core.safety.is_live_browser_automation_allowed", return_value=True), \
         patch("backend.tools.browser_tools.launch_in_google_chrome"), \
         patch.object(youtube_adapter, "observe_browser_state", return_value=unconfirmed_state):

        res = youtube_adapter.open()

        assert res["status"] == "DEGRADED"
        assert res["verified"] is False
        assert "Haan Shivam, YouTube open kar diya hai." not in res["message"]
        assert "confirm nahi kar pa raha" in res["message"]


def test_4_observer_exception_returns_verified_false():
    """TEST 4: Observer raises an exception during verification -> must return verified=False without crashing."""
    with patch.object(youtube_adapter, "observe_browser_state", side_effect=RuntimeError("UIA COM Exception")):
        is_active = youtube_adapter._verify_youtube_active()
        assert is_active is False


def test_5_generic_chrome_exists_without_youtube_returns_verified_false():
    """TEST 5: Generic Chrome exists but no YouTube tab -> verified=False."""
    generic_chrome_state = {
        "browser_running": True,
        "is_youtube": False,
        "current_url": "chrome://newtab",
        "window_title": "New Tab - Google Chrome",
        "page_type": "UNKNOWN",
    }

    with patch.object(youtube_adapter, "observe_browser_state", return_value=generic_chrome_state):
        is_active = youtube_adapter._verify_youtube_active()
        assert is_active is False


def test_6_physical_input_disabled_zero_hardware_calls(call_tracker):
    """TEST 6: Physical input disabled -> youtube.open operates without SetCursorPos, mouse_event, or keybd_event."""
    call_tracker.reset()

    mock_state = {
        "browser_running": True,
        "is_youtube": True,
        "current_url": "https://www.youtube.com/",
        "window_title": "YouTube - Google Chrome",
        "page_type": "HOME",
    }

    with patch("backend.core.safety.is_live_browser_automation_allowed", return_value=True), \
         patch("backend.core.safety.is_physical_automation_allowed", return_value=False), \
         patch("backend.tools.browser_tools.launch_in_google_chrome") as mock_launch, \
         patch.object(youtube_adapter, "observe_browser_state", return_value=mock_state):

        res = youtube_adapter.open()

        assert res["status"] == "LIVE_VERIFIED"
        assert res["verified"] is True
        assert call_tracker.set_cursor_pos_calls == 0
        assert call_tracker.mouse_event_calls == 0
        assert call_tracker.keybd_event_calls == 0
