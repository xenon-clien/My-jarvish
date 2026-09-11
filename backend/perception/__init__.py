"""JARVIS EYES V1 — Real Screen + Browser Perception Foundation Package."""

from backend.perception.perception_types import (
    BoundingBox,
    BrowserTabInfo,
    ControlsState,
    CurrentVideoInfo,
    PageType,
    PerceptionSource,
    PlayerState,
    VisibleVideoItem,
    YouTubePerceptionSnapshot,
    YouTubeState,
)
from backend.perception.browser_session import YouTubeBrowserSession, browser_session
from backend.perception.browser_dom import (
    YOUTUBE_DOM_EXTRACTOR_JS,
    parse_dom_extraction_result,
)
from backend.perception.screen_capture import ScreenCapture, screen_capture
from backend.perception.visual_fallback import VisualFallback, visual_fallback
from backend.perception.window_observer import WindowObserver, window_observer
from backend.perception.perception_fusion import PerceptionFusion, perception_fusion
from backend.perception.youtube_perception import YouTubePerception, youtube_perception

__all__ = [
    "BoundingBox",
    "BrowserTabInfo",
    "ControlsState",
    "CurrentVideoInfo",
    "PageType",
    "PerceptionSource",
    "PlayerState",
    "VisibleVideoItem",
    "YouTubePerceptionSnapshot",
    "YouTubeState",
    "YouTubeBrowserSession",
    "browser_session",
    "YOUTUBE_DOM_EXTRACTOR_JS",
    "parse_dom_extraction_result",
    "ScreenCapture",
    "screen_capture",
    "VisualFallback",
    "visual_fallback",
    "WindowObserver",
    "window_observer",
    "PerceptionFusion",
    "perception_fusion",
    "YouTubePerception",
    "youtube_perception",
]
