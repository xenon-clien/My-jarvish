"""Unit & Integration tests for Language Normalizer & Deterministic Router."""
import pytest
from nlu import DeterministicRouter, CanonicalIntent


def test_youtube_shorts_commands():
    test_cases = [
        ("play first short", "youtube.play_first_short"),
        ("pehla short chalao", "youtube.play_first_short"),
        ("pehla short play karo", "youtube.play_first_short"),
        ("पहला शॉर्ट चलाओ", "youtube.play_first_short"),
        ("youtube pe pehla short chalao", "youtube.play_first_short"),
        ("next short", "youtube.next_short"),
        ("agla short", "youtube.next_short"),
        ("previous short", "youtube.prev_short"),
        ("pichla short", "youtube.prev_short"),
    ]
    for phrase, expected_tool in test_cases:
        res = DeterministicRouter.route_command(phrase)
        assert res is not None, f"Failed to route '{phrase}'"
        assert res.tool_name == expected_tool, f"Expected {expected_tool} for '{phrase}', got {res.tool_name}"


def test_youtube_media_controls():
    test_cases = [
        ("youtube kholo", "youtube.open"),
        ("youtube open karo", "youtube.open"),
        ("pause karo", "youtube.pause"),
        ("rok do", "youtube.pause"),
        ("resume karo", "youtube.resume"),
        ("next video", "youtube.next_video"),
        ("pichla video", "youtube.prev_video"),
        ("video like karo", "youtube.like"),
    ]
    for phrase, expected_tool in test_cases:
        res = DeterministicRouter.route_command(phrase)
        assert res is not None, f"Failed to route '{phrase}'"
        assert res.tool_name == expected_tool, f"Expected {expected_tool} for '{phrase}', got {res.tool_name}"


def test_system_volume_controls():
    test_cases = [
        ("volume badhao", "system.volume_up"),
        ("volume up", "system.volume_up"),
        ("volume kam karo", "system.volume_down"),
        ("mute", "system.mute"),
        ("unmute", "system.unmute"),
    ]
    for phrase, expected_tool in test_cases:
        res = DeterministicRouter.route_command(phrase)
        assert res is not None, f"Failed to route '{phrase}'"
        assert res.tool_name == expected_tool, f"Expected {expected_tool} for '{phrase}', got {res.tool_name}"


def test_whatsapp_controls():
    res = DeterministicRouter.route_command("whatsapp kholo")
    assert res is not None and res.tool_name == "whatsapp.open"

    res_call = DeterministicRouter.route_command("call Harsh")
    assert res_call is not None and res_call.tool_name == "whatsapp.voice_call"
    assert res_call.arguments.get("contact") == "Harsh"


def test_emergency_stop_and_health():
    res_stop = DeterministicRouter.route_command("stop")
    assert res_stop is not None and res_stop.tool_name == "system.stop"

    res_ruk = DeterministicRouter.route_command("ruk jao")
    assert res_ruk is not None and res_ruk.tool_name == "system.stop"

    res_health = DeterministicRouter.route_command("health check")
    assert res_health is not None and res_health.tool_name == "diagnostics.health_check"
