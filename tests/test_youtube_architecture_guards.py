"""Architecture Invariant and Regression Guard Tests for JARVIS YouTube Runtime V3.

Enforces:
1. Zero physical input symbols (SetCursorPos, mouse_event, SendInput, keybd_event, VK_NEXT, VK_PRIOR) in backend/youtube/.
2. Zero webbrowser.open or external browser spawning in backend/youtube/.
3. Zero synthetic candidate IDs (cand_*, VID_SIM_*, SHORT_SIM_*) in production runtime.
4. Complete prohibition of generic "success" statuses.
5. Strict LIVE_VERIFIED contracts (exact identity, query match, verified == True).
6. Pure DOM execution and same-tab navigation invariants.
"""
import ast
import os
import re
import pytest

from backend.youtube.models import ActionResult, ActionStatus, PageType, PerceptionSnapshot, CurrentVideoInfo, VisibleVideoItem
from backend.youtube.verifier import youtube_verifier
from backend.youtube.session import youtube_session
from backend.youtube.dom import (
    DOM_MEDIA_PAUSE_SCRIPT,
    DOM_MEDIA_PLAY_SCRIPT,
    DOM_MEDIA_REPLAY_SCRIPT,
    get_dom_seek_script,
    get_dom_volume_script,
    get_dom_playback_rate_script,
    normalize_search_query,
)

YOUTUBE_PKG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", "youtube")

def test_zero_physical_input_in_backend_youtube():
    """Guarantee zero physical input automation calls inside backend/youtube/."""
    forbidden_tokens = {
        "SetCursorPos",
        "mouse_event",
        "SendInput",
        "keybd_event",
        "VK_NEXT",
        "VK_PRIOR",
    }
    violations = []
    assert os.path.isdir(YOUTUBE_PKG_DIR), f"Directory {YOUTUBE_PKG_DIR} not found"
    for root, _, files in os.walk(YOUTUBE_PKG_DIR):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    tree = ast.parse(content, filename=file_path)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Name) and node.id in forbidden_tokens:
                            violations.append(f"{file}:{node.lineno}: Name {node.id}")
                        elif isinstance(node, ast.Attribute) and node.attr in forbidden_tokens:
                            violations.append(f"{file}:{node.lineno}: Attribute {node.attr}")
    assert not violations, "Physical input violations found in backend/youtube/: " + ", ".join(violations)

def test_zero_webbrowser_open_in_backend_youtube():
    """Guarantee zero webbrowser.open or external process launch fallbacks inside backend/youtube/."""
    violations = []
    for root, _, files in os.walk(YOUTUBE_PKG_DIR):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    tree = ast.parse(content, filename=file_path)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.Import, ast.ImportFrom)):
                            for alias in getattr(node, "names", []):
                                if alias.name == "webbrowser":
                                    violations.append(f"{file}:{node.lineno}: import webbrowser")
                        elif isinstance(node, ast.Call):
                            if isinstance(node.func, ast.Attribute) and node.func.attr == "open":
                                if isinstance(node.func.value, ast.Name) and node.func.value.id == "webbrowser":
                                    violations.append(f"{file}:{node.lineno}: webbrowser.open call")
    assert not violations, "Webbrowser violations in backend/youtube/: " + ", ".join(violations)

def test_zero_synthetic_candidate_ids_in_backend_youtube():
    """Guarantee no synthetic or fake video IDs (cand_*, VID_SIM_*, SHORT_SIM_*) exist in backend/youtube/."""
    synthetic_patterns = [
        re.compile(r"cand_\d+", re.IGNORECASE),
        re.compile(r"VID_SIM_\d+", re.IGNORECASE),
        re.compile(r"SHORT_SIM_\d+", re.IGNORECASE),
    ]
    violations = []
    for root, _, files in os.walk(YOUTUBE_PKG_DIR):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    file_lines = f.readlines()
                    for idx, line in enumerate(file_lines, start=1):
                        for pattern in synthetic_patterns:
                            if pattern.search(line):
                                violations.append(f"{file}:{idx}: found synthetic candidate ID in '{line.strip()}'")
    assert not violations, "Synthetic candidate ID patterns found in backend/youtube/: " + ", ".join(violations)

def test_no_generic_success_status_allowed():
    """Verify that ActionResult rejects or does not emit generic 'success' as a status."""
    res = ActionResult(
        status=ActionStatus.LIVE_VERIFIED,
        verified=True,
        action="youtube.play_video",
        message="Video started",
    )
    d = res.to_dict()
    assert d["status"] != "success"
    assert d["status"] == "LIVE_VERIFIED"
    for status in ActionStatus:
        assert status.value != "success"
        assert status.value in [
            "LIVE_VERIFIED",
            "DEGRADED",
            "BROKEN",
            "SIMULATED",
            "UNSUPPORTED",
            "CDP_UNAVAILABLE",
            "TARGET_NOT_VISIBLE",
        ]

def test_live_verified_requires_verified_true():
    """Verify that verifier never assigns LIVE_VERIFIED unless verified is True."""
    before = PerceptionSnapshot(
        browser_running=True,
        is_youtube=True,
        page_type=PageType.SEARCH_RESULTS,
        current_video=CurrentVideoInfo(video_id="INITIAL_VID", title="Initial", url=""),
    )
    after = PerceptionSnapshot(
        browser_running=True,
        is_youtube=True,
        page_type=PageType.VIDEO,
        current_video=CurrentVideoInfo(video_id="WRONG_VID", title="Wrong", url=""),
    )
    status, verified, msg = youtube_verifier.verify(
        action="youtube.play_video",
        arguments={"ordinal": 1},
        actuation_result={"actuation_status": ActionStatus.LIVE_VERIFIED, "expected_video_id": "EXPECTED_VID", "ordinal": 1},
        snapshot_before=before,
        snapshot_after=after,
    )
    assert status != ActionStatus.LIVE_VERIFIED
    assert verified is False
    assert status == ActionStatus.DEGRADED

def test_search_verification_requires_observed_query_match():
    """Verify that search only achieves LIVE_VERIFIED when observed query matches requested query."""
    before = PerceptionSnapshot(browser_running=True, is_youtube=True, page_type=PageType.HOME, search_query="")
    stale_after = PerceptionSnapshot(
        browser_running=True,
        is_youtube=True,
        page_type=PageType.SEARCH_RESULTS,
        search_query="old query",
        url="https://www.youtube.com/results?search_query=old+query",
    )
    status_stale, verified_stale, _ = youtube_verifier.verify(
        action="youtube.search",
        arguments={"query": "karan aujla"},
        actuation_result={"actuation_status": ActionStatus.LIVE_VERIFIED},
        snapshot_before=before,
        snapshot_after=stale_after,
    )
    assert status_stale != ActionStatus.LIVE_VERIFIED
    assert verified_stale is False

    matching_after = PerceptionSnapshot(
        browser_running=True,
        is_youtube=True,
        page_type=PageType.SEARCH_RESULTS,
        search_query="karan aujla",
        url="https://www.youtube.com/results?search_query=karan+aujla",
    )
    status_match, verified_match, _ = youtube_verifier.verify(
        action="youtube.search",
        arguments={"query": "karan aujla"},
        actuation_result={"actuation_status": ActionStatus.LIVE_VERIFIED},
        snapshot_before=before,
        snapshot_after=matching_after,
    )
    assert status_match == ActionStatus.LIVE_VERIFIED
    assert verified_match is True

def test_same_tab_navigation_invariant():
    """Verify that YouTubeBrowserSession maintains single-tab reuse pattern."""
    assert hasattr(youtube_session, "navigate_same_tab_sync")
    assert hasattr(youtube_session, "evaluate_script_sync")
    assert hasattr(youtube_session, "is_cdp_available")

def test_pure_dom_player_control_scripts():
    """Verify that DOM scripts operate entirely on document elements without physical dependencies."""
    assert "document.querySelector('video')" in DOM_MEDIA_PAUSE_SCRIPT
    assert "document.querySelector('video')" in DOM_MEDIA_PLAY_SCRIPT
    assert "document.querySelector('video')" in DOM_MEDIA_REPLAY_SCRIPT
    assert "document.querySelector('video')" in get_dom_seek_script(10)
    assert "document.querySelector('video')" in get_dom_volume_script(0.5)
    assert "document.querySelector('video')" in get_dom_playback_rate_script(1.5)

def test_exact_query_extraction_karan_aujla():
    """Verify "search bar mein search karo karan aujla" extracts query="karan aujla"."""
    from backend.nlu.youtube_nlu import youtube_nlu
    parsed = youtube_nlu.parse("search bar mein search karo karan aujla")
    assert parsed.canonical_action in ["youtube.search", "youtube.open"]
    assert parsed.arguments.get("query") == "karan aujla"

def test_play_first_target_resolution():
    """Verify "play first" resolves ordinal=1, query="", and planner picks first visible card."""
    from backend.nlu.youtube_nlu import youtube_nlu
    from backend.youtube.planner import youtube_planner
    parsed = youtube_nlu.parse("play first")
    assert parsed.arguments.get("ordinal") == 1
    assert parsed.arguments.get("query") in [None, ""]

    snapshot = PerceptionSnapshot(
        page_type=PageType.HOME,
        visible_videos=[
            VisibleVideoItem(ordinal=1, video_id="REAL_DOM_VID_001", title="First Video", url=""),
            VisibleVideoItem(ordinal=2, video_id="REAL_DOM_VID_002", title="Second Video", url=""),
        ]
    )
    plan = youtube_planner.plan("youtube.play_video", {"ordinal": 1}, snapshot_before=snapshot)
    assert plan.target_video.video_id == "REAL_DOM_VID_001"

def test_search_rejects_empty_or_whitespace_query():
    """Verify that search verification rejects empty or whitespace-only queries."""
    before = PerceptionSnapshot(browser_running=True, is_youtube=True, page_type=PageType.HOME)
    after = PerceptionSnapshot(browser_running=True, is_youtube=True, page_type=PageType.SEARCH_RESULTS, search_query="")
    status, verified, msg = youtube_verifier.verify(
        action="youtube.search",
        arguments={"query": "   "},
        actuation_result={"actuation_status": ActionStatus.LIVE_VERIFIED},
        snapshot_before=before,
        snapshot_after=after,
    )
    assert status == ActionStatus.DEGRADED
    assert verified is False

def test_next_short_transition_requires_strict_id_change():
    """Verify that next_short rejects stalled short transitions even if actuation succeeded."""
    same_vid = CurrentVideoInfo(video_id="STALLED_SHORT_123", title="Short", url="")
    before = PerceptionSnapshot(browser_running=True, is_youtube=True, page_type=PageType.SHORTS, current_video=same_vid)
    after = PerceptionSnapshot(browser_running=True, is_youtube=True, page_type=PageType.SHORTS, current_video=same_vid)
    status, verified, msg = youtube_verifier.verify(
        action="youtube.next_short",
        arguments={},
        actuation_result={"actuation_status": ActionStatus.LIVE_VERIFIED},
        snapshot_before=before,
        snapshot_after=after,
    )
    assert status == ActionStatus.DEGRADED
    assert verified is False

def test_models_from_dict_preserves_falsy_values():
    """Verify PerceptionSnapshot.from_dict does not coerce 0 volume or False like_state."""
    snap = PerceptionSnapshot.from_dict({
        "volume": 0,
        "like_state": False,
        "is_youtube": True,
    })
    assert snap.player.volume == 0
    assert snap.controls.like_state is False

def test_youtube_adapter_convenience_methods():
    """Verify YouTubeAdapter methods call controller without AttributeError or TypeError."""
    from backend.adapters.youtube_adapter import youtube_adapter
    res1 = youtube_adapter.set_fullscreen(enabled=True)
    assert isinstance(res1, dict)
    res2 = youtube_adapter.set_theater_mode(enabled=True)
    assert isinstance(res2, dict)
    res3 = youtube_adapter.set_miniplayer(enabled=True)
    assert isinstance(res3, dict)
    res4 = youtube_adapter.set_captions(enabled=True)
    assert isinstance(res4, dict)
    res5 = youtube_adapter.seek_timestamp(seconds=120, raw_timestamp="02:00")
    assert isinstance(res5, dict)


def test_youtube_adapter_cannot_promote_unverified_statuses():
    """Verify that YouTubeAdapter NEVER promotes DEGRADED, BROKEN, or SIMULATED to LIVE_VERIFIED."""
    from unittest.mock import patch
    from backend.adapters.youtube_adapter import youtube_adapter
    from backend.youtube.controller import youtube_controller

    # 1. Controller returns DEGRADED -> Adapter must preserve DEGRADED
    degraded_res = ActionResult(
        status=ActionStatus.DEGRADED,
        verified=False,
        action="youtube.open",
        message="YouTube open verify nahi ho paya.",
    )
    with patch("backend.core.safety.is_live_browser_automation_allowed", return_value=True), \
         patch.object(youtube_controller, "open", return_value=degraded_res), \
         patch.object(youtube_adapter, "observe_browser_state", return_value={"browser_running": True, "is_youtube": True}):
        res = youtube_adapter.open()
        assert res["status"] == "DEGRADED"
        assert res["verified"] is False
        assert res["status"] != "LIVE_VERIFIED"

    # 2. Controller execute_canonical returns BROKEN -> Adapter must preserve BROKEN
    broken_res = ActionResult(
        status=ActionStatus.BROKEN,
        verified=False,
        action="youtube.pause",
        message="DOM error",
    )
    with patch("backend.core.safety.is_live_browser_automation_allowed", return_value=True), \
         patch.object(youtube_controller, "execute_canonical", return_value=broken_res), \
         patch.object(youtube_adapter, "observe_browser_state", return_value={"browser_running": True, "is_youtube": True}):
        res = youtube_adapter.execute_canonical("youtube.pause")
        assert res["status"] == "BROKEN"
        assert res["verified"] is False
        assert res["status"] != "LIVE_VERIFIED"

    # 3. Controller execute_canonical returns SIMULATED -> Adapter must preserve SIMULATED
    sim_res = ActionResult(
        status=ActionStatus.SIMULATED,
        verified=False,
        action="youtube.search",
        message="Simulated run",
    )
    with patch("backend.core.safety.is_live_browser_automation_allowed", return_value=True), \
         patch.object(youtube_controller, "execute_canonical", return_value=sim_res), \
         patch.object(youtube_adapter, "observe_browser_state", return_value={"browser_running": True, "is_youtube": True}):
        res = youtube_adapter.execute_canonical("youtube.search", {"query": "carryminati"})
        assert res["status"] == "SIMULATED"
        assert res["verified"] is False
        assert res["status"] != "LIVE_VERIFIED"


def test_play_video_with_query_requires_exact_video_id():
    """Verify play_video(query=...) strictly requires actual_video_id == expected_video_id and fails on search page."""
    before = PerceptionSnapshot(browser_running=True, is_youtube=True, page_type=PageType.HOME)

    # State where only search results page is open, no video playback has occurred
    search_page_after = PerceptionSnapshot(
        browser_running=True,
        is_youtube=True,
        page_type=PageType.SEARCH_RESULTS,
        search_query="carryminati",
        url="https://www.youtube.com/results?search_query=carryminati",
        current_video=CurrentVideoInfo(video_id="UNKNOWN", title="carryminati - YouTube", url=""),
    )

    status_search, verified_search, msg_search = youtube_verifier.verify(
        action="youtube.play_video",
        arguments={"query": "carryminati", "ordinal": 1},
        actuation_result={
            "actuation_status": ActionStatus.LIVE_VERIFIED,
            "expected_video_id": "TARGET_VID_999",
            "ordinal": 1,
        },
        snapshot_before=before,
        snapshot_after=search_page_after,
    )
    assert status_search == ActionStatus.DEGRADED
    assert verified_search is False
    assert "playback verify nahi ho paya" in msg_search

    # State where the target video is actually playing and ID matches exactly
    playing_after = PerceptionSnapshot(
        browser_running=True,
        is_youtube=True,
        page_type=PageType.VIDEO,
        url="https://www.youtube.com/watch?v=TARGET_VID_999",
        current_video=CurrentVideoInfo(video_id="TARGET_VID_999", title="CarryMinati Video", url="https://www.youtube.com/watch?v=TARGET_VID_999"),
    )

    status_playing, verified_playing, msg_playing = youtube_verifier.verify(
        action="youtube.play_video",
        arguments={"query": "carryminati", "ordinal": 1},
        actuation_result={
            "actuation_status": ActionStatus.LIVE_VERIFIED,
            "expected_video_id": "TARGET_VID_999",
            "ordinal": 1,
        },
        snapshot_before=before,
        snapshot_after=playing_after,
    )
    assert status_playing == ActionStatus.LIVE_VERIFIED
    assert verified_playing is True
    assert "video number 1 chala di" in msg_playing


def test_search_rejects_window_title_substring_without_exact_query():
    """Verify search rejects LIVE_VERIFIED if query only exists as substring in window_title."""
    before = PerceptionSnapshot(browser_running=True, is_youtube=True, page_type=PageType.HOME)
    title_only_after = PerceptionSnapshot(
        browser_running=True,
        is_youtube=True,
        page_type=PageType.SEARCH_RESULTS,
        search_query="totally different query",
        url="https://www.youtube.com/results?search_query=totally+different+query",
        window_title="karan aujla - YouTube",
    )

    status, verified, _ = youtube_verifier.verify(
        action="youtube.search",
        arguments={"query": "karan aujla"},
        actuation_result={"actuation_status": ActionStatus.LIVE_VERIFIED},
        snapshot_before=before,
        snapshot_after=title_only_after,
    )
    assert status == ActionStatus.DEGRADED
    assert verified is False

