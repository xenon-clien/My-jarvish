"""Unit tests for Windows hardware media and playback controls."""
import pytest
from backend.tools.media_tools import control_media


def test_media_control_actions(monkeypatch):
    """Test media control actions execution."""
    sent_keys = []
    from backend.tools import media_tools
    monkeypatch.setattr(media_tools, "is_physical_automation_allowed", lambda: True)
    monkeypatch.setattr(media_tools, "_focus_media_window", lambda: None)
    monkeypatch.setattr(media_tools, "_click_video_player_center", lambda: None)
    monkeypatch.setattr(media_tools, "_send_key_event", lambda vk: sent_keys.append(vk))

    # Mock pycaw so tests do not mute the host system audio sessions
    from unittest.mock import MagicMock
    monkeypatch.setattr("pycaw.pycaw.AudioUtilities.GetAllSessions", lambda: [])
    monkeypatch.setattr("pycaw.pycaw.AudioUtilities.GetSpeakers", lambda: MagicMock())

    # Play / Pause
    res_play = control_media("play_pause")
    assert res_play["status"] == "success"
    assert "Play/Pause" in res_play["message"]

    # Next track
    res_next = control_media("next")
    assert res_next["status"] == "success"
    assert "next track" in res_next["message"]

    # Volume up
    res_vol = control_media("volume_up")
    assert res_vol["status"] == "success"

    # Volume down
    res_vol_down = control_media("volume_down")
    assert res_vol_down["status"] == "success"

    # Mute
    res_mute = control_media("mute")
    assert res_mute["status"] == "success"


def test_invalid_media_action():
    """Ensure invalid media action strings are rejected."""
    with pytest.raises(ValueError) as exc_info:
        control_media("invalid_action_xyz")
    assert "Unknown media action" in str(exc_info.value)
