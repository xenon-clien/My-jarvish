"""High-Level YouTube Perception Coordinator for JARVIS EYES V1.

Coordinates the authoritative browser session, DOM evaluation, window observer,
and perception fusion engine. Implements freshness management and human-readable
diagnostic reporting for user perception inquiries.
"""
import time
from typing import Any, Dict, Optional

from backend.core.logger import get_logger
from backend.perception.browser_session import browser_session
from backend.perception.browser_dom import (
    YOUTUBE_DOM_EXTRACTOR_JS,
    parse_dom_extraction_result,
)
from backend.perception.window_observer import window_observer
from backend.perception.perception_fusion import perception_fusion
from backend.perception.perception_types import (
    PageType,
    YouTubePerceptionSnapshot,
)

logger = get_logger("YouTubePerception")


class YouTubePerception:
    """Master perception engine providing real eyes on the YouTube surface."""

    def __init__(self):
        self._cached_snapshot: Optional[YouTubePerceptionSnapshot] = None
        self._last_snapshot_time: float = 0.0
        self._cache_ttl: float = 1.5  # seconds

    def observe(self, force_refresh: bool = False) -> YouTubePerceptionSnapshot:
        """Capture a truthful perception snapshot of the live YouTube page."""
        now = time.time()
        if not force_refresh and self._cached_snapshot is not None:
            if (now - self._last_snapshot_time) < self._cache_ttl:
                return self._cached_snapshot

        # 1. Inspect OS-level browser window
        win_info = window_observer.get_browser_window()
        omnibox_url = None
        if win_info:
            omnibox_url = window_observer.get_omnibox_url(win_info[0])

        # 2. Inspect CDP / Browser Session
        cdp_connected = False
        page_id = "UNKNOWN"
        cdp_url = "UNKNOWN"
        cdp_title = "UNKNOWN"
        dom_data = None

        try:
            if browser_session.is_cdp_available():
                page = browser_session.execute_async_safe(browser_session.get_page())
                if page and not page.is_closed():
                    cdp_connected = True
                    cdp_url = page.url or "UNKNOWN"
                    cdp_title = browser_session.execute_async_safe(page.title()) or "UNKNOWN"
                    page_id = getattr(browser_session, "_page_id", "tab_main") or "tab_main"

                    # Execute DOM extraction script inside the YouTube tab
                    raw_dom = browser_session.execute_async_safe(page.evaluate(YOUTUBE_DOM_EXTRACTOR_JS))
                    dom_data = parse_dom_extraction_result(raw_dom)
        except Exception as exc:
            logger.debug(f"CDP perception extraction exception: {exc}")

        # 3. Fuse evidence through Truth Hierarchy
        snapshot = perception_fusion.fuse(
            dom_data=dom_data,
            cdp_connected=cdp_connected,
            page_id=page_id,
            cdp_url=cdp_url,
            cdp_title=cdp_title,
            window_info=win_info,
            omnibox_url=omnibox_url,
        )

        self._cached_snapshot = snapshot
        self._last_snapshot_time = now
        return snapshot

    def invalidate_cache(self) -> None:
        """Explicitly invalidate perception cache upon action execution."""
        self._cached_snapshot = None
        self._last_snapshot_time = 0.0

    def format_diagnostic_summary(self, max_items: int = 5) -> str:
        """Produce a human-readable diagnostic report for voice and UI."""
        snap = self.observe(force_refresh=True)
        yt = snap.youtube
        pt = yt.page_type.value if hasattr(yt.page_type, "value") else str(yt.page_type)

        lines = []
        # Page classification
        if pt == PageType.SEARCH_RESULTS.value:
            lines.append(f"Current page: YouTube Search Results")
            if yt.search_query != "UNKNOWN":
                lines.append(f"Search: '{yt.search_query}'")
        elif pt == PageType.VIDEO.value:
            lines.append(f"Current page: YouTube Video Watch Page")
            if yt.current_video.title != "UNKNOWN":
                lines.append(f"Playing: '{yt.current_video.title}' (ID: {yt.current_video.video_id})")
        elif pt == PageType.SHORTS.value:
            lines.append(f"Current page: YouTube Shorts")
            if yt.current_video.video_id != "UNKNOWN":
                lines.append(f"Active Short ID: {yt.current_video.video_id}")
        elif pt == PageType.HOME.value:
            lines.append(f"Current page: YouTube Home Feed")
        elif not snap.browser.connected and not yt.is_youtube:
            return "YouTube browser open nahi hai ya connect nahi ho pa raha."
        else:
            lines.append(f"Current page: YouTube ({pt})")

        # Visible videos listing
        if yt.visible_videos:
            lines.append(f"\nVisible standard videos (Top {min(len(yt.visible_videos), max_items)}):")
            for item in yt.visible_videos[:max_items]:
                lines.append(f"{item.ordinal}. {item.title}\n   ID: {item.video_id}")
        elif yt.visible_shorts:
            lines.append(f"\nVisible Shorts (Top {min(len(yt.visible_shorts), max_items)}):")
            for item in yt.visible_shorts[:max_items]:
                lines.append(f"{item.ordinal}. {item.title}\n   ID: {item.video_id}")
        else:
            if pt != PageType.VIDEO.value:
                lines.append("\nNo standard video cards visible in current view.")

        # Active player state
        if yt.player.exists:
            p_state = "PAUSED" if yt.player.paused else "PLAYING"
            lines.append(f"\nPlayer: {p_state} at {yt.player.current_time}s / {yt.player.duration}s")

        return "\n".join(lines)


# Global singleton
youtube_perception = YouTubePerception()
