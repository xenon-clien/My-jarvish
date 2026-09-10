"""Comprehensive unit and integration test suite for YouTube V2 Contract & Adapter."""
import pytest
from backend.nlu.youtube_nlu import youtube_nlu
from backend.adapters.youtube_adapter import youtube_adapter
from backend.core.command_processor import command_processor, ExecutionStatus


def test_v2_contract_all_intents_slot_extraction():
    """Verify that all 25 canonical V2 intents extract correct semantic slots."""
    test_cases = [
        ("YouTube kholo", "youtube.open", {}, None),
        ("CarryMinati search karo", "youtube.search", {"query": "carryminati"}, None),
        ("pehli short chalao", "youtube.play_short", {"ordinal": 1}, 1),
        ("short chalao", "youtube.play_short", {"ordinal": 1}, 1),
        ("3rd short laga do", "youtube.play_short", {"ordinal": 3}, 3),
        ("agla short", "youtube.next_short", {}, None),
        ("pichla short", "youtube.previous_short", {}, None),
        ("rok do", "youtube.pause", {}, None),
        ("chala do", "youtube.resume", {}, None),
        ("fullscreen karo", "youtube.set_fullscreen", {"enabled": True}, None),
        ("fullscreen hatao", "youtube.set_fullscreen", {"enabled": False}, None),
        ("theater mode chalu karo", "youtube.set_theater_mode", {"enabled": True}, None),
        ("theater mode band karo", "youtube.set_theater_mode", {"enabled": False}, None),
        ("miniplayer chalu karo", "youtube.set_miniplayer", {"enabled": True}, None),
        ("captions on karo", "youtube.set_captions", {"enabled": True}, None),
        ("caption band karo", "youtube.set_captions", {"enabled": False}, None),
        ("1.5x speed kar do", "youtube.set_playback_speed", {"rate": 1.5}, None),
        ("speed badhao", "youtube.speed_up", {"step": 0.25}, None),
        ("speed kam karo", "youtube.speed_down", {"step": 0.25}, None),
        ("10 second aage", "youtube.seek_forward", {"seconds": 10}, None),
        ("ek minute aage", "youtube.seek_forward", {"seconds": 60}, None),
        ("20 sec peeche", "youtube.seek_backward", {"seconds": 20}, None),
        ("2 minute peeche", "youtube.seek_backward", {"seconds": 120}, None),
        ("2 minute 30 second pe le jao", "youtube.seek_timestamp", {"seconds": 150}, None),
        ("volume 50 kar do", "youtube.set_volume", {"level": 50}, None),
        ("volume badhao", "youtube.volume_up", {"step": 10}, None),
        ("volume kam karo", "youtube.volume_down", {"step": 10}, None),
        ("mute karo", "youtube.mute", {}, None),
        ("unmute karo", "youtube.unmute", {}, None),
        ("video like karo", "youtube.set_like", {"enabled": True}, None),
        ("like hatao", "youtube.set_like", {"enabled": False}, None),
        ("replay karo", "youtube.replay", {}, None),
    ]

    for utterance, exp_action, exp_args, exp_ord in test_cases:
        res = youtube_nlu.parse(utterance)
        assert res.canonical_action == exp_action, f"Failed action for '{utterance}': got {res.canonical_action}"
        if exp_ord is not None:
            assert res.ordinal == exp_ord, f"Failed ordinal for '{utterance}': got {res.ordinal}"
        for k, v in exp_args.items():
            assert res.arguments.get(k) == v, f"Failed arg '{k}' for '{utterance}': expected {v}, got {res.arguments.get(k)}"


def test_v2_adapter_methods_exist():
    """Verify all 25 canonical V2 intents are implemented in YouTubeAdapter."""
    methods = [
        "open", "search", "play_video", "play_short", "next_short", "prev_short",
        "pause", "resume", "set_fullscreen", "set_theater_mode", "set_miniplayer",
        "set_captions", "set_playback_speed", "speed_up", "speed_down",
        "seek_forward", "seek_backward", "seek_timestamp", "set_volume",
        "volume_up", "volume_down", "mute", "unmute", "set_like", "replay"
    ]
    for m in methods:
        assert hasattr(youtube_adapter, m), f"YouTubeAdapter missing method '{m}'"


def test_negations_and_self_corrections():
    """Verify negations and corrections."""
    res_neg = youtube_nlu.parse("pause mat karna")
    assert res_neg.is_negated is True
    assert res_neg.canonical_action == "youtube.none_negated"

    res_corr = youtube_nlu.parse("second nahi first short chalao")
    assert res_corr.canonical_action == "youtube.play_short"
    assert res_corr.ordinal == 1


def test_v2_adapter_observe_browser_state():
    """Verify observe_browser_state returns expected structure without crashing."""
    state = youtube_adapter.observe_browser_state()
    assert isinstance(state, dict)
    required_keys = ["browser_running", "browser_name", "hwnd", "window_title", "is_foreground", "url", "is_youtube", "is_shorts", "is_watch"]
    for k in required_keys:
        assert k in state, f"Missing key '{k}' in observed state"


def test_v2_adapter_verify_state():
    """Verify closed-loop state verifier logic."""
    # When result is error
    assert youtube_adapter.verify_state("youtube.pause", "PAUSED", {"status": "error"}) == "BROKEN"

    # Status must be one of the three contract states
    status = youtube_adapter.verify_state("youtube.pause", "PAUSED", {"status": "success"})
    assert status in ["LIVE_VERIFIED", "DEGRADED", "BROKEN"]


def test_v2_adapter_execute_canonical_all_intents():
    """Verify execute_canonical covers all 25 canonical actions and returns structured payload."""
    test_intents = [
        ("youtube.open", {"query": ""}, "NAVIGATED_HOME"),
        ("youtube.search", {"query": "carryminati"}, "SEARCH_RESULTS_DISPLAYED"),
        ("youtube.play_video", {"query": "carryminati", "ordinal": 1}, "VIDEO_PLAYING"),
        ("youtube.play_short", {"ordinal": 1}, "SHORT_PLAYING"),
        ("youtube.next_short", {}, "NAVIGATED_NEXT_SHORT"),
        ("youtube.previous_short", {}, "NAVIGATED_PREV_SHORT"),
        ("youtube.pause", {}, "PAUSED"),
        ("youtube.resume", {}, "PLAYING"),
        ("youtube.set_fullscreen", {"enabled": True}, "FULLSCREEN_STATE_SET"),
        ("youtube.set_theater_mode", {"enabled": True}, "THEATER_MODE_SET"),
        ("youtube.set_miniplayer", {"enabled": True}, "MINIPLAYER_STATE_SET"),
        ("youtube.set_captions", {"enabled": True}, "CAPTIONS_STATE_SET"),
        ("youtube.set_playback_speed", {"rate": 1.25}, "SPEED_SET"),
        ("youtube.speed_up", {"step": 0.25}, "SPEED_INCREASED"),
        ("youtube.speed_down", {"step": 0.25}, "SPEED_DECREASED"),
        ("youtube.seek_forward", {"seconds": 10}, "SEEKED_FORWARD"),
        ("youtube.seek_backward", {"seconds": 10}, "SEEKED_BACKWARD"),
        ("youtube.seek_timestamp", {"seconds": 150, "raw_timestamp": "02:30"}, "SEEKED_TO_TIMESTAMP"),
        ("youtube.set_volume", {"level": 60}, "VOLUME_LEVEL_SET"),
        ("youtube.volume_up", {"step": 10}, "VOLUME_INCREASED"),
        ("youtube.volume_down", {"step": 10}, "VOLUME_DECREASED"),
        ("youtube.mute", {}, "MUTED"),
        ("youtube.unmute", {}, "UNMUTED"),
        ("youtube.set_like", {"enabled": True}, "LIKED_STATE_SET"),
        ("youtube.replay", {}, "REPLAYED"),
    ]

    for action, args, exp_effect in test_intents:
        # Mock sub-operations or test structure
        res = youtube_adapter.execute_canonical(action, args)
        assert isinstance(res, dict)
        assert res["canonical_action"] == action
        assert res["expected_effect"] == exp_effect
        assert res["status"] in ["LIVE_VERIFIED", "DEGRADED", "BROKEN", "SIMULATED", "LIVE_AUTOMATION_DISABLED"]
        assert "message" in res
        assert "observed_state" in res


@pytest.mark.asyncio
async def test_v2_command_processor_youtube_routing():
    """Verify CommandProcessor routes YouTube commands through YouTubeAdapter."""
    ctx = await command_processor.process_command("YouTube par CarryMinati search karo", source="test")
    assert ctx.action == "youtube.search"
    assert ctx.status in [ExecutionStatus.VERIFIED_SUCCESS, ExecutionStatus.VERIFIED_FAILURE, ExecutionStatus.SIMULATED]
    assert "carryminati" in ctx.response_message.lower() or "youtube" in ctx.response_message.lower() or "disabled" in ctx.response_message.lower()

    ctx2 = await command_processor.process_command("short chalao", source="test")
    assert ctx2.action == "youtube.play_short"
    assert ctx2.status in [ExecutionStatus.VERIFIED_SUCCESS, ExecutionStatus.VERIFIED_FAILURE, ExecutionStatus.SIMULATED]


@pytest.mark.asyncio
async def test_v2_command_processor_scroll_and_video_ordinal():
    """Verify CommandProcessor routes scroll commands and play first video cleanly."""
    ctx_scroll_down = await command_processor.process_command("neeche scroll karo", source="test")
    assert ctx_scroll_down.action == "youtube.scroll"
    assert ctx_scroll_down.arguments.get("direction") == "down"
    assert ctx_scroll_down.status in [ExecutionStatus.VERIFIED_SUCCESS, ExecutionStatus.SIMULATED]

    ctx_scroll_up = await command_processor.process_command("upar scroll karo", source="test")
    assert ctx_scroll_up.action == "youtube.scroll"
    assert ctx_scroll_up.arguments.get("direction") == "up"
    assert ctx_scroll_up.status in [ExecutionStatus.VERIFIED_SUCCESS, ExecutionStatus.SIMULATED]

    res_parse = youtube_nlu.parse("play first video")
    assert res_parse.canonical_action == "youtube.play_video"
    assert res_parse.arguments.get("ordinal") == 1


