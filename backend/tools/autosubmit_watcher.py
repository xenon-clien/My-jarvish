"""
AutoSubmit Watcher for Antigravity IDE.
Runs as a background daemon thread — detects "Submit" / "Proceed" buttons
in the Antigravity window and auto-clicks them.
"""
import ctypes
import logging
import os
import re
import threading
import time
from ctypes import wintypes
from typing import Optional, Tuple

logger = logging.getLogger("AutoSubmit")

# ── Win32 helpers ────────────────────────────────────────────────────────────
try:
    import win32gui
    import win32con
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

# Submit button label variants (case-insensitive)
_SUBMIT_LABELS = [
    "submit", "proceed", "confirm", "ok", "yes", "continue",
    "accept", "apply", "send", "run", "execute",
]

# How often to scan (seconds)
_SCAN_INTERVAL = 1.5
# Minimum gap between auto-clicks (seconds) — prevents double-click spam
_MIN_CLICK_GAP = 4.0

_last_click_time: float = 0.0
_watcher_started: bool = False
_watcher_lock = threading.Lock()


def _get_cursor_pos() -> Tuple[int, int]:
    pt = wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def _left_click(x: int, y: int) -> None:
    """Send a real mouse left-click at (x, y)."""
    user32 = ctypes.windll.user32
    user32.SetCursorPos(x, y)
    time.sleep(0.05)
    user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
    time.sleep(0.04)
    user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP


def _find_antigravity_hwnd() -> Optional[int]:
    """Return the HWND of the active Antigravity window, or None."""
    if not WIN32_AVAILABLE:
        return None
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    h_desk = None
    try:
        GENERIC_ALL = 0x10000000
        h_winsta = user32.OpenWindowStationW("winsta0", False, GENERIC_ALL)
        if h_winsta:
            user32.SetProcessWindowStation(h_winsta)
        h_desk = user32.OpenDesktopW("default", 0, False, GENERIC_ALL)
    except Exception:
        pass

    found = []

    def cb(hwnd, _):
        try:
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value:
                try:
                    import psutil
                    pname = psutil.Process(pid.value).name().lower()
                    if "antigravity" in pname and user32.IsWindowVisible(hwnd):
                        found.append(hwnd)
                except Exception:
                    pass
        except Exception:
            pass
        return True

    proc = WNDENUMPROC(cb)
    try:
        if h_desk:
            user32.EnumDesktopWindows(h_desk, proc, 0)
        else:
            user32.EnumWindows(proc, 0)
    except Exception:
        pass
    return found[0] if found else None


def _find_submit_button_in_window(hwnd: int) -> Optional[Tuple[int, int]]:
    """
    Search child windows of hwnd for a button whose title matches a submit label.
    Returns (center_x, center_y) if found, else None.
    """
    if not WIN32_AVAILABLE:
        return None

    result = []

    def child_cb(child_hwnd, _):
        try:
            cls = win32gui.GetClassName(child_hwnd)
            title = win32gui.GetWindowText(child_hwnd).strip().lower()
            if cls.lower() in ("button", "toolbarwindow32") or any(
                lbl in title for lbl in _SUBMIT_LABELS
            ):
                if title and any(lbl in title for lbl in _SUBMIT_LABELS):
                    if win32gui.IsWindowVisible(child_hwnd) and win32gui.IsWindowEnabled(child_hwnd):
                        rect = win32gui.GetWindowRect(child_hwnd)
                        cx = (rect[0] + rect[2]) // 2
                        cy = (rect[1] + rect[3]) // 2
                        result.append((cx, cy))
                        return False  # stop after first match
        except Exception:
            pass
        return True

    try:
        win32gui.EnumChildWindows(hwnd, child_cb, None)
    except Exception:
        pass
    return result[0] if result else None


def _scan_and_click():
    """Main scan loop — runs forever in a daemon thread."""
    global _last_click_time
    logger.info("AutoSubmit watcher started for Antigravity.")
    while True:
        try:
            time.sleep(_SCAN_INTERVAL)
            hwnd = _find_antigravity_hwnd()
            if not hwnd:
                continue

            btn = _find_submit_button_in_window(hwnd)
            if btn:
                now = time.time()
                if now - _last_click_time >= _MIN_CLICK_GAP:
                    cx, cy = btn
                    logger.info(f"AutoSubmit: Submit button found at ({cx},{cy}), clicking...")
                    _last_click_time = now
                    _left_click(cx, cy)
                    logger.info("AutoSubmit: Clicked Submit button.")
        except Exception as e:
            logger.debug(f"AutoSubmit scan error: {e}")


def start_autosubmit_watcher():
    """Start the AutoSubmit watcher daemon thread (idempotent — only one thread)."""
    global _watcher_started
    with _watcher_lock:
        if _watcher_started:
            return
        if not WIN32_AVAILABLE:
            logger.warning("AutoSubmit watcher requires Windows API (pywin32). Skipping.")
            return
        t = threading.Thread(target=_scan_and_click, daemon=True, name="AutoSubmitWatcher")
        t.start()
        _watcher_started = True
        logger.info("AutoSubmit watcher thread launched.")
