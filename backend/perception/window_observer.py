"""OS Window Observer for Browser and Desktop Perception.

Inspects active Windows processes and top-level windows to identify genuine
Chrome, Edge, or Brave browser windows, foreground status, window geometry,
and omnibox URL fallback via UIAutomation.
"""
import os
import re
from typing import Any, Dict, List, Optional, Tuple
from backend.core.logger import get_logger

logger = get_logger("WindowObserver")

try:
    import ctypes
    import win32gui
    import win32con
    import win32process
    import comtypes.client
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


class WindowObserver:
    """Discovers and inspects OS-level browser windows without coordinate assumptions."""

    def __init__(self):
        self._ensure_desktop_access()

    def _ensure_desktop_access(self) -> None:
        """Ensure current thread is attached to the default interactive desktop."""
        if not WIN32_AVAILABLE:
            return
        try:
            user32 = ctypes.windll.user32
            user32.OpenDesktopW.restype = ctypes.c_void_p
            user32.SetThreadDesktop.argtypes = [ctypes.c_void_p]
            h_desk = user32.OpenDesktopW("default", 0, False, 0x01FF)
            if h_desk:
                user32.SetThreadDesktop(h_desk)
        except Exception:
            pass

    def get_browser_window(self) -> Optional[Tuple[int, str, str, Tuple[int, int, int, int]]]:
        """Find the active Google Chrome or Chromium browser window.
        
        Returns:
            (hwnd, title, class_name, (left, top, right, bottom)) or None
        """
        if not WIN32_AVAILABLE:
            return None
        self._ensure_desktop_access()

        candidates: List[Tuple[int, int, str, str, Tuple[int, int, int, int]]] = []

        def enum_handler(hwnd, extra):
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return
                title = win32gui.GetWindowText(hwnd).strip()
                cls = win32gui.GetClassName(hwnd).strip()
                t_low = title.lower()
                c_low = cls.lower()

                # Filter out IDEs, terminals, and non-browsers
                if any(ex in t_low for ex in ["antigravity", "visual studio code", "vscode", "cmd.exe", "powershell", "jarvis", "j.a.r.v.i.s."]):
                    return

                # Target genuine browsers
                if "chrome" in c_low or "chrome" in t_low or "edge" in c_low or "edge" in t_low or "brave" in c_low:
                    rect = win32gui.GetWindowRect(hwnd)
                    w = rect[2] - rect[0]
                    h = rect[3] - rect[1]
                    if w > 300 and h > 200:
                        score = 100 if "youtube" in t_low else 50
                        if hwnd == win32gui.GetForegroundWindow():
                            score += 25
                        extra.append((score, hwnd, title, cls, rect))
            except Exception:
                pass

        try:
            win32gui.EnumWindows(enum_handler, candidates)
        except Exception:
            pass

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        _, best_hwnd, best_title, best_cls, best_rect = candidates[0]
        return best_hwnd, best_title, best_cls, best_rect

    def get_omnibox_url(self, hwnd: int) -> Optional[str]:
        """Extract the active tab URL from the Chrome/Edge Omnibox via UIA fallback."""
        if not WIN32_AVAILABLE or not hwnd:
            return None
        self._ensure_desktop_access()

        try:
            mod = comtypes.client.GetModule("UIAutomationCore.dll")
            uia = comtypes.client.CreateObject(mod.CUIAutomation, interface=mod.IUIAutomation)
            root = uia.ElementFromHandle(hwnd)
            if not root:
                return None

            # EditControlTypeId = 50004
            cond = uia.CreatePropertyCondition(mod.UIA_ControlTypePropertyId, mod.UIA_EditControlTypeId)
            edit_el = root.FindFirst(mod.TreeScope_Descendants, cond)
            if edit_el:
                pattern = edit_el.GetCurrentPattern(mod.UIA_ValuePatternId)
                if pattern:
                    val_obj = pattern.QueryInterface(mod.IUIAutomationValuePattern)
                    val = val_obj.CurrentValue
                    if val:
                        v_str = str(val).strip()
                        if not v_str.startswith("http://") and not v_str.startswith("https://"):
                            v_str = f"https://{v_str}"
                        return v_str
        except Exception as exc:
            logger.debug(f"Omnibox URL inspection error: {exc}")
        return None


# Global singleton
window_observer = WindowObserver()
