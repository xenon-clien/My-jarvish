"""Authoritative DOM extraction, normalization, and player control scripts for YouTube Runtime V3.

Implements:
- Strict visible-only card filtering (bounding box, positive dimensions, viewport intersection).
- Exact search query normalization.
- Pure DOM HTMLMediaElement execution (no Windows media keys, no master volume manipulation).
- Pure DOM UI control button execution.
"""
import re
import unicodedata
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

from backend.youtube.models import (
    BoundingBox,
    ControlsState,
    CurrentVideoInfo,
    PageType,
    PlayerState,
    VisibleVideoItem,
)


def normalize_search_query(query: Optional[str]) -> str:
    """Normalize search query strings with unicode normalization and casefolding.
    
    Rules:
    - Strip leading/trailing whitespace
    - Unicode normalize (NFKC)
    - URL-decode if encoded
    - Collapse repeated whitespace
    - Casefold (lowercase)
    """
    if not query:
        return ""
    q = str(query).strip()
    try:
        # Decode if query contains URL encoding (%20, %2B, etc.)
        if "%" in q or "+" in q:
            q = urllib.parse.unquote_plus(q)
    except Exception:
        pass
    q = unicodedata.normalize("NFKC", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q.casefold()


# Authoritative DOM Extraction JavaScript
YOUTUBE_DOM_EXTRACTOR_JS = """
(() => {
    const href = window.location.href;
    const title = document.title;
    const hLow = href.toLowerCase();

    // 1. Page Type Classification
    let pageType = "UNKNOWN";
    if (hLow.includes("/results") || hLow.includes("search_query=")) {
        pageType = "SEARCH_RESULTS";
    } else if (hLow.includes("/watch")) {
        pageType = "VIDEO";
    } else if (hLow.includes("/shorts")) {
        pageType = "SHORTS";
    } else if (hLow.includes("/channel/") || hLow.includes("/@")) {
        pageType = "CHANNEL";
    } else if (hLow.includes("youtube.com") && (window.location.pathname === "/" || window.location.pathname === "")) {
        pageType = "HOME";
    } else if (hLow.includes("youtube.com")) {
        pageType = "OTHER";
    }

    // 2. HTMLMediaElement Player State
    const video = document.querySelector('video');
    const player = {
        exists: false,
        paused: "UNKNOWN",
        current_time: "UNKNOWN",
        duration: "UNKNOWN",
        volume: "UNKNOWN",
        muted: "UNKNOWN",
        playback_rate: "UNKNOWN"
    };

    if (video) {
        player.exists = true;
        player.paused = Boolean(video.paused);
        player.current_time = Number.isFinite(video.currentTime) ? Number(video.currentTime.toFixed(1)) : "UNKNOWN";
        player.duration = Number.isFinite(video.duration) ? Number(video.duration.toFixed(1)) : "UNKNOWN";
        player.volume = Number.isFinite(video.volume) ? Number(video.volume.toFixed(2)) : "UNKNOWN";
        player.muted = Boolean(video.muted);
        player.playback_rate = Number.isFinite(video.playbackRate) ? Number(video.playbackRate.toFixed(2)) : "UNKNOWN";
    }

    // 3. Exact Search Query Extraction from Search Input or URL
    let searchQuery = "UNKNOWN";
    const searchInput = document.querySelector('input#search, ytd-searchbox input, input[name="search_query"]');
    if (searchInput && searchInput.value && searchInput.value.trim()) {
        searchQuery = searchInput.value.trim();
    } else {
        try {
            const u = new URL(href);
            const q = u.searchParams.get("search_query");
            if (q) searchQuery = q.trim();
        } catch (e) {}
    }

    // 4. UI Controls State
    const controls = {
        like_state: "UNKNOWN",
        captions: "UNKNOWN",
        fullscreen: "UNKNOWN",
        theater: "UNKNOWN",
        miniplayer: "UNKNOWN"
    };

    try {
        controls.fullscreen = Boolean(document.fullscreenElement);
        const flexy = document.querySelector('ytd-watch-flexy');
        if (flexy) {
            controls.theater = flexy.hasAttribute('theater') || flexy.hasAttribute('theater-requested_');
        }
        controls.miniplayer = Boolean(document.querySelector('ytd-miniplayer, .ytp-player-minimized'));

        const ccBtn = document.querySelector('.ytp-subtitles-button');
        if (ccBtn) {
            controls.captions = ccBtn.getAttribute('aria-pressed') === 'true';
        }

        const likeBtns = Array.from(document.querySelectorAll('like-button-view-model button, ytd-like-button-renderer button, button[aria-label*="like" i]'));
        for (const b of likeBtns) {
            const label = (b.getAttribute('aria-label') || '').toLowerCase();
            const pressed = b.getAttribute('aria-pressed');
            if (label.includes('like') && !label.includes('dislike')) {
                if (pressed === 'true') controls.like_state = true;
                else if (pressed === 'false') controls.like_state = false;
                break;
            }
        }
    } catch (e) {}

    // 5. Strict Visible Standard Video Cards Discovery (Phase 7)
    const rawVideos = [];
    const videoRenderers = Array.from(document.querySelectorAll('ytd-video-renderer, ytd-rich-item-renderer, ytd-grid-video-renderer'));
    const seenVideoIds = new Set();

    for (const card of videoRenderers) {
        // Exclude promoted/ads
        if (card.querySelector('ytd-ad-slot-renderer, [id*="ad-badge"], .ytd-badge-supported-renderer')) {
            const badgeText = card.textContent || '';
            if (badgeText.includes('Sponsored') || badgeText.includes('Ad')) continue;
        }

        // Exclude shorts rows/shelves from standard video candidates
        if (card.closest('ytd-rich-shelf-renderer[is-shorts], ytd-reel-shelf-renderer') || card.querySelector('a[href*="/shorts/"]')) {
            continue;
        }

        // Viewport and Bounding Box Visibility Check (Must intersect viewport with positive dimensions)
        const rect = card.getBoundingClientRect();
        const isVisible = rect.width > 40 && rect.height > 40 &&
                          rect.top < window.innerHeight && rect.bottom > 0 &&
                          rect.left < window.innerWidth && rect.right > 0;
        if (!isVisible) continue;

        // Find primary video link
        const titleAnchor = card.querySelector('a#video-title, a#thumbnail[href*="/watch?v="], a.yt-simple-endpoint[href*="/watch?v="]');
        if (!titleAnchor) continue;

        const linkHref = titleAnchor.getAttribute('href') || '';
        const match = linkHref.match(/[?&]v=([a-zA-Z0-9_-]{11})/);
        if (!match) continue;

        const videoId = match[1];
        if (seenVideoIds.has(videoId)) continue;
        seenVideoIds.add(videoId);

        let titleText = (titleAnchor.getAttribute('title') || titleAnchor.getAttribute('aria-label') || titleAnchor.textContent || '').trim();
        titleText = titleText.replace(/\\s+by\\s+.*$/i, '').trim();

        rawVideos.push({
            video_id: videoId,
            title: titleText || "YouTube Video",
            url: "https://www.youtube.com/watch?v=" + videoId,
            is_short: false,
            visible: true,
            x: Math.round(rect.x),
            y: Math.round(rect.y),
            width: Math.round(rect.width),
            height: Math.round(rect.height)
        });
    }

    // 6. Strict Visible Shorts Discovery
    const rawShorts = [];
    const shortsAnchors = Array.from(document.querySelectorAll('a[href*="/shorts/"]'));
    const seenShortIds = new Set();

    for (const a of shortsAnchors) {
        const h = a.getAttribute('href') || '';
        const m = h.match(/\\/shorts\\/([a-zA-Z0-9_-]{11})/);
        if (!m) continue;
        const sid = m[1];
        if (seenShortIds.has(sid)) continue;

        const r = a.getBoundingClientRect();
        const isVis = r.width > 20 && r.height > 20 &&
                      r.top < window.innerHeight && r.bottom > 0 &&
                      r.left < window.innerWidth && r.right > 0;
        if (!isVis) continue;
        seenShortIds.add(sid);

        let sTitle = (a.getAttribute('title') || a.getAttribute('aria-label') || a.textContent || '').trim();

        rawShorts.push({
            video_id: sid,
            title: sTitle || "YouTube Short",
            url: "https://www.youtube.com/shorts/" + sid,
            is_short: true,
            visible: true,
            x: Math.round(r.x),
            y: Math.round(r.y),
            width: Math.round(r.width),
            height: Math.round(r.height)
        });
    }

    return {
        url: href,
        title: title,
        search_query: searchQuery,
        page_type: pageType,
        player: player,
        controls: controls,
        raw_videos: rawVideos,
        raw_shorts: rawShorts
    };
})()
"""


def parse_dom_extraction_result(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Parse raw JS evaluation result into typed models with strict 1-based ordinal assignment."""
    if not data or not isinstance(data, dict):
        return {
            "page_type": PageType.UNKNOWN,
            "search_query": "UNKNOWN",
            "current_video": CurrentVideoInfo(),
            "player": PlayerState(),
            "controls": ControlsState(),
            "visible_videos": [],
            "visible_shorts": [],
        }

    url = data.get("url") or ""
    u_low = url.lower()

    # Determine Page Type
    raw_pt = data.get("page_type")
    if raw_pt and str(raw_pt).upper() in PageType.__members__:
        page_type = PageType[str(raw_pt).upper()]
    elif "/results" in u_low or "search_query=" in u_low:
        page_type = PageType.SEARCH_RESULTS
    elif "/watch" in u_low:
        page_type = PageType.VIDEO
    elif "/shorts" in u_low:
        page_type = PageType.SHORTS
    elif "/channel/" in u_low or "/@" in u_low:
        page_type = PageType.CHANNEL
    elif "youtube.com" in u_low:
        page_type = PageType.HOME
    else:
        page_type = PageType.OTHER

    # Current Video Extraction
    current_video = CurrentVideoInfo(url=url)
    if page_type == PageType.VIDEO:
        m = re.search(r"[?&]v=([a-zA-Z0-9_-]{11})", url)
        if m:
            current_video.video_id = m.group(1)
            raw_title = data.get("title") or ""
            current_video.title = re.sub(r"\s*-\s*youtube.*$", "", raw_title, flags=re.IGNORECASE).strip()
            current_video.is_short = False
    elif page_type == PageType.SHORTS:
        m = re.search(r"/shorts/([a-zA-Z0-9_-]{11})", url)
        if m:
            current_video.video_id = m.group(1)
            raw_title = data.get("title") or ""
            current_video.title = re.sub(r"\s*-\s*youtube.*$", "", raw_title, flags=re.IGNORECASE).strip()
            current_video.is_short = True

    # Player State
    raw_player = data.get("player") or {}
    player = PlayerState(
        exists=bool(raw_player.get("exists")),
        paused=raw_player.get("paused", "UNKNOWN"),
        current_time=raw_player.get("current_time", "UNKNOWN"),
        duration=raw_player.get("duration", "UNKNOWN"),
        volume=raw_player.get("volume", "UNKNOWN"),
        muted=raw_player.get("muted", "UNKNOWN"),
        playback_rate=raw_player.get("playback_rate", "UNKNOWN"),
    )

    # Controls State
    raw_ctrls = data.get("controls") or {}
    controls = ControlsState(
        like_state=raw_ctrls.get("like_state", "UNKNOWN"),
        captions=raw_ctrls.get("captions", "UNKNOWN"),
        fullscreen=raw_ctrls.get("fullscreen", "UNKNOWN"),
        theater=raw_ctrls.get("theater", "UNKNOWN"),
        miniplayer=raw_ctrls.get("miniplayer", "UNKNOWN"),
    )

    # Visible Standard Videos (Phase 7: strictly visible-only, sorted top -> bottom, then left -> right)
    raw_videos = data.get("raw_videos") or []
    visible_videos: List[VisibleVideoItem] = []

    # Sort strictly by rendered coordinate (y // 60 for row clustering, then x)
    raw_videos.sort(key=lambda item: (item.get("y", 0) // 60, item.get("x", 0)))

    for idx, rv in enumerate(raw_videos, start=1):
        visible_videos.append(
            VisibleVideoItem(
                ordinal=idx,
                video_id=rv["video_id"],
                title=rv.get("title", f"Video {idx}"),
                url=rv.get("url", f"https://www.youtube.com/watch?v={rv['video_id']}"),
                is_short=False,
                visible=True,
                bounding_box=BoundingBox(
                    x=rv.get("x", 0),
                    y=rv.get("y", 0),
                    width=rv.get("width", 0),
                    height=rv.get("height", 0),
                ),
                source="DOM",
            )
        )

    # Visible Shorts (Phase 7: strictly visible-only, sorted top -> bottom, then left -> right)
    raw_shorts = data.get("raw_shorts") or []
    visible_shorts: List[VisibleVideoItem] = []

    raw_shorts.sort(key=lambda item: (item.get("y", 0) // 60, item.get("x", 0)))

    for idx, rs in enumerate(raw_shorts, start=1):
        visible_shorts.append(
            VisibleVideoItem(
                ordinal=idx,
                video_id=rs["video_id"],
                title=rs.get("title", f"Short {idx}"),
                url=rs.get("url", f"https://www.youtube.com/shorts/{rs['video_id']}"),
                is_short=True,
                visible=True,
                bounding_box=BoundingBox(
                    x=rs.get("x", 0),
                    y=rs.get("y", 0),
                    width=rs.get("width", 0),
                    height=rs.get("height", 0),
                ),
                source="DOM",
            )
        )

    return {
        "page_type": page_type,
        "search_query": data.get("search_query", "UNKNOWN"),
        "current_video": current_video,
        "player": player,
        "controls": controls,
        "visible_videos": visible_videos,
        "visible_shorts": visible_shorts,
    }


# ── DOM Actuation Scripts (Phase 14 & 15 Pure DOM Controls) ─────────────────

DOM_MEDIA_PAUSE_SCRIPT = """
(() => {
    const v = document.querySelector('video');
    if (v) {
        v.pause();
        return true;
    }
    return false;
})()
"""

DOM_MEDIA_PLAY_SCRIPT = """
(() => {
    const v = document.querySelector('video');
    if (v) {
        v.play();
        return true;
    }
    return false;
})()
"""

def get_dom_seek_script(seconds: float) -> str:
    return f"""
    (() => {{
        const v = document.querySelector('video');
        if (v && Number.isFinite({seconds})) {{
            v.currentTime = {seconds};
            return true;
        }}
        return false;
    }})()
    """

def get_dom_volume_script(volume_level: float) -> str:
    # Volume 0.0 to 1.0
    vol = max(0.0, min(1.0, float(volume_level)))
    return f"""
    (() => {{
        const v = document.querySelector('video');
        if (v) {{
            v.volume = {vol};
            v.muted = false;
            return true;
        }}
        return false;
    }})()
    """

def get_dom_mute_script(muted: bool) -> str:
    val = "true" if muted else "false"
    return f"""
    (() => {{
        const v = document.querySelector('video');
        if (v) {{
            v.muted = {val};
            return true;
        }}
        return false;
    }})()
    """

def get_dom_playback_rate_script(rate: float) -> str:
    r = max(0.25, min(3.0, float(rate)))
    return f"""
    (() => {{
        const v = document.querySelector('video');
        if (v) {{
            v.playbackRate = {r};
            return true;
        }}
        return false;
    }})()
    """

DOM_MEDIA_REPLAY_SCRIPT = """
(() => {
    const v = document.querySelector('video');
    if (v) {
        v.currentTime = 0;
        v.play();
        return true;
    }
    return false;
})()
"""

def get_dom_set_captions_script(enabled: bool) -> str:
    target_str = "true" if enabled else "false"
    return f"""
    (() => {{
        const ccBtn = document.querySelector('.ytp-subtitles-button');
        if (ccBtn) {{
            const isPressed = ccBtn.getAttribute('aria-pressed') === 'true';
            if (isPressed !== {target_str}) {{
                ccBtn.click();
                return true;
            }}
            return true;
        }}
        return false;
    }})()
    """

def get_dom_set_fullscreen_script(enabled: bool) -> str:
    target_str = "true" if enabled else "false"
    return f"""
    (() => {{
        const isFs = Boolean(document.fullscreenElement);
        if (isFs !== {target_str}) {{
            const fsBtn = document.querySelector('.ytp-fullscreen-button');
            if (fsBtn) {{
                fsBtn.click();
                return true;
            }}
        }}
        return isFs === {target_str};
    }})()
    """

def get_dom_set_theater_script(enabled: bool) -> str:
    target_str = "true" if enabled else "false"
    return f"""
    (() => {{
        const flexy = document.querySelector('ytd-watch-flexy');
        const isTheater = flexy ? (flexy.hasAttribute('theater') || flexy.hasAttribute('theater-requested_')) : false;
        if (isTheater !== {target_str}) {{
            const btn = document.querySelector('.ytp-size-button');
            if (btn) {{
                btn.click();
                return true;
            }}
        }}
        return isTheater === {target_str};
    }})()
    """

def get_dom_set_miniplayer_script(enabled: bool) -> str:
    target_str = "true" if enabled else "false"
    return f"""
    (() => {{
        const isMini = Boolean(document.querySelector('ytd-miniplayer, .ytp-player-minimized'));
        if (isMini !== {target_str}) {{
            const btn = document.querySelector('.ytp-miniplayer-button');
            if (btn) {{
                btn.click();
                return true;
            }}
        }}
        return isMini === {target_str};
    }})()
    """

def get_dom_set_like_script(enabled: bool) -> str:
    target_str = "true" if enabled else "false"
    return f"""
    (() => {{
        const likeBtns = Array.from(document.querySelectorAll('like-button-view-model button, ytd-like-button-renderer button, button[aria-label*="like" i]'));
        for (const b of likeBtns) {{
            const label = (b.getAttribute('aria-label') || '').toLowerCase();
            const pressed = b.getAttribute('aria-pressed');
            if (label.includes('like') && !label.includes('dislike')) {{
                const isLiked = (pressed === 'true');
                if (isLiked !== {target_str}) {{
                    b.click();
                    return true;
                }}
                return true;
            }}
        }}
        return false;
    }})()
    """

def get_dom_card_click_script(video_id: str) -> str:
    """Click genuine video card anchor matching video ID in DOM without mouse movement."""
    return f"""
    (() => {{
        const vid = "{video_id}";
        const anchor = document.querySelector(`a#video-title[href*="${{vid}}"], a#thumbnail[href*="${{vid}}"], a.yt-simple-endpoint[href*="${{vid}}"]`);
        if (anchor) {{
            anchor.click();
            return true;
        }}
        return false;
    }})()
    """

def get_dom_scroll_script(delta_y: int) -> str:
    return f"window.scrollBy({{top: {int(delta_y)}, behavior: 'smooth'}});"
