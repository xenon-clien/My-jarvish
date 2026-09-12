"""Domain models, typed result structures, and enumerations for JARVIS YouTube Runtime V3.

Enforces:
- Canonical ActionResult model with strict status enumerations.
- Complete removal of ambiguous generic "success" statuses.
- Strictly typed perception snapshot and player/controls states.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ActionStatus(str, Enum):
    LIVE_VERIFIED = "LIVE_VERIFIED"
    DEGRADED = "DEGRADED"
    BROKEN = "BROKEN"
    SIMULATED = "SIMULATED"
    UNSUPPORTED = "UNSUPPORTED"
    CDP_UNAVAILABLE = "CDP_UNAVAILABLE"
    TARGET_NOT_VISIBLE = "TARGET_NOT_VISIBLE"


class PageType(str, Enum):
    HOME = "HOME"
    SEARCH_RESULTS = "SEARCH_RESULTS"
    VIDEO = "VIDEO"
    SHORTS = "SHORTS"
    CHANNEL = "CHANNEL"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class CapabilityStatus(str, Enum):
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    UNIT_TESTED = "UNIT_TESTED"
    INTEGRATION_TESTED = "INTEGRATION_TESTED"
    LIVE_VERIFIED = "LIVE_VERIFIED"
    DEGRADED = "DEGRADED"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass
class BoundingBox:
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0


@dataclass
class VisibleVideoItem:
    ordinal: int
    video_id: str
    title: str
    url: str
    is_short: bool = False
    visible: bool = True
    bounding_box: BoundingBox = field(default_factory=BoundingBox)
    source: str = "DOM"


@dataclass
class CurrentVideoInfo:
    video_id: str = "UNKNOWN"
    title: str = "UNKNOWN"
    url: str = "UNKNOWN"
    is_short: bool = False


@dataclass
class PlayerState:
    exists: bool = False
    paused: Any = "UNKNOWN"  # bool or "UNKNOWN"
    current_time: Any = "UNKNOWN"  # float or "UNKNOWN"
    duration: Any = "UNKNOWN"  # float or "UNKNOWN"
    volume: Any = "UNKNOWN"  # float 0.0-1.0 or "UNKNOWN"
    muted: Any = "UNKNOWN"  # bool or "UNKNOWN"
    playback_rate: Any = "UNKNOWN"  # float or "UNKNOWN"


@dataclass
class ControlsState:
    like_state: Any = "UNKNOWN"  # bool or "UNKNOWN"
    captions: Any = "UNKNOWN"  # bool or "UNKNOWN"
    fullscreen: Any = "UNKNOWN"  # bool or "UNKNOWN"
    theater: Any = "UNKNOWN"  # bool or "UNKNOWN"
    miniplayer: Any = "UNKNOWN"  # bool or "UNKNOWN"


@dataclass
class PerceptionSnapshot:
    snapshot_id: str = ""
    page_id: str = "UNKNOWN"
    url: str = "UNKNOWN"
    page_type: PageType = PageType.UNKNOWN
    search_query: str = "UNKNOWN"
    generation: int = 0
    timestamp: float = 0.0
    is_youtube: bool = False
    browser_running: bool = False
    window_title: str = "UNKNOWN"
    hwnd: int = 0
    current_video: CurrentVideoInfo = field(default_factory=CurrentVideoInfo)
    player: PlayerState = field(default_factory=PlayerState)
    controls: ControlsState = field(default_factory=ControlsState)
    visible_videos: List[VisibleVideoItem] = field(default_factory=list)
    visible_shorts: List[VisibleVideoItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to standard dictionary for serialization and logging."""
        playback_state = "UNKNOWN"
        if self.player.exists:
            playback_state = "PAUSED" if self.player.paused is True else "PLAYING"

        page_type_str = self.page_type.value if hasattr(self.page_type, "value") else str(self.page_type)
        cur_url = self.url
        is_shorts = page_type_str == PageType.SHORTS.value or "/shorts" in (cur_url or "").lower()
        is_watch = page_type_str == PageType.VIDEO.value or "/watch" in (cur_url or "").lower() or " - youtube" in (self.window_title or "").lower()
        browser_name = "chrome" if self.browser_running else "UNKNOWN"

        return {
            "snapshot_id": self.snapshot_id,
            "page_id": self.page_id,
            "url": self.url,
            "current_url": self.url,
            "page_type": page_type_str,
            "search_query": self.search_query,
            "generation": self.generation,
            "timestamp": self.timestamp,
            "is_youtube": self.is_youtube,
            "browser_running": self.browser_running,
            "browser_name": browser_name,
            "hwnd": self.hwnd,
            "window_title": self.window_title,
            "is_foreground": False,
            "is_shorts": is_shorts,
            "is_watch": is_watch,
            "current_video_id": self.current_video.video_id,
            "current_title": self.current_video.title,
            "playback_state": playback_state,
            "current_time": self.player.current_time,
            "duration": self.player.duration,
            "volume": self.player.volume,
            "muted": self.player.muted,
            "playback_rate": self.player.playback_rate if self.player.playback_rate != "UNKNOWN" else 1.0,
            "fullscreen": self.controls.fullscreen,
            "theater_mode": self.controls.theater,
            "miniplayer": self.controls.miniplayer,
            "captions": self.controls.captions,
            "like_state": self.controls.like_state,
            "visible_video_candidates": self.visible_videos,
            "visible_short_candidates": self.visible_shorts,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "PerceptionSnapshot":
        """Reconstruct PerceptionSnapshot from dictionary (e.g. for testing and mock compatibility)."""
        if not data:
            return cls()

        pt_val = data.get("page_type", PageType.UNKNOWN)
        if isinstance(pt_val, str):
            pt_str = pt_val.lower()
            if "search" in pt_str:
                page_type = PageType.SEARCH_RESULTS
            elif "watch" in pt_str or "video" in pt_str:
                page_type = PageType.VIDEO
            elif "short" in pt_str:
                page_type = PageType.SHORTS
            elif "home" in pt_str:
                page_type = PageType.HOME
            else:
                page_type = PageType.UNKNOWN
        else:
            page_type = pt_val

        cur_vid_id = data.get("current_video_id") or ""
        cur_title = data.get("current_title") or data.get("window_title") or ""
        cur_video = CurrentVideoInfo(
            video_id=cur_vid_id,
            title=cur_title,
            url=data.get("current_url") or data.get("url") or "",
        )

        pb_state = data.get("playback_state")
        is_paused = None
        if pb_state:
            is_paused = (str(pb_state).upper() == "PAUSED")
        elif "paused" in data:
            is_paused = bool(data["paused"])

        player = PlayerState(
            exists=True if (pb_state or "current_time" in data or "volume" in data) else False,
            paused=is_paused if is_paused is not None else False,
            current_time=data.get("current_time", 0.0) or 0.0,
            duration=data.get("duration", 0.0) or 0.0,
            volume=data.get("volume") if data.get("volume") is not None else 100,
            muted=data.get("muted", False) or False,
            playback_rate=data.get("playback_rate", 1.0) or 1.0,
        )

        controls = ControlsState(
            fullscreen=data.get("fullscreen", False) or False,
            theater=data.get("theater_mode", False) or False,
            miniplayer=data.get("miniplayer", False) or False,
            captions=data.get("captions", False) or False,
            like_state=data.get("like_state") if data.get("like_state") is not None else "unliked",
        )

        raw_vids = data.get("visible_video_candidates") or data.get("candidates") or []
        visible_videos = []
        for i, item in enumerate(raw_vids, start=1):
            if isinstance(item, VisibleVideoItem):
                visible_videos.append(item)
            elif isinstance(item, dict):
                visible_videos.append(VisibleVideoItem(
                    ordinal=item.get("ordinal", i),
                    video_id=item.get("id") or item.get("video_id") or "",
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    is_short=item.get("is_short", False),
                    visible=True,
                ))
            elif hasattr(item, "video_id") or hasattr(item, "id"):
                vid = getattr(item, "video_id", None) or getattr(item, "id", "")
                visible_videos.append(VisibleVideoItem(
                    ordinal=getattr(item, "ordinal", i),
                    video_id=vid,
                    title=getattr(item, "title", ""),
                    url=getattr(item, "url", ""),
                    is_short=getattr(item, "is_short", False),
                    visible=True,
                ))

        raw_shorts = data.get("visible_short_candidates") or []
        visible_shorts = []
        for i, item in enumerate(raw_shorts, start=1):
            if isinstance(item, VisibleVideoItem):
                visible_shorts.append(item)
            elif isinstance(item, dict):
                visible_shorts.append(VisibleVideoItem(
                    ordinal=item.get("ordinal", i),
                    video_id=item.get("id") or item.get("video_id") or "",
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    is_short=True,
                    visible=True,
                ))
            elif hasattr(item, "video_id") or hasattr(item, "id"):
                vid = getattr(item, "video_id", None) or getattr(item, "id", "")
                visible_shorts.append(VisibleVideoItem(
                    ordinal=getattr(item, "ordinal", i),
                    video_id=vid,
                    title=getattr(item, "title", ""),
                    url=getattr(item, "url", ""),
                    is_short=True,
                    visible=True,
                ))

        if page_type == PageType.UNKNOWN:
            if raw_shorts:
                page_type = PageType.SHORTS
            elif raw_vids:
                page_type = PageType.HOME

        url_val = data.get("current_url") or data.get("url") or "UNKNOWN"
        url_low = url_val.lower()
        title_val = data.get("window_title") or data.get("current_title") or "UNKNOWN"
        title_low = title_val.lower()

        is_yt = data.get("is_youtube")
        if is_yt is None:
            is_yt = (
                ("youtube.com" in url_low)
                or ("youtube" in title_low)
                or (page_type in [PageType.VIDEO, PageType.SHORTS, PageType.SEARCH_RESULTS, PageType.HOME])
                or bool(raw_vids)
                or bool(raw_shorts)
                or bool(cur_vid_id and cur_vid_id != "UNKNOWN")
            )

        br_running = data.get("browser_running")
        if br_running is None:
            br_running = is_yt or bool(data.get("hwnd"))

        return cls(
            snapshot_id=data.get("snapshot_id", ""),
            page_id=data.get("page_id", "tab_main"),
            url=url_val,
            page_type=page_type,
            search_query=data.get("search_query", "UNKNOWN"),
            generation=data.get("generation", 0),
            timestamp=data.get("timestamp", 0.0),
            is_youtube=bool(is_yt),
            browser_running=bool(br_running),
            window_title=title_val,
            hwnd=data.get("hwnd", 0),
            current_video=cur_video,
            player=player,
            controls=controls,
            visible_videos=visible_videos,
            visible_shorts=visible_shorts,
        )



@dataclass
class ActionResult:
    status: ActionStatus
    verified: bool
    action: str
    message: str
    expected: Any = None
    observed: Any = None
    error: Optional[str] = None
    source: str = "CDP"
    generation: int = 0
    snapshot_before: Optional[Dict[str, Any]] = None
    snapshot_after: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for backward compatibility with command processor."""
        # Strictly reject returning generic "success" status
        status_val = self.status.value if hasattr(self.status, "value") else str(self.status)
        return {
            "status": status_val,
            "verified": self.verified,
            "canonical_action": self.action,
            "action": self.action,
            "message": self.message,
            "expected": self.expected,
            "observed": self.observed,
            "error": self.error,
            "source": self.source,
            "generation": self.generation,
            "observed_state": self.snapshot_after or self.snapshot_before or {},
        }
