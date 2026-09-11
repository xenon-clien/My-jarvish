"""Perception types and data models for JARVIS EYES V1.

Defines truthful, structured schemas for browser state, DOM-inspected video cards,
player metrics, controls, and perception fusion snapshots.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import time


class PageType(str, Enum):
    """Canonical classification of YouTube pages."""
    HOME = "HOME"
    SEARCH_RESULTS = "SEARCH_RESULTS"
    VIDEO = "VIDEO"
    SHORTS = "SHORTS"
    CHANNEL = "CHANNEL"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class PerceptionSource(str, Enum):
    """Origin of a perceived property."""
    CDP = "CDP"
    DOM = "DOM"
    URL = "URL"
    TITLE = "TITLE"
    UIA = "UIA"
    VISION = "VISION"
    UNKNOWN = "UNKNOWN"


@dataclass
class BoundingBox:
    """Visual bounding rectangle of an element on screen / viewport."""
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass
class VisibleVideoItem:
    """Represents an actual rendered YouTube video or Short card."""
    ordinal: int
    video_id: str
    title: str
    url: str
    is_short: bool = False
    visible: bool = True
    bounding_box: Optional[BoundingBox] = None
    source: str = "DOM"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "video_id": self.video_id,
            "title": self.title,
            "url": self.url,
            "is_short": self.is_short,
            "visible": self.visible,
            "bounding_box": self.bounding_box.to_dict() if self.bounding_box else None,
            "source": self.source,
        }


@dataclass
class CurrentVideoInfo:
    """Metadata for the currently active/playing video."""
    video_id: str = "UNKNOWN"
    title: str = "UNKNOWN"
    url: str = "UNKNOWN"
    is_short: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "video_id": self.video_id,
            "title": self.title,
            "url": self.url,
            "is_short": self.is_short,
        }


@dataclass
class PlayerState:
    """Direct HTML5 <video> media element playback metrics."""
    exists: bool = False
    paused: Union[bool, str] = "UNKNOWN"
    current_time: Union[float, str] = "UNKNOWN"
    duration: Union[float, str] = "UNKNOWN"
    volume: Union[float, str] = "UNKNOWN"
    muted: Union[bool, str] = "UNKNOWN"
    playback_rate: Union[float, str] = "UNKNOWN"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exists": self.exists,
            "paused": self.paused,
            "current_time": self.current_time,
            "duration": self.duration,
            "volume": self.volume,
            "muted": self.muted,
            "playback_rate": self.playback_rate,
        }


@dataclass
class ControlsState:
    """YouTube UI controls states."""
    like_state: Union[bool, str] = "UNKNOWN"
    captions: Union[bool, str] = "UNKNOWN"
    fullscreen: Union[bool, str] = "UNKNOWN"
    theater: Union[bool, str] = "UNKNOWN"
    miniplayer: Union[bool, str] = "UNKNOWN"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "like_state": self.like_state,
            "captions": self.captions,
            "fullscreen": self.fullscreen,
            "theater": self.theater,
            "miniplayer": self.miniplayer,
        }


@dataclass
class BrowserTabInfo:
    """Browser session and target page metadata."""
    connected: bool = False
    page_id: str = "UNKNOWN"
    url: str = "UNKNOWN"
    title: str = "UNKNOWN"
    browser_name: str = "UNKNOWN"
    hwnd: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connected": self.connected,
            "page_id": self.page_id,
            "url": self.url,
            "title": self.title,
            "browser_name": self.browser_name,
            "hwnd": self.hwnd,
        }


@dataclass
class YouTubeState:
    """Complete perception of the YouTube application surface."""
    is_youtube: bool = False
    page_type: PageType = PageType.UNKNOWN
    search_query: str = "UNKNOWN"
    current_video: CurrentVideoInfo = field(default_factory=CurrentVideoInfo)
    player: PlayerState = field(default_factory=PlayerState)
    visible_videos: List[VisibleVideoItem] = field(default_factory=list)
    visible_shorts: List[VisibleVideoItem] = field(default_factory=list)
    controls: ControlsState = field(default_factory=ControlsState)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_youtube": self.is_youtube,
            "page_type": self.page_type.value if isinstance(self.page_type, PageType) else str(self.page_type),
            "search_query": self.search_query,
            "current_video": self.current_video.to_dict(),
            "player": self.player.to_dict(),
            "visible_videos": [v.to_dict() for v in self.visible_videos],
            "visible_shorts": [s.to_dict() for s in self.visible_shorts],
            "controls": self.controls.to_dict(),
        }


@dataclass
class YouTubePerceptionSnapshot:
    """Top-level immutable perception snapshot returned by YouTubePerception."""
    timestamp: float = field(default_factory=time.time)
    browser: BrowserTabInfo = field(default_factory=BrowserTabInfo)
    youtube: YouTubeState = field(default_factory=YouTubeState)
    confidence: Dict[str, float] = field(default_factory=dict)
    sources: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "browser": self.browser.to_dict(),
            "youtube": self.youtube.to_dict(),
            "confidence": self.confidence,
            "sources": self.sources,
        }
