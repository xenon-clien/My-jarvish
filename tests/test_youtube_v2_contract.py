"""Comprehensive unit and integration test suite for YouTube V2 Contract & Adapter."""
import pytest
from backend.nlu.youtube_nlu import youtube_nlu
from backend.adapters.youtube_adapter import youtube_adapter
from backend.core.command_processor import command_processor


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
