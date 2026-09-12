"""Authoritative Perception Coordinator for YouTube Runtime V3.

Implements Phase 6, Phase 7, and Phase 8 invariants:
- Pure DOM ground truth via YouTubeBrowserSession.
- Strict visible-only video discovery (dimensions, viewport intersection, 11-char ID).
- Zero fabricated or synthetic candidate IDs (strictly rejected).
- Page generation counter and stale context protection.
- Unknown data remains strictly "UNKNOWN".
"""
import time
import uuid
from typing import Any, Dict, List, Optional

from backend.core.logger import get_logger
from backend.youtube.dom import YOUTUBE_DOM_EXTRACTOR_JS, parse_dom_extraction_result
from backend.youtube.models import (
    CurrentVideoInfo,
    PageType,
    PerceptionSnapshot,
    VisibleVideoItem,
)
from backend.youtube.session import youtube_session

logger = get_logger("YouTubePerceptionV3")


class YouTubePerception:
    """Master perception engine providing authoritative eyes on the YouTube surface."""

    def __init__(self):
        self._cached_snapshot: Optional[PerceptionSnapshot] = None
        self._last_snapshot_time: float = 0.0
        self._cache_ttl: float = 1.0  # seconds
        self._override_provider: Optional[Any] = None
        self._is_mock_active_checker: Optional[Any] = None

    def is_override_active(self) -> bool:
        """Check if perception is being overridden in test mock environment without calling provider."""
        if self._is_mock_active_checker is not None:
            try:
                return bool(self._is_mock_active_checker())
            except Exception:
                return False
        return False

    def invalidate_cache(self) -> None:
        """Explicitly invalidate perception cache upon actions or page navigation."""
        self._cached_snapshot = None
        self._last_snapshot_time = 0.0

    def observe_fresh(self, force_refresh: bool = True) -> PerceptionSnapshot:
        """Capture a truthful perception snapshot directly from the controlled browser page."""
        if self.is_override_active() and self._override_provider is not None:
            try:
                prov_res = self._override_provider()
                if prov_res is not None:
                    if isinstance(prov_res, PerceptionSnapshot):
                        return prov_res
                    elif isinstance(prov_res, dict):
                        return PerceptionSnapshot.from_dict(prov_res)
            except Exception as exc:
                logger.debug(f"Perception override provider exception: {exc}")

        now = time.time()
        if not force_refresh and self._cached_snapshot is not None:
            if (now - self._last_snapshot_time) < self._cache_ttl:
                return self._cached_snapshot

        # 1. Query Authoritative CDP Browser Session
        cdp_connected = False
        page_id = youtube_session.page_id
        generation = youtube_session.generation
        raw_dom_data = None
        cdp_url = "UNKNOWN"
        cdp_title = "UNKNOWN"

        try:
            if youtube_session.is_cdp_available():
                page = youtube_session.execute_async_safe(youtube_session.get_page())
                if page and not page.is_closed():
                    cdp_connected = True
                    cdp_url = page.url or "UNKNOWN"
                    cdp_title = youtube_session.execute_async_safe(page.title()) or "UNKNOWN"
                    page_id = getattr(youtube_session, "_page_id", "tab_main") or "tab_main"

                    # Execute authoritative DOM extraction script inside the YouTube tab
                    raw_dom_data = youtube_session.execute_async_safe(page.evaluate(YOUTUBE_DOM_EXTRACTOR_JS))
        except Exception as exc:
            logger.debug(f"CDP perception extraction exception: {exc}")

        # 2. Parse DOM extraction output
        dom_data = parse_dom_extraction_result(raw_dom_data)
        primary_url = cdp_url if cdp_url != "UNKNOWN" else (dom_data.get("current_video").url if dom_data.get("current_video") else "UNKNOWN")
        url_lower = primary_url.lower()
        title_lower = cdp_title.lower()

        is_youtube = ("youtube.com" in url_lower) or ("youtube" in title_lower) or (" - youtube" in title_lower)

        # 3. Fallback OS Window Observer (Only if CDP is not attached, without fabricating DOM cards)
        if not cdp_connected:
            from backend.perception.window_observer import window_observer
            win_info = window_observer.get_browser_window()
            if win_info:
                hwnd, win_title, _, _ = win_info
                w_low = win_title.lower()
                is_youtube = is_youtube or ("youtube" in w_low)
                cdp_title = win_title

        # 4. Construct Truthful Perception Snapshot
        snapshot_id = f"snap_{int(now * 1000)}_{uuid.uuid4().hex[:6]}"

        snapshot = PerceptionSnapshot(
            snapshot_id=snapshot_id,
            page_id=page_id,
            url=primary_url,
            page_type=dom_data.get("page_type", PageType.UNKNOWN),
            search_query=dom_data.get("search_query", "UNKNOWN"),
            generation=generation,
            timestamp=now,
            is_youtube=is_youtube,
            browser_running=cdp_connected or is_youtube,
            window_title=cdp_title,
            current_video=dom_data.get("current_video", CurrentVideoInfo()),
            player=dom_data.get("player"),
            controls=dom_data.get("controls"),
            visible_videos=dom_data.get("visible_videos", []),
            visible_shorts=dom_data.get("visible_shorts", []),
        )

        self._cached_snapshot = snapshot
        self._last_snapshot_time = now
        return snapshot


# Global singleton instance
youtube_perception = YouTubePerception()


def get_youtube_perception() -> YouTubePerception:
    """Return the global YouTubePerception singleton."""
    return youtube_perception
