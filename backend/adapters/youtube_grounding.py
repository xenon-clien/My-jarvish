"""YouTube Grounding Provider & Page Observer for JARVIS.

Provides real browser grounding, dynamic element/candidate discovery,
active tab URL extraction via Windows UI Automation, and closed-loop state verification
without static ordinal coordinates or fake DOM profiles.
"""
from dataclasses import dataclass
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from backend.core.logger import get_logger

logger = get_logger("YouTubeGrounding")

try:
    import ctypes
    import win32gui
    import win32con
    import win32process
    import comtypes.client
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


@dataclass
class YouTubeCandidate:
    """Represents a dynamically discovered YouTube video or Short element."""
    candidate_type: str  # "short" or "video"
    video_id: str
    title: str
    canonical_url: str
    href: str
    bounding_rect: Optional[Tuple[int, int, int, int]] = None  # (left, top, right, bottom)
    visual_order: int = 0
    is_visible: bool = True
    is_interactable: bool = True


class YouTubePageObserver:
    """Observes live YouTube browser state without static screen coordinates."""

    def __init__(self):
        self._ensure_desktop_access()

    def _ensure_desktop_access(self) -> None:
        """Ensure thread is attached to the user's interactive desktop."""
        if not WIN32_AVAILABLE:
            return
        try:
            user32 = ctypes.windll.user32
            user32.OpenDesktopW.restype = ctypes.c_void_p
            user32.SetThreadDesktop.argtypes = [ctypes.c_void_p]
            hDesk = user32.OpenDesktopW("default", 0, False, 0x01FF)
            if hDesk:
                user32.SetThreadDesktop(hDesk)
        except Exception:
            pass

    def switch_to_youtube_tab(self, hwnd: int) -> bool:
        """If Chrome/browser has an open YouTube tab in background, switch to it immediately."""
        if not WIN32_AVAILABLE or not hwnd:
            return False
        self._ensure_desktop_access()
        try:
            mod = comtypes.client.GetModule("UIAutomationCore.dll")
            uia = comtypes.client.CreateObject(mod.CUIAutomation, interface=mod.IUIAutomation)
            elem = uia.ElementFromHandle(hwnd)
            if not elem:
                return False
            cond = uia.CreatePropertyCondition(30003, 50019)  # TabItem ControlType
            tabs = elem.FindAll(mod.TreeScope_Descendants, cond)
            if not tabs:
                return False
            for i in range(tabs.Length):
                t = tabs.GetElement(i)
                name = (t.CurrentName or "").lower()
                if "youtube" in name:
                    pat = t.GetCurrentPattern(10010)  # SelectionItemPattern
                    sel_pat = pat.QueryInterface(mod.IUIAutomationSelectionItemPattern)
                    sel_pat.Select()
                    logger.info(f"Switched directly to existing YouTube tab: '{t.CurrentName}'")
                    return True
        except Exception as exc:
            logger.debug(f"switch_to_youtube_tab error: {exc}")
        return False

    def get_browser_window(self) -> Optional[Tuple[int, str, str, Tuple[int, int, int, int]]]:
        """Discover the genuine foreground or active Chrome/Edge/Brave browser window.
        
        Returns:
            (hwnd, title, class_name, (left, top, right, bottom)) or None
        """
        if not WIN32_AVAILABLE:
            return None
        self._ensure_desktop_access()

        candidates = []

        def enum_cb(hwnd, extra):
            try:
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd).strip()
                    cls = win32gui.GetClassName(hwnd).strip()
                    t_low = title.lower()
                    c_low = cls.lower()

                    # Filter out IDEs, terminals, and assistant windows
                    excluded = ["antigravity", "visual studio code", "vscode", "cmd.exe", "powershell", "cursor", "jarvis", "j.a.r.v.i.s."]
                    if any(ex in t_low for ex in excluded):
                        return True

                    if any(b in t_low or b in c_low for b in ["chrome", "edge", "brave", "youtube"]):
                        rect = win32gui.GetWindowRect(hwnd)
                        w = rect[2] - rect[0]
                        h = rect[3] - rect[1]
                        if w > 300 and h > 200:
                            score = 100 if "youtube" in t_low else 50
                            if hwnd == win32gui.GetForegroundWindow():
                                score += 30
                            extra.append((score, hwnd, title, cls, rect))
            except Exception:
                pass
            return True

        h_desk = None
        try:
            user32 = ctypes.windll.user32
            user32.OpenDesktopW.restype = ctypes.c_void_p
            h_desk = user32.OpenDesktopW("default", 0, False, 0x01FF)
        except Exception:
            pass

        try:
            if h_desk:
                win32gui.EnumDesktopWindows(h_desk, enum_cb, candidates)
            else:
                win32gui.EnumWindows(enum_cb, candidates)
        except Exception:
            try:
                win32gui.EnumWindows(enum_cb, candidates)
            except Exception:
                pass

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        _, best_hwnd, best_title, best_cls, best_rect = candidates[0]
        return best_hwnd, best_title, best_cls, best_rect

    def get_active_url(self, hwnd: int) -> Optional[str]:
        """Extract the real-time active URL from Google Chrome / Edge using UIA Omnibox edit control."""
        if not WIN32_AVAILABLE or not hwnd:
            return None
        self._ensure_desktop_access()

        try:
            mod = comtypes.client.GetModule("UIAutomationCore.dll")
            uia = comtypes.client.CreateObject(mod.CUIAutomation, interface=mod.IUIAutomation)
            root = uia.ElementFromHandle(hwnd)
            if not root:
                return None

            # Address bar edit control (UIA_EditControlTypeId = 50004)
            cond = uia.CreatePropertyCondition(mod.UIA_ControlTypePropertyId, mod.UIA_EditControlTypeId)
            edit_el = root.FindFirst(mod.TreeScope_Descendants, cond)
            if edit_el:
                pattern = edit_el.GetCurrentPattern(mod.UIA_ValuePatternId)
                if pattern:
                    val_obj = pattern.QueryInterface(mod.IUIAutomationValuePattern)
                    val = val_obj.CurrentValue
                    if val:
                        # Normalize URL
                        v_str = str(val).strip()
                        if not v_str.startswith("http://") and not v_str.startswith("https://"):
                            v_str = f"https://{v_str}"
                        return v_str
        except Exception as exc:
            logger.debug(f"get_active_url UIA inspection error: {exc}")
        return None

    def observe(self) -> Dict[str, Any]:
        """Full observation of live YouTube browser state with truthful values or UNKNOWN."""
        self._ensure_desktop_access()

        state: Dict[str, Any] = {
            "browser_running": False,
            "browser_name": "UNKNOWN",
            "hwnd": 0,
            "window_title": "UNKNOWN",
            "is_foreground": False,
            "current_url": "UNKNOWN",
            "page_type": "UNKNOWN",
            "current_video_id": "UNKNOWN",
            "current_title": "UNKNOWN",
            "playback_state": "UNKNOWN",
            "current_time": "UNKNOWN",
            "duration": "UNKNOWN",
            "volume": "UNKNOWN",
            "muted": "UNKNOWN",
            "fullscreen": "UNKNOWN",
            "theater_mode": "UNKNOWN",
            "miniplayer": "UNKNOWN",
            "captions": "UNKNOWN",
            "playback_rate": 1.0,
            "like_state": "UNKNOWN",
            "visible_video_candidates": [],
            "visible_short_candidates": [],
        }

        win_info = self.get_browser_window()
        if not win_info:
            return state

        hwnd, title, cls, rect = win_info
        state["browser_running"] = True
        state["hwnd"] = hwnd
        state["window_title"] = title
        state["is_foreground"] = (hwnd == win32gui.GetForegroundWindow())

        t_low = title.lower()
        c_low = cls.lower()
        if "edge" in t_low or "edge" in c_low:
            state["browser_name"] = "edge"
        elif "brave" in t_low or "brave" in c_low:
            state["browser_name"] = "brave"
        else:
            state["browser_name"] = "chrome"

        # 1. URL Observation
        url = self.get_active_url(hwnd)
        if url:
            state["current_url"] = url
            u_low = url.lower()

            # Determine page type
            if "/shorts" in u_low:
                state["page_type"] = "SHORTS"
                match_short = re.search(r"/shorts/([a-zA-Z0-9_-]{11})", url)
                if match_short:
                    state["current_video_id"] = match_short.group(1)
            elif "/watch" in u_low:
                state["page_type"] = "VIDEO"
                match_v = re.search(r"[?&]v=([a-zA-Z0-9_-]{11})", url)
                if match_v:
                    state["current_video_id"] = match_v.group(1)
            elif "/results" in u_low or "search_query=" in u_low:
                state["page_type"] = "SEARCH_RESULTS"
            elif "youtube.com" in u_low:
                if u_low.rstrip("/").endswith("youtube.com"):
                    state["page_type"] = "HOME"
                else:
                    state["page_type"] = "OTHER"
            else:
                state["page_type"] = "OTHER"
        else:
            # Fallback title-based classification
            if "youtube" in t_low:
                if "short" in t_low:
                    state["page_type"] = "SHORTS"
                elif " - youtube" in t_low:
                    state["page_type"] = "VIDEO"
                else:
                    state["page_type"] = "HOME"
            else:
                state["page_type"] = "UNKNOWN"

        # 2. Extract title
        if " - youtube" in t_low:
            clean_t = re.sub(r"\s*-\s*youtube.*$", "", title, flags=re.IGNORECASE).strip()
            state["current_title"] = clean_t
        elif state["page_type"] == "HOME":
            state["current_title"] = "YouTube Home"

        # 3. Fullscreen check (Window covers entire screen resolution)
        try:
            user32 = ctypes.windll.user32
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            if rect[0] <= 0 and rect[1] <= 0 and w >= screen_w and h >= screen_h:
                state["fullscreen"] = True
            else:
                state["fullscreen"] = False
        except Exception:
            state["fullscreen"] = "UNKNOWN"

        # 4. Discover dynamic candidates
        state["visible_short_candidates"] = self.discover_short_candidates(hwnd, rect)
        state["visible_video_candidates"] = self.discover_video_candidates(hwnd, rect)

        return state

    def discover_short_candidates(self, hwnd: int, window_rect: Tuple[int, int, int, int]) -> List[YouTubeCandidate]:
        """Discover live visible Short candidates dynamically on page."""
        candidates: List[YouTubeCandidate] = []
        if not WIN32_AVAILABLE or not hwnd:
            return candidates

        self._ensure_desktop_access()

        # Inspect UIA tree for Short links
        try:
            mod = comtypes.client.GetModule("UIAutomationCore.dll")
            uia = comtypes.client.CreateObject(mod.CUIAutomation, interface=mod.IUIAutomation)
            root = uia.ElementFromHandle(hwnd)
            if root:
                cond_link = uia.CreatePropertyCondition(mod.UIA_ControlTypePropertyId, mod.UIA_HyperlinkControlTypeId)
                elements = root.FindAll(mod.TreeScope_Descendants, cond_link)
                if elements:
                    seen_ids = set()
                    for i in range(elements.Length):
                        el = elements.GetElement(i)
                        name = el.CurrentName or ""
                        href = ""
                        try:
                            val_p = el.GetCurrentPattern(mod.UIA_ValuePatternId)
                            if val_p:
                                href = val_p.QueryInterface(mod.IUIAutomationValuePattern).CurrentValue or ""
                        except Exception:
                            pass

                        match = re.search(r"/shorts/([a-zA-Z0-9_-]{11})", f"{name} {href}")
                        if match:
                            vid_id = match.group(1)
                            if vid_id not in seen_ids:
                                seen_ids.add(vid_id)
                                brect = el.CurrentBoundingRectangle
                                rect_tuple = (brect.left, brect.top, brect.right, brect.bottom)
                                candidates.append(YouTubeCandidate(
                                    candidate_type="short",
                                    video_id=vid_id,
                                    title=name,
                                    canonical_url=f"https://www.youtube.com/shorts/{vid_id}",
                                    href=f"/shorts/{vid_id}",
                                    bounding_rect=rect_tuple,
                                    visual_order=len(candidates) + 1,
                                ))
        except Exception as exc:
            logger.debug(f"UIA candidate discovery exception: {exc}")

        return candidates

    def discover_video_candidates(self, hwnd: int, window_rect: Tuple[int, int, int, int]) -> List[YouTubeCandidate]:
        """Discover live visible standard video candidates dynamically on page."""
        candidates: List[YouTubeCandidate] = []
        if not WIN32_AVAILABLE or not hwnd:
            return candidates

        self._ensure_desktop_access()

        try:
            mod = comtypes.client.GetModule("UIAutomationCore.dll")
            uia = comtypes.client.CreateObject(mod.CUIAutomation, interface=mod.IUIAutomation)
            root = uia.ElementFromHandle(hwnd)
            if root:
                cond_link = uia.CreatePropertyCondition(mod.UIA_ControlTypePropertyId, mod.UIA_HyperlinkControlTypeId)
                elements = root.FindAll(mod.TreeScope_Descendants, cond_link)
                if elements:
                    seen_ids = set()
                    for i in range(elements.Length):
                        el = elements.GetElement(i)
                        name = el.CurrentName or ""
                        href = ""
                        try:
                            val_p = el.GetCurrentPattern(mod.UIA_ValuePatternId)
                            if val_p:
                                href = val_p.QueryInterface(mod.IUIAutomationValuePattern).CurrentValue or ""
                        except Exception:
                            pass

                        match = re.search(r"[?&]v=([a-zA-Z0-9_-]{11})", f"{name} {href}")
                        if match:
                            vid_id = match.group(1)
                            if vid_id not in seen_ids:
                                seen_ids.add(vid_id)
                                brect = el.CurrentBoundingRectangle
                                rect_tuple = (brect.left, brect.top, brect.right, brect.bottom)
                                candidates.append(YouTubeCandidate(
                                    candidate_type="video",
                                    video_id=vid_id,
                                    title=name,
                                    canonical_url=f"https://www.youtube.com/watch?v={vid_id}",
                                    href=f"/watch?v={vid_id}",
                                    bounding_rect=rect_tuple,
                                    visual_order=len(candidates) + 1,
                                ))
        except Exception as exc:
            logger.debug(f"UIA video candidate discovery exception: {exc}")

        return candidates


# Global Singleton Observer
youtube_page_observer = YouTubePageObserver()
