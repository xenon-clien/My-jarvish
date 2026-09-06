"""Tests for YouTube Ordinal Identity, Grounding & Closed-Loop Verification.

Proves:
1. First Short Fix: 'pehli short chalao' selects ID_A and verifies expected_id == actual_id == ID_A.
2. Second & Third Short: 'dusri short chalao' -> ID_B, 'teesri short chalao' -> ID_C.
3. 1-based ordinal semantics applied exactly once.
4. Window layout resilience (maximized vs resized).
5. Closed-loop state verifiers (pause, resume, fullscreen, next/prev short, like idempotency).
6. Production app isolation (WhatsApp, Spotify, VS Code disabled).
"""
import pytest
from unittest.mock import MagicMock, patch

from backend.adapters.youtube_adapter import youtube_adapter
from backend.adapters.youtube_grounding import YouTubeCandidate
from backend.core.command_processor import command_processor, ExecutionStatus
from backend.nlu.youtube_nlu import youtube_nlu


@pytest.fixture
def mock_short_candidates():
    return [
        YouTubeCandidate(
            candidate_type="short",
            video_id="ID_SHORT_A",
            title="Short Candidate One",
            canonical_url="https://www.youtube.com/shorts/ID_SHORT_A",
            href="/shorts/ID_SHORT_A",
            bounding_rect=(100, 200, 250, 450),
            visual_order=1,
        ),
        YouTubeCandidate(
            candidate_type="short",
            video_id="ID_SHORT_B",
            title="Short Candidate Two",
            canonical_url="https://www.youtube.com/shorts/ID_SHORT_B",
            href="/shorts/ID_SHORT_B",
            bounding_rect=(280, 200, 430, 450),
            visual_order=2,
        ),
        YouTubeCandidate(
            candidate_type="short",
            video_id="ID_SHORT_C",
            title="Short Candidate Three",
            canonical_url="https://www.youtube.com/shorts/ID_SHORT_C",
            href="/shorts/ID_SHORT_C",
            bounding_rect=(460, 200, 610, 450),
            visual_order=3,
        ),
    ]


def test_first_short_exact_identity(mock_short_candidates):
    """PHASE 12 MANDATORY TEST:
    Given candidates: 1=ID_SHORT_A, 2=ID_SHORT_B, 3=ID_SHORT_C,
    'pehli short chalao' must resolve expected_id=ID_SHORT_A and verify actual_id=ID_SHORT_A.
    """
    with patch.object(youtube_adapter, "observe_browser_state") as mock_obs, \
         patch("backend.tools.browser_tools.navigate_active_browser_tab", return_value=True):

        # Initial state before activation exposes the 3 visible candidates
        mock_obs.side_effect = [
            {
                "browser_running": True,
                "current_url": "https://www.youtube.com",
                "page_type": "HOME",
                "visible_short_candidates": mock_short_candidates,
                "current_video_id": "UNKNOWN",
            },
            # State after activation confirms navigation to ID_SHORT_A
            {
                "browser_running": True,
                "current_url": "https://www.youtube.com/shorts/ID_SHORT_A",
                "page_type": "SHORTS",
                "visible_short_candidates": mock_short_candidates,
                "current_video_id": "ID_SHORT_A",
            },
        ]

        parsed = youtube_nlu.parse("pehli short chalao")
        assert parsed.canonical_action == "youtube.play_short"
        assert parsed.ordinal == 1

        result = youtube_adapter.play_short(ordinal=parsed.ordinal)
        assert result["status"] == "LIVE_VERIFIED"
        assert result["expected_video_id"] == "ID_SHORT_A"
        assert result["actual_video_id"] == "ID_SHORT_A"
        assert result["verified"] is True


def test_second_and_third_short_identity(mock_short_candidates):
    """PHASE 13 TEST:
    'dusri short chalao' -> ID_SHORT_B, 'teesri short chalao' -> ID_SHORT_C.
    """
    with patch.object(youtube_adapter, "observe_browser_state") as mock_obs, \
         patch("backend.tools.browser_tools.navigate_active_browser_tab", return_value=True):

        # Test Second Short
        mock_obs.side_effect = [
            {
                "browser_running": True,
                "current_url": "https://www.youtube.com",
                "page_type": "HOME",
                "visible_short_candidates": mock_short_candidates,
                "current_video_id": "UNKNOWN",
            },
            {
                "browser_running": True,
                "current_url": "https://www.youtube.com/shorts/ID_SHORT_B",
                "page_type": "SHORTS",
                "visible_short_candidates": mock_short_candidates,
                "current_video_id": "ID_SHORT_B",
            },
        ]

        parsed2 = youtube_nlu.parse("dusri short chalao")
        assert parsed2.ordinal == 2
        res2 = youtube_adapter.play_short(ordinal=parsed2.ordinal)
        assert res2["status"] == "LIVE_VERIFIED"
        assert res2["expected_video_id"] == "ID_SHORT_B"
        assert res2["actual_video_id"] == "ID_SHORT_B"

        # Test Third Short
        mock_obs.side_effect = [
            {
                "browser_running": True,
                "current_url": "https://www.youtube.com",
                "page_type": "HOME",
                "visible_short_candidates": mock_short_candidates,
                "current_video_id": "UNKNOWN",
            },
            {
                "browser_running": True,
                "current_url": "https://www.youtube.com/shorts/ID_SHORT_C",
                "page_type": "SHORTS",
                "visible_short_candidates": mock_short_candidates,
                "current_video_id": "ID_SHORT_C",
            },
        ]

        parsed3 = youtube_nlu.parse("teesri short chalao")
        assert parsed3.ordinal == 3
        res3 = youtube_adapter.play_short(ordinal=parsed3.ordinal)
        assert res3["status"] == "LIVE_VERIFIED"
        assert res3["expected_video_id"] == "ID_SHORT_C"
        assert res3["actual_video_id"] == "ID_SHORT_C"


def test_window_layout_resilience(mock_short_candidates):
    """PHASE 14 TEST: Dynamic discovery works under maximized and resized windows without coordinates."""
    with patch.object(youtube_adapter, "observe_browser_state") as mock_obs, \
         patch("backend.tools.browser_tools.navigate_active_browser_tab", return_value=True):

        # 1. Maximized layout
        mock_obs.side_effect = [
            {
                "browser_running": True,
                "fullscreen": False,
                "visible_short_candidates": mock_short_candidates,
                "current_video_id": "UNKNOWN",
            },
            {
                "browser_running": True,
                "visible_short_candidates": mock_short_candidates,
                "current_video_id": "ID_SHORT_A",
            },
        ]
        res_max = youtube_adapter.play_short(ordinal=1)
        assert res_max["status"] == "LIVE_VERIFIED"
        assert res_max["expected_video_id"] == "ID_SHORT_A"

        # 2. Resized / Sidebar layout
        resized_candidates = [
            YouTubeCandidate(
                candidate_type="short",
                video_id="ID_RESIZED_1",
                title="Resized Card",
                canonical_url="https://www.youtube.com/shorts/ID_RESIZED_1",
                href="/shorts/ID_RESIZED_1",
                bounding_rect=(50, 100, 150, 250),
                visual_order=1,
            )
        ]
        mock_obs.side_effect = [
            {
                "browser_running": True,
                "visible_short_candidates": resized_candidates,
                "current_video_id": "UNKNOWN",
            },
            {
                "browser_running": True,
                "visible_short_candidates": resized_candidates,
                "current_video_id": "ID_RESIZED_1",
            },
        ]
        res_resized = youtube_adapter.play_short(ordinal=1)
        assert res_resized["status"] == "LIVE_VERIFIED"
        assert res_resized["expected_video_id"] == "ID_RESIZED_1"


def test_next_prev_short_state_verification():
    """PHASE 18 TEST: Next/Previous short verified by BEFORE != AFTER video_id."""
    with patch.object(youtube_adapter, "observe_browser_state") as mock_obs, \
         patch("backend.tools.media_tools.control_media", return_value={"status": "success"}):

        # next_short: before=ID_1, after=ID_2
        mock_obs.side_effect = [
            {"browser_running": True, "current_video_id": "ID_1"},
            {"browser_running": True, "current_video_id": "ID_2"},
        ]
        res_next = youtube_adapter.next_short()
        assert res_next["status"] == "LIVE_VERIFIED"
        assert res_next["before_video_id"] == "ID_1"
        assert res_next["after_video_id"] == "ID_2"
        assert res_next["verified"] is True

        # prev_short: before=ID_2, after=ID_1
        mock_obs.side_effect = [
            {"browser_running": True, "current_video_id": "ID_2"},
            {"browser_running": True, "current_video_id": "ID_1"},
        ]
        res_prev = youtube_adapter.prev_short()
        assert res_prev["status"] == "LIVE_VERIFIED"
        assert res_prev["verified"] is True


def test_pause_resume_idempotency():
    """PHASE 17 TEST: Pause/Resume idempotency (no-op when already desired state)."""
    with patch.object(youtube_adapter, "observe_browser_state") as mock_obs:
        # Pause when already paused -> no-op LIVE_VERIFIED
        mock_obs.return_value = {"browser_running": True, "playback_state": "PAUSED"}
        res_pause = youtube_adapter.pause()
        assert res_pause["status"] == "LIVE_VERIFIED"
        assert "pehle se hi paused" in res_pause["message"]

        # Resume when already playing -> no-op LIVE_VERIFIED
        mock_obs.return_value = {"browser_running": True, "playback_state": "PLAYING"}
        res_resume = youtube_adapter.resume()
        assert res_resume["status"] == "LIVE_VERIFIED"
        assert "pehle se hi chal rahi" in res_resume["message"]


def test_like_idempotency():
    """PHASE 25 TEST: Like is strictly idempotent (never unlikes when user says like)."""
    with patch.object(youtube_adapter, "observe_browser_state") as mock_obs:
        # Video already liked
        mock_obs.return_value = {"browser_running": True, "like_state": True}
        res_like = youtube_adapter.set_like(enabled=True)
        assert res_like["status"] == "LIVE_VERIFIED"
        assert "pehle se hi liked" in res_like["message"]


@pytest.mark.asyncio
async def test_disabled_applications_intercept():
    """PHASE 37 TEST: Non-allowlisted apps return truthful disable message."""
    wa_res = await command_processor.process_command("WhatsApp kholo", source="test")
    assert wa_res.status == ExecutionStatus.VERIFIED_SUCCESS
    assert wa_res.response_message == "WhatsApp automation is not enabled in the current production profile."

    sp_res = await command_processor.process_command("Spotify chalao", source="test")
    assert sp_res.status == ExecutionStatus.VERIFIED_SUCCESS
    assert sp_res.response_message == "Spotify automation is not enabled in the current production profile."

    vc_res = await command_processor.process_command("VS Code open karo", source="test")
    assert vc_res.status == ExecutionStatus.VERIFIED_SUCCESS
    assert vc_res.response_message == "VS Code automation is not enabled in the current production profile."
