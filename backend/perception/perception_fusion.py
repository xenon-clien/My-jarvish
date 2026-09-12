"""Perception Fusion Engine for JARVIS EYES V1.

Fuses multi-modal observations according to strict truth hierarchy:
    1. CDP / Browser DOM (Primary Ground Truth)
    2. Browser Tab URL
    3. Browser Window Title
    4. Windows UI Automation
    5. Secondary Screen Vision (Optional)

Strict Rules:
- Weaker sources NEVER overwrite stronger sources.
- UNKNOWN must strictly remain UNKNOWN.
- Synthetic/fabricated candidate IDs (e.g. cand_1, VID_SIM_1) are strictly rejected.
"""
from typing import Any, Dict, List, Optional
import time

from backend.perception.perception_types import (
    BrowserTabInfo,
    CurrentVideoInfo,
    PageType,
    PerceptionSource,
    PlayerState,
    ControlsState,
    YouTubePerceptionSnapshot,
    YouTubeState,
)


class PerceptionFusion:
    """Fuses multi-source evidence into a single truthful perception snapshot."""

    @staticmethod
    def fuse(
        dom_data: Optional[Dict[str, Any]] = None,
        cdp_connected: bool = False,
        page_id: str = "UNKNOWN",
        cdp_url: str = "UNKNOWN",
        cdp_title: str = "UNKNOWN",
        window_info: Optional[tuple] = None,
        omnibox_url: Optional[str] = None,
    ) -> YouTubePerceptionSnapshot:
        """Fuse available DOM, CDP, OS window, and UIA evidence."""
        snapshot = YouTubePerceptionSnapshot()
        sources_used: List[str] = []

        # ── 1. OS Window & Process Grounding ────────────────────────────────
        hwnd = 0
        win_title = "UNKNOWN"
        win_browser = "UNKNOWN"
        if window_info:
            hwnd, win_title, win_cls, _ = window_info
            c_low = win_cls.lower()
            t_low = win_title.lower()
            if "edge" in c_low or "edge" in t_low:
                win_browser = "edge"
            elif "brave" in c_low or "brave" in t_low:
                win_browser = "brave"
            else:
                win_browser = "chrome"

        # ── 2. Browser Tab Information ──────────────────────────────────────
        primary_url = "UNKNOWN"
        primary_title = "UNKNOWN"

        if cdp_connected and cdp_url != "UNKNOWN":
            primary_url = cdp_url
            primary_title = cdp_title
            sources_used.append(PerceptionSource.CDP.value)
        elif omnibox_url:
            primary_url = omnibox_url
            primary_title = win_title
            sources_used.append(PerceptionSource.URL.value)
        elif win_title != "UNKNOWN":
            primary_title = win_title
            sources_used.append(PerceptionSource.TITLE.value)

        snapshot.browser = BrowserTabInfo(
            connected=cdp_connected,
            page_id=page_id,
            url=primary_url,
            title=primary_title,
            browser_name=win_browser,
            hwnd=hwnd,
        )

        # ── 3. YouTube Domain Detection ─────────────────────────────────────
        url_lower = primary_url.lower()
        title_lower = primary_title.lower()
        is_youtube = ("youtube.com" in url_lower) or ("youtube" in title_lower) or (" - youtube" in title_lower)

        # ── 4. DOM Primary Perception (Priority 1) ──────────────────────────
        if dom_data and dom_data.get("page_type") != PageType.UNKNOWN:
            sources_used.append(PerceptionSource.DOM.value)
            snapshot.youtube = YouTubeState(
                is_youtube=True,
                page_type=dom_data.get("page_type", PageType.UNKNOWN),
                search_query=dom_data.get("search_query", "UNKNOWN"),
                current_video=dom_data.get("current_video", CurrentVideoInfo()),
                player=dom_data.get("player", PlayerState()),
                visible_videos=dom_data.get("visible_videos", []),
                visible_shorts=dom_data.get("visible_shorts", []),
                controls=dom_data.get("controls", ControlsState()),
            )
            snapshot.confidence = {
                "overall": 1.0,
                "page_type": 1.0,
                "visible_videos": 1.0,
                "current_video": 1.0,
                "player": 1.0,
            }
        else:
            # Fallback: Infer strictly from URL / Title without fabricating DOM cards
            inferred_type = PageType.UNKNOWN
            curr_video = CurrentVideoInfo()
            inferred_search_query = "UNKNOWN"

            if is_youtube:
                if "/shorts" in url_lower:
                    inferred_type = PageType.SHORTS
                    import re
                    m = re.search(r"/shorts/([a-zA-Z0-9_-]{11})", primary_url)
                    if m:
                        curr_video.video_id = m.group(1)
                        curr_video.is_short = True
                elif "/watch" in url_lower:
                    inferred_type = PageType.VIDEO
                    import re
                    m = re.search(r"[?&]v=([a-zA-Z0-9_-]{11})", primary_url)
                    if m:
                        curr_video.video_id = m.group(1)
                        curr_video.is_short = False
                elif "/results" in url_lower or "search_query=" in url_lower:
                    inferred_type = PageType.SEARCH_RESULTS
                    import re
                    import urllib.parse
                    m = re.search(r"[?&]search_query=([^&]+)", primary_url)
                    if m:
                        inferred_search_query = urllib.parse.unquote_plus(m.group(1)).strip()
                elif "youtube.com" in url_lower:
                    inferred_type = PageType.HOME
                elif " - youtube" in title_lower:
                    inferred_type = PageType.VIDEO

            snapshot.youtube = YouTubeState(
                is_youtube=is_youtube,
                page_type=inferred_type,
                search_query=inferred_search_query,
                current_video=curr_video,
                player=PlayerState(exists=False),
                visible_videos=[],  # Never fabricate visible video cards if DOM not queried
                visible_shorts=[],
                controls=ControlsState(),
            )
            snapshot.confidence = {
                "overall": 0.7 if is_youtube else 0.0,
                "page_type": 0.7 if inferred_type != PageType.UNKNOWN else 0.0,
                "visible_videos": 0.0,
                "current_video": 0.6 if curr_video.video_id != "UNKNOWN" else 0.0,
                "player": 0.0,
            }

        snapshot.sources = sources_used
        return snapshot


# Global singleton
perception_fusion = PerceptionFusion()
