"""Comprehensive test suite for JARVIS EYES V1 — Real Screen + Browser Perception Foundation.

Tests:
1. Query extraction strips UI vocabulary ("search bar mein search karo X" -> "X").
2. "play first" resolves to pure ordinal selection (ordinal=1, query="") and never searches "first".
3. "youtube.observe" intent recognition for diagnostic questions.
4. DOM extraction parsing: visual top-to-bottom sorting, deduplication, 1-based ordinals.
5. Perception fusion truth hierarchy (CDP/DOM > URL > Title > UIA > Vision).
6. Same-tab reuse: searches and ordinal navigation reuse active tab via CDP without duplicate windows.
7. Closed-loop identity verification: actual_id == expected_id required for LIVE_VERIFIED.
8. Rejection of fake video IDs and generic browser presence.
9. Zero physical hijacking: physical mouse/keyboard disabled by default.
10. Diagnostic summary formatting for voice and UI.
11. Command processor integration for perception inquiries.
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.nlu.youtube_nlu import youtube_nlu
from backend.adapters.youtube_adapter import youtube_adapter
from backend.core.command_processor import command_processor, ExecutionStatus
from backend.core.safety import is_physical_automation_allowed
from backend.perception.perception_types import (
    PageType,
    VisibleVideoItem,
    YouTubePerceptionSnapshot,
    YouTubeState,
    BrowserTabInfo,
    PlayerState,
    CurrentVideoInfo,
)
from backend.perception.browser_dom import parse_dom_extraction_result
from backend.perception.perception_fusion import perception_fusion
from backend.perception.youtube_perception import youtube_perception


# =====================================================================
# 1. Query Extraction & UI Vocabulary Stripping
# =====================================================================

def test_query_extraction_strips_search_ui_vocabulary():
    """Verify that 'search bar mein search karo X' strips 'search bar' and extracts clean query."""
    test_cases = [
        ("search bar mein search karo Karan Aujla", "karan aujla"),
        ("search bar me search karo Arijit Singh", "arijit singh"),
        ("search box mein search karo Sidhu Moosewala", "sidhu moosewala"),
        ("searchbar me search karo Diljit Dosanjh", "diljit dosanjh"),
        ("search bar me type karo Coke Studio", "coke studio"),
        ("search box me dalo Badshah", "badshah"),
        ("search bar mein chalao divine", "divine"),
    ]
    for utterance, expected_query in test_cases:
        res = youtube_nlu.parse(utterance)
        assert res.canonical_action in ["youtube.search", "youtube.open"], f"Failed action for '{utterance}'"
        assert res.arguments.get("query") == expected_query, f"Failed for '{utterance}': got '{res.arguments.get('query')}' expected '{expected_query}'"


# =====================================================================
# 2. Pure Ordinal Selection ("play first" -> ordinal=1, query="")
# =====================================================================

def test_play_first_pure_ordinal_never_searches_word_first():
    """Verify that 'play first', 'pehla chalao' etc. map to ordinal selection, NEVER query='first'."""
    test_cases = [
        ("play first", 1),
        ("first play karo", 1),
        ("play 1st", 1),
        ("pehla chalao", 1),
        ("pehli video chalao", 1),
        ("play first video", 1),
        ("pehla video play karo", 1),
        ("play second video", 2),
        ("dusri video chalao", 2),
        ("teesra chalao", 3),
        ("play third", 3),
    ]
    for utterance, expected_ordinal in test_cases:
        res = youtube_nlu.parse(utterance)
        assert res.canonical_action == "youtube.play_video", f"Failed action for '{utterance}': got {res.canonical_action}"
        assert res.ordinal == expected_ordinal, f"Failed ordinal for '{utterance}': got {res.ordinal}"
        # Query must NEVER be 'first', 'second', etc.
        query = res.arguments.get("query", "")
        assert query == "" or query is None, f"Query for '{utterance}' must be empty, but got '{query}'"


# =====================================================================
# 3. YouTube Observe Intent Recognition
# =====================================================================

def test_youtube_observe_intent_parsing():
    """Verify diagnostic perception questions map to youtube.observe."""
    test_cases = [
        ("screen pe kya dikh raha hai", "youtube.observe"),
        ("first 5 videos batao", "youtube.observe"),
        ("abhi kaunsa page open hai", "youtube.observe"),
        ("abhi kaunsi video chal rahi hai", "youtube.observe"),
        ("kya play ho raha hai", "youtube.observe"),
        ("kaunse videos dikh rahe hain", "youtube.observe"),
    ]
    for utterance, exp_act in test_cases:
        res = youtube_nlu.parse(utterance)
        assert res.canonical_action == exp_act, f"Failed canonical action for '{utterance}': got {res.canonical_action}"


# =====================================================================
# 4. DOM Extraction: Sorting, Deduplication, and Ordinals
# =====================================================================

def test_dom_extraction_parsing_sorting_and_deduplication():
    """Verify raw DOM payload is sorted top-to-bottom, deduplicated, and given 1-based ordinals."""
    raw_dom = {
        "page_type": "SEARCH_RESULTS",
        "search_query": "karan aujla",
        "current_video": {"video_id": "UNKNOWN", "title": "UNKNOWN"},
        "player": {"exists": False, "paused": "UNKNOWN"},
        "items": [
            # Item B appears lower on screen (y = 500)
            {
                "video_id": "VID_BBB",
                "title": "Karan Aujla Song 2",
                "url": "https://www.youtube.com/watch?v=VID_BBB",
                "is_short": False,
                "is_ad": False,
                "bounding_box": {"x": 100, "y": 500, "width": 400, "height": 200},
            },
            # Item A appears higher on screen (y = 100)
            {
                "video_id": "VID_AAA",
                "title": "Karan Aujla Song 1",
                "url": "https://www.youtube.com/watch?v=VID_AAA",
                "is_short": False,
                "is_ad": False,
                "bounding_box": {"x": 100, "y": 100, "width": 400, "height": 200},
            },
            # Duplicate of Item A
            {
                "video_id": "VID_AAA",
                "title": "Karan Aujla Song 1 Duplicate",
                "url": "https://www.youtube.com/watch?v=VID_AAA",
                "is_short": False,
                "is_ad": False,
                "bounding_box": {"x": 100, "y": 700, "width": 400, "height": 200},
            },
            # Ad item (must be filtered out)
            {
                "video_id": "VID_AD",
                "title": "Sponsored Video",
                "url": "https://www.youtube.com/watch?v=VID_AD",
                "is_short": False,
                "is_ad": True,
                "bounding_box": {"x": 100, "y": 50, "width": 400, "height": 200},
            },
        ],
    }

    parsed = parse_dom_extraction_result(raw_dom)
    assert parsed["page_type"] == "SEARCH_RESULTS"
    assert parsed["search_query"] == "karan aujla"

    videos = parsed["visible_videos"]
    # Ad and duplicate must be removed -> exactly 2 videos
    assert len(videos) == 2

    # Top-to-bottom sorting: VID_AAA (y=100) must be ordinal 1, VID_BBB (y=500) must be ordinal 2
    assert videos[0].video_id == "VID_AAA"
    assert videos[0].ordinal == 1
    assert videos[1].video_id == "VID_BBB"
    assert videos[1].ordinal == 2


# =====================================================================
# 5. Perception Fusion Hierarchy
# =====================================================================

def test_perception_fusion_hierarchy():
    """Verify CDP/DOM evidence takes precedence over window title and URL."""
    # When CDP is connected with DOM data
    dom_data = {
        "page_type": "SEARCH_RESULTS",
        "search_query": "sidhu moosewala",
        "current_video": {"video_id": "UNKNOWN", "title": "UNKNOWN", "url": "UNKNOWN", "is_short": False},
        "player": {"exists": False, "paused": "UNKNOWN", "current_time": "UNKNOWN", "duration": "UNKNOWN"},
        "visible_videos": [
            VisibleVideoItem(ordinal=1, video_id="VID_1", title="Video 1", url="https://youtube.com/watch?v=VID_1")
        ],
        "visible_shorts": [],
        "controls": {},
    }

    window_info = (12345, "YouTube - Google Chrome", "Chrome_WidgetWin_1", (0, 0, 1920, 1080))

    snap = perception_fusion.fuse(
        dom_data=dom_data,
        cdp_connected=True,
        page_id="tab_1",
        cdp_url="https://www.youtube.com/results?search_query=sidhu+moosewala",
        cdp_title="sidhu moosewala - YouTube",
        window_info=window_info,
        omnibox_url=None,
    )

    assert snap.browser.connected is True
    assert snap.youtube.is_youtube is True
    assert snap.youtube.page_type == PageType.SEARCH_RESULTS
    assert snap.youtube.search_query == "sidhu moosewala"
    assert len(snap.youtube.visible_videos) == 1
    assert snap.confidence["overall"] >= 0.95
    assert "DOM" in snap.sources


# =====================================================================
# 6. Same-Tab Reuse on Search (No Duplicate Windows)
# =====================================================================

def test_same_tab_reuse_on_search():
    """Verify searching reuses the active CDP tab without calling launch_in_google_chrome."""
    from backend.perception.browser_session import browser_session

    with patch("backend.core.safety.is_live_browser_automation_allowed", return_value=True), \
         patch.object(browser_session, "is_cdp_available", return_value=True), \
         patch.object(browser_session, "navigate_same_tab_sync", return_value=True) as mock_same_tab, \
         patch("backend.tools.browser_tools.launch_in_google_chrome") as mock_launch, \
         patch.object(youtube_adapter, "observe_browser_state", return_value={
             "browser_running": True,
             "is_youtube": True,
             "page_type": "SEARCH_RESULTS",
             "search_query": "karan aujla",
             "current_url": "https://www.youtube.com/results?search_query=karan+aujla",
             "window_title": "karan aujla - YouTube",
         }):

        res = youtube_adapter.search("karan aujla")

        assert res["status"] == "LIVE_VERIFIED"
        assert res["verified"] is True
        # Proves existing tab was navigated
        mock_same_tab.assert_called_once()
        # Proves NO duplicate process was spawned
        mock_launch.assert_not_called()


# =====================================================================
# 7. Closed-Loop Identity Verification (actual vs expected)
# =====================================================================

def test_play_video_identity_verification_success():
    """When actual_video_id matches expected_video_id, status is LIVE_VERIFIED."""
    cands = [
        VisibleVideoItem(ordinal=1, video_id="REAL_VID_1", title="Song 1", url="https://youtube.com/watch?v=REAL_VID_1"),
        VisibleVideoItem(ordinal=2, video_id="REAL_VID_2", title="Song 2", url="https://youtube.com/watch?v=REAL_VID_2"),
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
        "current_video_id": "REAL_VID_1",
        "current_url": "https://www.youtube.com/watch?v=REAL_VID_1",
        "playback_state": "PLAYING",
    }

    with patch("backend.core.safety.is_live_browser_automation_allowed", return_value=True), \
         patch("backend.tools.browser_tools.navigate_active_browser_tab", return_value=True), \
         patch.object(youtube_adapter, "observe_browser_state", side_effect=[before_obs, after_obs]):

        res = youtube_adapter.play_video(ordinal=1)

        assert res["status"] == "LIVE_VERIFIED"
        assert res["verified"] is True
        assert res["expected_video_id"] == "REAL_VID_1"
        assert res["actual_video_id"] == "REAL_VID_1"


def test_play_video_identity_verification_mismatch_degraded():
    """When actual_video_id is UNKNOWN or does not match, status is DEGRADED."""
    cands = [
        VisibleVideoItem(ordinal=1, video_id="REAL_VID_1", title="Song 1", url="https://youtube.com/watch?v=REAL_VID_1"),
    ]

    before_obs = {
        "browser_running": True,
        "is_youtube": True,
        "page_type": "SEARCH_RESULTS",
        "visible_video_candidates": cands,
        "current_video_id": "UNKNOWN",
    }
    # Video failed to load, remains on search results with UNKNOWN ID
    after_obs = {
        "browser_running": True,
        "is_youtube": True,
        "page_type": "SEARCH_RESULTS",
        "current_video_id": "UNKNOWN",
        "current_url": "https://www.youtube.com/results?search_query=test",
        "playback_state": "UNKNOWN",
    }

    with patch("backend.core.safety.is_live_browser_automation_allowed", return_value=True), \
         patch("backend.tools.browser_tools.navigate_active_browser_tab", return_value=True), \
         patch.object(youtube_adapter, "observe_browser_state", side_effect=[before_obs, after_obs]):

        res = youtube_adapter.play_video(ordinal=1)

        assert res["status"] == "DEGRADED"
        assert res["verified"] is False
        assert res["expected_video_id"] == "REAL_VID_1"
        assert res["actual_video_id"] == "UNKNOWN"


# =====================================================================
# 8. Rejection of Fake IDs and Generic Browser Presence
# =====================================================================

def test_verify_state_rejects_generic_presence_for_play_video():
    """Generic Chrome presence without playing video must NOT return LIVE_VERIFIED."""
    generic_state = {
        "browser_running": True,
        "is_youtube": True,
        "current_url": "https://www.youtube.com/",
        "window_title": "YouTube - Google Chrome",
        "page_type": "HOME",
        "current_video_id": "UNKNOWN",
        "playback_state": "UNKNOWN",
    }

    with patch.object(youtube_adapter, "observe_browser_state", return_value=generic_state):
        # Action is play_video, but current_video_id is UNKNOWN and page is HOME
        status = youtube_adapter.verify_state(
            action="youtube.play_video",
            expected_effect="VIDEO_PLAYING",
            result={"expected_video_id": "TARGET_123"},
        )
        assert status == "DEGRADED"


# =====================================================================
# 9. Zero Physical Hijacking
# =====================================================================

def test_zero_physical_hijacking_enforced(call_tracker):
    """Calling play_video with JARVIS_ALLOW_PHYSICAL_INPUT=0 must never trigger OS mouse/keybd events."""
    call_tracker.reset()
    assert is_physical_automation_allowed() is False

    with patch("backend.core.safety.is_live_browser_automation_allowed", return_value=False):
        res = youtube_adapter.play_video(ordinal=1)

    assert res["status"] in ["SIMULATED", "LIVE_AUTOMATION_DISABLED"]
    assert res.get("verified") is False
    assert call_tracker.set_cursor_pos_calls == 0
    assert call_tracker.mouse_event_calls == 0
    assert call_tracker.keybd_event_calls == 0


# =====================================================================
# 10. Diagnostic Summary Formatting
# =====================================================================

def test_diagnostic_summary_formatting():
    """Verify format_diagnostic_summary produces clean report for user inquiry."""
    snap = YouTubePerceptionSnapshot(
        browser=BrowserTabInfo(connected=True, browser_name="Chrome", hwnd=12345),
        youtube=YouTubeState(
            is_youtube=True,
            page_type=PageType.SEARCH_RESULTS,
            search_query="karan aujla",
            visible_videos=[
                VisibleVideoItem(ordinal=1, video_id="ID_1", title="Winning Speech - Karan Aujla", url="https://youtube.com/watch?v=ID_1"),
                VisibleVideoItem(ordinal=2, video_id="ID_2", title="Softly - Karan Aujla", url="https://youtube.com/watch?v=ID_2"),
            ],
            player=PlayerState(exists=False),
        ),
    )

    with patch.object(youtube_perception, "observe", return_value=snap):
        summary = youtube_perception.format_diagnostic_summary()

        assert "YouTube Search Results" in summary
        assert "Search: 'karan aujla'" in summary
        assert "1. Winning Speech - Karan Aujla" in summary
        assert "ID: ID_1" in summary
        assert "2. Softly - Karan Aujla" in summary
        assert "ID: ID_2" in summary


# =====================================================================
# 11. Command Processor Integration for youtube.observe
# =====================================================================

@pytest.mark.asyncio
async def test_command_processor_youtube_observe():
    """Verify 'screen pe kya dikh raha hai' routes to youtube.observe and returns summary."""
    mock_obs_result = {
        "status": "LIVE_VERIFIED",
        "verified": True,
        "message": "Current page: YouTube Search Results\n1. Winning Speech",
        "summary": "Current page: YouTube Search Results\n1. Winning Speech",
    }

    with patch.object(youtube_adapter, "execute_canonical", return_value=mock_obs_result):
        ctx = await command_processor.process_command("screen pe kya dikh raha hai", source="test")
        assert ctx.action == "youtube.observe"
        assert ctx.status == ExecutionStatus.VERIFIED_SUCCESS
        assert ctx.verified is True
        assert "YouTube Search Results" in ctx.response_message
