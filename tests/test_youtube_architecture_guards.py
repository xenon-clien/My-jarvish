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
