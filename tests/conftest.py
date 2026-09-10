"""Global Pytest Configuration and Test Isolation Sandbox for JARVIS AI.

Enforces 100% hardware-isolated test execution.
Intercepts all Windows OS physical mouse/keyboard/window focus APIs so
running unit tests can NEVER move the physical mouse, click buttons,
steal window focus, or interact with real Chrome.
"""

import os
import sys
import pytest

# Enforce safe development mode environment variables immediately on test collection
os.environ["JARVIS_DEV_SAFE_MODE"] = "1"
os.environ["JARVIS_ALLOW_PHYSICAL_INPUT"] = "0"
os.environ["JARVIS_ALLOW_LIVE_BROWSER_AUTOMATION"] = "0"
os.environ["JARVIS_LIVE_TEST"] = "0"
os.environ["JARVIS_ALLOW_FOREGROUND_FOCUS"] = "0"


class PhysicalCallTracker:
    """Tracks intercepted physical OS calls during test execution."""
    def __init__(self):
        self.set_cursor_pos_calls = 0
        self.mouse_event_calls = 0
        self.keybd_event_calls = 0
        self.set_foreground_window_calls = 0
        self.send_input_calls = 0

    def reset(self):
        self.set_cursor_pos_calls = 0
        self.mouse_event_calls = 0
        self.keybd_event_calls = 0
        self.set_foreground_window_calls = 0
        self.send_input_calls = 0


_global_tracker = PhysicalCallTracker()


@pytest.fixture(autouse=True)
def hardware_isolation_sandbox(monkeypatch):
    """Autouse fixture: Isolates tests completely from real hardware."""
    # Ensure environment variables are strictly safe
    monkeypatch.setenv("JARVIS_DEV_SAFE_MODE", "1")
    monkeypatch.setenv("JARVIS_ALLOW_PHYSICAL_INPUT", "0")
    monkeypatch.setenv("JARVIS_ALLOW_LIVE_BROWSER_AUTOMATION", "0")
    monkeypatch.setenv("JARVIS_LIVE_TEST", "0")
    monkeypatch.setenv("JARVIS_ALLOW_FOREGROUND_FOCUS", "0")

    _global_tracker.reset()

    # Intercept ctypes windll user32 calls if available
    try:
        import ctypes
        if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "user32"):
            user32 = ctypes.windll.user32

            def mock_set_cursor_pos(x, y):
                _global_tracker.set_cursor_pos_calls += 1
                return 1

            def mock_mouse_event(flags, dx=0, dy=0, data=0, extra=0):
                _global_tracker.mouse_event_calls += 1
                return None

            def mock_keybd_event(vk, scan=0, flags=0, extra=0):
                _global_tracker.keybd_event_calls += 1
                return None

            def mock_set_foreground_window(hwnd):
                _global_tracker.set_foreground_window_calls += 1
                return 1

            def mock_send_input(n, inputs, size):
                _global_tracker.send_input_calls += 1
                return n

            monkeypatch.setattr(user32, "SetCursorPos", mock_set_cursor_pos)
            monkeypatch.setattr(user32, "mouse_event", mock_mouse_event)
            monkeypatch.setattr(user32, "keybd_event", mock_keybd_event)
            monkeypatch.setattr(user32, "SetForegroundWindow", mock_set_foreground_window)
            monkeypatch.setattr(user32, "SendInput", mock_send_input)
    except Exception:
        pass

    # Intercept pywin32 calls if available
    try:
        import win32gui
        monkeypatch.setattr(win32gui, "SetForegroundWindow", lambda hwnd: 1)
    except Exception:
        pass

    try:
        import win32api
        monkeypatch.setattr(win32api, "keybd_event", lambda bVk, bScan=0, dwFlags=0, dwExtraInfo=0: None)
        monkeypatch.setattr(win32api, "mouse_event", lambda dwFlags, dx=0, dy=0, dwData=0, dwExtraInfo=0: None)
    except Exception:
        pass

    yield _global_tracker


@pytest.fixture
def call_tracker():
    """Provides access to physical hardware call tracking."""
    return _global_tracker
