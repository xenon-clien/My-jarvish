"""DOM-based Extraction Scripts for YouTube Web Perception.

Executes direct JavaScript evaluation inside the live YouTube page to extract
rendered video cards, exact video IDs, viewport visibility, bounding boxes,
player playback metrics, and UI controls.
"""
from typing import Any, Dict, List, Optional
import urllib.parse
import re

from backend.perception.perception_types import (
    BoundingBox,
    ControlsState,
    CurrentVideoInfo,
    PageType,
    PlayerState,
    VisibleVideoItem,
)


YOUTUBE_DOM_EXTRACTOR_JS = """
() => {
    // 1. URL and Page Context
    const href = window.location.href || "";
    const title = document.title || "";

    // 2. Video Player Evaluation
    const video = document.querySelector('video');
    let player = {
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

    // 3. Search Query Extraction from Search Input or URL
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

    // 4. Controls State
    let controls = {
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

        // Like button inspection
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

    // 5. Standard Video Cards Discovery (Search Results and Home Feed)
    const rawVideos = [];
    const videoRenderers = Array.from(document.querySelectorAll('ytd-video-renderer, ytd-rich-item-renderer, ytd-grid-video-renderer'));

    for (const card of videoRenderers) {
        // Exclude promoted/ads
        if (card.querySelector('ytd-ad-slot-renderer, [id*="ad-badge"], .ytd-badge-supported-renderer')) {
            const badgeText = card.textContent || '';
            if (badgeText.includes('Sponsored') || badgeText.includes('Ad')) continue;
        }

        // Find primary video link
        const titleAnchor = card.querySelector('a#video-title, a#thumbnail[href*="/watch?v="], a.yt-simple-endpoint[href*="/watch?v="]');
        if (!titleAnchor) continue;

        const linkHref = titleAnchor.getAttribute('href') || '';
        const match = linkHref.match(/[?&]v=([a-zA-Z0-9_-]{11})/);
        if (!match) continue;

        const videoId = match[1];
        let titleText = (titleAnchor.getAttribute('title') || titleAnchor.getAttribute('aria-label') || titleAnchor.textContent || '').trim();
        // Remove trailing timestamps or badges from title
        titleText = titleText.replace(/\\s+by\\s+.*$/i, '').trim();

        // Viewport and Bounding Box
        const rect = card.getBoundingClientRect();
        const isVisible = rect.width > 40 && rect.height > 40 && rect.bottom > 0 && rect.top < window.innerHeight;

        rawVideos.push({
            video_id: videoId,
            title: titleText || "YouTube Video",
            url: "https://www.youtube.com/watch?v=" + videoId,
            is_short: false,
            visible: isVisible,
            x: Math.round(rect.x),
            y: Math.round(rect.y),
            width: Math.round(rect.width),
            height: Math.round(rect.height)
        });
    }

    // 6. Shorts Discovery
    const rawShorts = [];
    const shortsAnchors = Array.from(document.querySelectorAll('a[href*="/shorts/"]'));
    const seenShortIds = new Set();

    for (const a of shortsAnchors) {
        const h = a.getAttribute('href') || '';
        const m = h.match(/\\/shorts\\/([a-zA-Z0-9_-]{11})/);
        if (!m) continue;
        const sid = m[1];
        if (seenShortIds.has(sid)) continue;
        seenShortIds.add(sid);

        const r = a.getBoundingClientRect();
        const isVis = r.width > 20 && r.height > 20 && r.bottom > 0 && r.top < window.innerHeight;
        let sTitle = (a.getAttribute('title') || a.getAttribute('aria-label') || a.textContent || '').trim();

        rawShorts.push({
            video_id: sid,
            title: sTitle || "YouTube Short",
            url: "https://www.youtube.com/shorts/" + sid,
            is_short: true,
            visible: isVis,
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
        player: player,
        controls: controls,
        raw_videos: rawVideos,
        raw_shorts: rawShorts
    };
}
"""


def parse_dom_extraction_result(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Parse and normalize raw JS evaluation output into typed domain models."""
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

    # Visible Standard Videos: Sort by top coordinate and assign strict 1-based ordinals
    raw_videos = data.get("raw_videos") or data.get("items") or []
    visible_videos: List[VisibleVideoItem] = []
    seen_ids = set()

    # Filter only genuine cards, deduplicate, and sort top -> bottom
    filtered_videos = []
    for rv in raw_videos:
        if rv.get("is_ad"):
            continue
        vid = rv.get("video_id")
        if not vid or vid in seen_ids:
            continue
        # Never accept synthetic/fake candidate strings
        if vid.startswith("cand_") or vid.startswith("VID_SIM_"):
            continue
        seen_ids.add(vid)
        filtered_videos.append(rv)

    # Sort rendered top position (y coordinate), secondary by x
    def get_pos(item):
        box = item.get("bounding_box") or {}
        y = item.get("y", box.get("y", 0))
        x = item.get("x", box.get("x", 0))
        return (y, x)

    filtered_videos.sort(key=get_pos)

    for idx, fv in enumerate(filtered_videos, start=1):
        box = fv.get("bounding_box") or {}
        visible_videos.append(
            VisibleVideoItem(
                ordinal=idx,
                video_id=fv["video_id"],
                title=fv.get("title", f"Video {idx}"),
                url=fv.get("url", f"https://www.youtube.com/watch?v={fv['video_id']}"),
                is_short=False,
                visible=bool(fv.get("visible", True)),
                bounding_box=BoundingBox(
                    x=fv.get("x", box.get("x", 0)),
                    y=fv.get("y", box.get("y", 0)),
                    width=fv.get("width", box.get("width", 0)),
                    height=fv.get("height", box.get("height", 0)),
                ),
                source="DOM",
            )
        )

    # Visible Shorts: Deduplicate and sort
    raw_shorts = data.get("raw_shorts") or []
    visible_shorts: List[VisibleVideoItem] = []
    seen_sids = set()
    filtered_shorts = []
    for rs in raw_shorts:
        sid = rs.get("video_id")
        if not sid or sid in seen_sids:
            continue
        seen_sids.add(sid)
        filtered_shorts.append(rs)

    filtered_shorts.sort(key=lambda item: (item.get("y", 0), item.get("x", 0)))

    for idx, fs in enumerate(filtered_shorts, start=1):
        visible_shorts.append(
            VisibleVideoItem(
                ordinal=idx,
                video_id=fs["video_id"],
                title=fs.get("title", f"Short {idx}"),
                url=fs.get("url", f"https://www.youtube.com/shorts/{fs['video_id']}"),
                is_short=True,
                visible=bool(fs.get("visible", True)),
                bounding_box=BoundingBox(
                    x=fs.get("x", 0),
                    y=fs.get("y", 0),
                    width=fs.get("width", 0),
                    height=fs.get("height", 0),
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
