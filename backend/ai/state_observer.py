"""Computer State Awareness & Screen Observer Layer for JARVIS AI.

Inspects the real-time state of the computer:
- Active foreground application and window title
- Running user desktop applications
- Active browser tab / context
- Screen spatial layout and coordinate mapping
Answers the core questions: 'Where am I?', 'What app is active?', 'What is on screen?'
"""
import ctypes
from ctypes import wintypes
import os
import time
from typing import Any, Dict, List, Optional, Tuple
import psutil
from pydantic import BaseModel, Field

from backend.core.logger import get_logger

logger = get_logger("StateObserver")


class ActiveComputerState(BaseModel):
    """Snapshot of the computer's current active state."""
    active_window_title: str = ""
    active_process_name: str = ""
    active_app_category: str = "unknown"  # browser, editor, file_manager, terminal, media, system, unknown
    running_applications: List[str] = Field(default_factory=list)
    is_browser_active: bool = False
    screen_width: int = 1920
    screen_height: int = 1080
    timestamp: float = Field(default_factory=time.time)
    context_details: Dict[str, Any] = Field(default_factory=dict)


class ComputerStateObserver:
    """Observes and analyzes current computer state across Windows applications."""

    # Categorization of common Windows processes
    APP_CATEGORIES = {
        "chrome.exe": "browser",
        "msedge.exe": "browser",
        "firefox.exe": "browser",
        "brave.exe": "browser",
        "code.exe": "editor",
        "notepad.exe": "editor",
        "explorer.exe": "file_manager",
        "cmd.exe": "terminal",
        "powershell.exe": "terminal",
        "wt.exe": "terminal",
        "spotify.exe": "media",
        "vlc.exe": "media",
        "systemsettings.exe": "system",
        "taskmgr.exe": "system",
        "whatsapp.exe": "messaging",
    }

    @classmethod
    def get_screen_resolution(cls) -> Tuple[int, int]:
        """Get the primary screen resolution."""
        try:
            user32 = ctypes.windll.user32
            w = user32.GetSystemMetrics(0)
            h = user32.GetSystemMetrics(1)
            return (w if w > 0 else 1920, h if h > 0 else 1080)
        except Exception:
            return (1920, 1080)

    @classmethod
    def get_active_window_info(cls) -> Tuple[Optional[int], str, str]:
        """Retrieve HWND, window title, and process name of the active foreground window."""
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return None, "", ""

            # Get title
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value.strip()

            # Get process name
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            proc_name = ""
            if pid.value > 0:
                try:
                    proc_name = psutil.Process(pid.value).name().lower()
                except Exception:
                    pass

            return hwnd, title, proc_name
        except Exception as exc:
            logger.debug(f"Error inspecting active window: {exc}")
            return None, "", ""

    @classmethod
    def get_running_apps(cls) -> List[str]:
        """List currently running top-level user applications with sub-millisecond latency."""
        running = set()
        user32 = ctypes.windll.user32

        def enum_win_proc(hwnd, _):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    try:
                        p = psutil.Process(pid.value)
                        pname = p.name().lower()
                        if pname in cls.APP_CATEGORIES:
                            running.add(pname)
                    except Exception:
                        pass
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        try:
            user32.EnumWindows(WNDENUMPROC(enum_win_proc), 0)
        except Exception:
            pass
        return sorted(list(running))

    @classmethod
    def capture_current_state(cls) -> ActiveComputerState:
        """Capture a complete snapshot of current active computer state."""
        hwnd, title, proc_name = cls.get_active_window_info()
        category = cls.APP_CATEGORIES.get(proc_name, "unknown")
        running = cls.get_running_apps()
        sw, sh = cls.get_screen_resolution()

        is_browser = category == "browser" or "youtube" in title.lower() or "chrome" in title.lower()

        state = ActiveComputerState(
            active_window_title=title,
            active_process_name=proc_name,
            active_app_category=category,
            running_applications=running,
            is_browser_active=is_browser,
            screen_width=sw,
            screen_height=sh,
            context_details={"hwnd": hwnd},
        )
        logger.debug(f"Computer state observed: app='{proc_name}', title='{title}', category='{category}'")
        return state

    @classmethod
    def resolve_spatial_coordinates(
        cls,
        spatial_hint: str,
        base_rect: Optional[Tuple[int, int, int, int]] = None,
    ) -> Tuple[int, int]:
        """Resolve natural spatial references ('upar wala', 'neeche wala', 'left', 'right', 'beech wala')

        into exact pixel coordinates on the active window or screen.
        """
        hint = spatial_hint.lower().strip()
        sw, sh = cls.get_screen_resolution()

        if base_rect:
            left, top, right, bottom = base_rect
            w = right - left
            h = bottom - top
        else:
            left, top, w, h = 0, 0, sw, sh

        # Spatial reference grid mapping
        if any(w in hint for w in ["upar wala", "top", "upper", "first", "pehla", "pehli", "1st"]):
            # Top-left / Top-center region
            return (int(left + w * 0.25), int(top + h * 0.35))

        elif any(w in hint for w in ["neeche wala", "bottom", "lower", "down"]):
            # Bottom region
            return (int(left + w * 0.25), int(top + h * 0.75))

        elif any(w in hint for w in ["right side wala", "right side", "right", "daye"]):
            # Right sidebar / right column
            return (int(left + w * 0.75), int(top + h * 0.40))

        elif any(w in hint for w in ["left side wala", "left side", "left", "baye"]):
            # Left sidebar / left column
            return (int(left + w * 0.20), int(top + h * 0.40))

        elif any(w in hint for w in ["beech wala", "center", "middle", "middle wala"]):
            # Center region
            return (int(left + w * 0.50), int(top + h * 0.45))

        elif any(w in hint for w in ["second", "dusra", "dusri", "2nd"]):
            # Second item in grid
            return (int(left + w * 0.55), int(top + h * 0.35))

        elif any(w in hint for w in ["third", "teesra", "teesri", "3rd"]):
            # Third item in grid
            return (int(left + w * 0.82), int(top + h * 0.35))

        # Default to window center
        return (int(left + w * 0.50), int(top + h * 0.50))


# Global singleton observer
state_observer = ComputerStateObserver()
