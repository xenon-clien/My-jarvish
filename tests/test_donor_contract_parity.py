"""Contract Parity Test Suite: Production Authority vs Donor Clean Build.

Verifies that the production codebase satisfies all 25 canonical YouTube intents,
passes all parsing test cases from the donor clean build, and properly classifies
Astra / Gemini provider errors.
"""
import pytest
from backend.nlu.youtube_nlu import youtube_nlu
from backend.adapters.youtube_adapter import youtube_adapter
from backend.ai.providers import AstraProvider, ErrorCategory


def test_donor_contract_all_25_actions_implemented():
    """Verify that all 25 actions from donor contracts/youtube_actions.json are present."""
    donor_canonical_25 = [
        "open", "search", "play_video", "play_short", "next_short", "previous_short",
        "pause", "resume", "set_fullscreen", "set_theater_mode", "set_miniplayer",
        "set_captions", "set_playback_speed", "speed_up", "speed_down",
        "seek_forward", "seek_backward", "seek_timestamp", "set_volume",
        "volume_up", "volume_down", "mute", "unmute", "set_like", "replay"
    ]
    for action in donor_canonical_25:
        method_name = "prev_short" if action == "previous_short" else action
        has_method = hasattr(youtube_adapter, action) or hasattr(youtube_adapter, method_name)
        assert has_method, f"Production YouTubeAdapter is missing canonical action method: '{action}'"


def test_donor_fast_parser_parity_cases():
    """Verify production NLU correctly parses test cases from donor test_parser.py."""
    # 1. pehli short chala -> play_short, ordinal: 1
    res1 = youtube_nlu.parse("pehli short chala")
    assert res1.canonical_action == "youtube.play_short"
    assert res1.arguments.get("ordinal") == 1

    # 2. third short play karo -> play_short, ordinal: 3
    res2 = youtube_nlu.parse("third short play karo")
    assert res2.canonical_action == "youtube.play_short"
    assert res2.arguments.get("ordinal") == 3

    # 3. YouTube pe MrBeast search karo -> search, query: "mrbeast"
    res3 = youtube_nlu.parse("YouTube pe MrBeast search karo")
    assert res3.canonical_action == "youtube.search"
    assert "mrbeast" in res3.arguments.get("query", "").lower()

    # 4. 2 minute 30 second pe jao -> seek_timestamp, seconds: 150
    res4 = youtube_nlu.parse("2 minute 30 second pe jao")
    assert res4.canonical_action == "youtube.seek_timestamp"
    assert res4.arguments.get("seconds") == 150

    # 5. volume 40 kar do -> set_volume, level: 40
    res5 = youtube_nlu.parse("volume 40 kar do")
    assert res5.canonical_action == "youtube.set_volume"
    assert res5.arguments.get("level") == 40


def test_first_video_and_scrolling_utterances():
    """Verify user problem cases: 'play first video' and scrolling."""
    # First video
    res_v1 = youtube_nlu.parse("play first video")
    assert res_v1.canonical_action == "youtube.play_video"
    assert res_v1.arguments.get("ordinal") == 1

    res_v2 = youtube_nlu.parse("pehli video chalao")
    assert res_v2.canonical_action == "youtube.play_video"
    assert res_v2.arguments.get("ordinal") == 1

    # Scrolling
    res_s1 = youtube_nlu.parse("neeche scroll karo")
    assert res_s1.canonical_action == "youtube.scroll"
    assert res_s1.arguments.get("direction") == "down"

    res_s2 = youtube_nlu.parse("upar scroll karo")
    assert res_s2.canonical_action == "youtube.scroll"
    assert res_s2.arguments.get("direction") == "up"


def test_donor_provider_error_classification_parity():
    """Verify error classification matches donor test_provider_errors.py expectations."""
    provider = AstraProvider()

    # 1. Quota exhausted -> CATEGORY_B_QUOTA_EXHAUSTED
    cat1, _ = provider.classify_error(429, '{"error":{"type":"insufficient_quota"}}')
    assert cat1 == ErrorCategory.CATEGORY_B_QUOTA_EXHAUSTED

    # 2. Rate limit (temporary) -> CATEGORY_A_TEMPORARY
    cat2, _ = provider.classify_error(429, 'rate limit exceeded, try again later')
    assert cat2 == ErrorCategory.CATEGORY_A_TEMPORARY

    # 3. Server error -> CATEGORY_A_TEMPORARY
    cat3, _ = provider.classify_error(503, 'temporary unavailable')
    assert cat3 == ErrorCategory.CATEGORY_A_TEMPORARY

    # 4. Auth invalid -> CATEGORY_C_AUTH_INVALID
    cat4, _ = provider.classify_error(401, 'invalid api key')
    assert cat4 == ErrorCategory.CATEGORY_C_AUTH_INVALID
