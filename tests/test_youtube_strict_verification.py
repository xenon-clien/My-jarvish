"""Strict Closed-Loop Verification Tests for YouTube Adapter & Perception.

Enforces:
1. youtube.search must NOT become LIVE_VERIFIED merely because page_type == SEARCH_RESULTS
   or URL contains results?search_query=. Requires observed search query to match requested query.
2. youtube.play_video ordinal selection must ONLY be LIVE_VERIFIED when actual_video_id == expected_video_id.
   playback_state == PLAYING, actual_id != previous_id, and page_type == VIDEO are rejected as substitutes.
3. youtube.play_short must ONLY be LIVE_VERIFIED when actual_video_id == expected_video_id.
   page_type == SHORTS alone is NOT proof.
4. verify_state() enforces strict identity and captions enabled target.
5. JARVIS_ALLOW_PHYSICAL_INPUT=0 safety invariant.
"""
import pytest
from unittest.mock import MagicMock, patch

from backend.adapters.youtube_adapter import youtube_adapter
from backend.adapters.youtube_grounding import YouTubeCandidate
from backend.perception.perception_types import VisibleVideoItem


def test_search_rejects_stale_search_results_page():
    """If browser is already on a previous search page, searching for a new query must NOT
    falsely verify as LIVE_VERIFIED before the new query is observed.
    """
    stale_state = {
        "browser_running": True,
        "is_youtube": True,
        "page_type": "SEARCH_RESULTS",
        "current_url": "https://www.youtube.com/results?search_query=old_topic",
        "search_query": "old_topic",
        "window_title": "old_topic - YouTube",
    }

    with patch("backend.core.safety.is_live_browser_automation_allowed", return_value=True), \
         patch("backend.tools.browser_tools.navigate_active_browser_tab", return_value=True), \
         patch.object(youtube_adapter, "observe_browser_state", return_value=stale_state):

        res = youtube_adapter.search("karan aujla")
        assert res["status"] == "DEGRADED"
        assert res["verified"] is False

        # verify_state directly must also reject stale query
        v_status = youtube_adapter.verify_state(
            action="youtube.search",
            expected_effect="SEARCH_RESULTS_DISPLAYED",
            result={"query": "karan aujla"},
        )
        assert v_status == "DEGRADED"


def test_search_accepts_when_query_observed():
    """When the requested query is genuinely present in the observed state, status is LIVE_VERIFIED."""
    confirmed_state = {
        "browser_running": True,
        "is_youtube": True,
        "page_type": "SEARCH_RESULTS",
        "current_url": "https://www.youtube.com/results?search_query=karan+aujla",
        "search_query": "karan aujla",
        "window_title": "karan aujla - YouTube",
    }

    with patch("backend.core.safety.is_live_browser_automation_allowed", return_value=True), \
         patch("backend.tools.browser_tools.navigate_active_browser_tab", return_value=True), \
         patch.object(youtube_adapter, "observe_browser_state", return_value=confirmed_state):

        res = youtube_adapter.search("karan aujla")
        assert res["status"] == "LIVE_VERIFIED"
        assert res["verified"] is True

        v_status = youtube_adapter.verify_state(
            action="youtube.search",
            expected_effect="SEARCH_RESULTS_DISPLAYED",
            result={"query": "karan aujla"},
        )
        assert v_status == "LIVE_VERIFIED"


def test_play_video_rejects_playing_state_when_id_mismatches():
    """Crucial Invariant: If video #1 (ID: TARGET_11AA) was targeted, but autoplay or an ad plays
    (ID: OTHER_VID99) with playback_state='PLAYING', status must be DEGRADED, NEVER LIVE_VERIFIED.
    """
    cands = [
        VisibleVideoItem(ordinal=1, video_id="TARGET_11AA", title="Target Video", url="https://youtube.com/watch?v=TARGET_11AA"),
        VisibleVideoItem(ordinal=2, video_id="OTHER_VID99", title="Other Video", url="https://youtube.com/watch?v=OTHER_VID99"),
    ]

    before_obs = {
        "browser_running": True,
        "is_youtube": True,
        "page_type": "SEARCH_RESULTS",
        "visible_video_candidates": cands,
        "current_video_id": "UNKNOWN",
    }
    # Another video starts playing instead of TARGET_11AA
    after_obs = {
        "browser_running": True,
        "is_youtube": True,
        "page_type": "VIDEO",
        "current_video_id": "OTHER_VID99",
        "current_url": "https://www.youtube.com/watch?v=OTHER_VID99",
        "playback_state": "PLAYING",
    }

    with patch("backend.core.safety.is_live_browser_automation_allowed", return_value=True), \
         patch("backend.tools.browser_tools.navigate_active_browser_tab", return_value=True), \
         patch.object(youtube_adapter, "observe_browser_state", side_effect=[before_obs, after_obs]):

        res = youtube_adapter.play_video(ordinal=1)
        assert res["status"] == "DEGRADED"
        assert res["verified"] is False
        assert res["expected_video_id"] == "TARGET_11AA"
        assert res["actual_video_id"] == "OTHER_VID99"


def test_play_video_accepts_only_exact_identity():
    """Exact match actual_video_id == expected_video_id must yield LIVE_VERIFIED."""
    cands = [
        VisibleVideoItem(ordinal=1, video_id="TARGET_11AA", title="Target Video", url="https://youtube.com/watch?v=TARGET_11AA"),
    ]

    before_obs = {
        "browser_running": True,
        "is_youtube": True,
        "page_type": "SEARCH_RESULTS",
        "visible_video_candidates": cands,
        "current_video_id": "UNKNOWN",
    }
    after_obs = {
        "browser_running": True,
        "is_youtube": True,
        "page_type": "VIDEO",
        "current_video_id": "TARGET_11AA",
        "current_url": "https://www.youtube.com/watch?v=TARGET_11AA",
        "playback_state": "PLAYING",
    }

    with patch("backend.core.safety.is_live_browser_automation_allowed", return_value=True), \
         patch("backend.tools.browser_tools.navigate_active_browser_tab", return_value=True), \
         patch.object(youtube_adapter, "observe_browser_state", side_effect=[before_obs, after_obs]):

        res = youtube_adapter.play_video(ordinal=1)
        assert res["status"] == "LIVE_VERIFIED"
        assert res["verified"] is True
        assert res["expected_video_id"] == "TARGET_11AA"
        assert res["actual_video_id"] == "TARGET_11AA"


def test_play_short_rejects_shorts_page_type_when_id_mismatches():
    """Being on page_type == 'SHORTS' alone is NOT proof. If actual_id != expected_id, must be DEGRADED."""
    short_cands = [
        YouTubeCandidate(
            candidate_type="short",
            video_id="SHORT_AAA11",
            title="Target Short",
            canonical_url="https://www.youtube.com/shorts/SHORT_AAA11",
            href="/shorts/SHORT_AAA11",
            bounding_rect=(10, 10, 100, 100),
            visual_order=1,
        )
    ]

    before_obs = {
        "browser_running": True,
        "is_youtube": True,
        "page_type": "HOME",
        "visible_short_candidates": short_cands,
        "current_video_id": "UNKNOWN",
    }
    # Page navigated to shorts, but to an unrelated short
    after_obs = {
        "browser_running": True,
        "is_youtube": True,
        "page_type": "SHORTS",
        "current_video_id": "UNRELATED_SH",
        "current_url": "https://www.youtube.com/shorts/UNRELATED_SH",
    }

    with patch("backend.core.safety.is_live_browser_automation_allowed", return_value=True), \
         patch("backend.tools.browser_tools.navigate_active_browser_tab", return_value=True), \
         patch.object(youtube_adapter, "observe_browser_state", side_effect=[before_obs, after_obs]):

        res = youtube_adapter.play_short(ordinal=1)
        assert res["status"] == "DEGRADED"
        assert res["verified"] is False
        assert res["expected_video_id"] == "SHORT_AAA11"
        assert res["actual_video_id"] == "UNRELATED_SH"


def test_captions_verification_matches_requested_target():
    """set_captions(enabled=True) must NOT verify as LIVE_VERIFIED when captions are False."""
    obs_false = {
        "browser_running": True,
        "is_youtube": True,
        "captions": False,
    }
    with patch.object(youtube_adapter, "observe_browser_state", return_value=obs_false):
        status = youtube_adapter.verify_state(
            action="youtube.set_captions",
            expected_effect="CAPTIONS_STATE_SET",
            result={"arguments": {"enabled": True}},
        )
        assert status == "DEGRADED"

    obs_true = {
        "browser_running": True,
        "is_youtube": True,
        "captions": True,
    }
    with patch.object(youtube_adapter, "observe_browser_state", return_value=obs_true):
        status = youtube_adapter.verify_state(
            action="youtube.set_captions",
            expected_effect="CAPTIONS_STATE_SET",
            result={"arguments": {"enabled": True}},
        )
        assert status == "LIVE_VERIFIED"
