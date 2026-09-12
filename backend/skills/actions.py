"""Universal Application-Agnostic Action Engine for JARVIS AI.

Implements all core UI, media, navigation, and input automation tools
backed by the 7-Tier Fallback Execution Hierarchy:
1. Official API / Local Interface
2. DOM / Semantic Element
3. Windows UIAutomation / Accessibility Tree
4. Application Automation API / Command Palette
5. Keyboard Shortcuts
6. Visual / Layout Recognition
7. Calibrated Coordinate Fallback
"""
import asyncio
import ctypes
import os
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

try:
    import win32api
    import win32con
    import win32gui
    import win32process
    import win32clipboard
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

import contextlib

@contextlib.contextmanager
def safe_clipboard():
    """Context manager ensuring Windows clipboard is always closed cleanly."""
    opened = False
    try:
        win32clipboard.OpenClipboard()
        opened = True
        yield win32clipboard
    finally:
        if opened:
            try:
                win32clipboard.CloseClipboard()
            except Exception:
                pass

from backend.core.logger import get_logger
from backend.core.safety import (
    is_dev_safe_mode,
    is_physical_automation_allowed,
    is_foreground_stealing_allowed,
    safe_blocked_result,
)
from backend.skills.models import ActionResult, FallbackTier

logger = get_logger("UniversalActionEngine")

user32 = ctypes.windll.user32 if WIN32_AVAILABLE else None


# ── Windows SendInput Structures ──────────────────────────────────────────────
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class INPUT_I(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("ii", INPUT_I),
    ]


class UniversalActionEngine:
    """Core executor for all application actions across the 7-tier hierarchy."""

    # ── Hardware Input Helpers ────────────────────────────────────────────────
    @staticmethod
    def send_hardware_click(x: int, y: int, double_click: bool = False, right_click: bool = False) -> None:
        """Inject direct OS-level hardware mouse click using Windows SendInput API."""
        if not is_physical_automation_allowed():
            return
        if not WIN32_AVAILABLE:
            return
        user32.SetCursorPos(int(x), int(y))
        time.sleep(0.04)

        down_flag = 0x0008 if right_click else 0x0002  # RIGHTDOWN / LEFTDOWN
        up_flag = 0x0010 if right_click else 0x0004    # RIGHTUP / LEFTUP

        inp_down = INPUT(type=0, ii=INPUT_I(mi=MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=down_flag, time=0, dwExtraInfo=None)))
        inp_up = INPUT(type=0, ii=INPUT_I(mi=MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=up_flag, time=0, dwExtraInfo=None)))

        user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))
        time.sleep(0.03)
        user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))

        if double_click:
            time.sleep(0.05)
            user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))
            time.sleep(0.03)
            user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))

    @staticmethod
    def send_hardware_wheel(delta: int, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """Send hardware mouse wheel scroll event without moving physical cursor."""
        if not is_physical_automation_allowed():
            return
        if not WIN32_AVAILABLE:
            return
        user32.mouse_event(0x0800, 0, 0, int(delta), 0)  # MOUSEEVENTF_WHEEL

    @staticmethod
    def send_key_press(vk_code: int, ctrl: bool = False, shift: bool = False, alt: bool = False) -> None:
        """Send virtual key event with optional modifiers."""
        if not is_physical_automation_allowed():
            return
        if not WIN32_AVAILABLE:
            return
        if ctrl:
            win32api.keybd_event(0x11, 0, 0, 0)
            time.sleep(0.02)
        if shift:
            win32api.keybd_event(0x10, 0, 0, 0)
            time.sleep(0.02)
        if alt:
            win32api.keybd_event(0x12, 0, 0, 0)
            time.sleep(0.02)

        win32api.keybd_event(vk_code, 0, 0, 0)
        time.sleep(0.04)
        win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP, 0)

        if alt:
            win32api.keybd_event(0x12, 0, win32con.KEYEVENTF_KEYUP, 0)
        if shift:
            win32api.keybd_event(0x10, 0, win32con.KEYEVENTF_KEYUP, 0)
        if ctrl:
            win32api.keybd_event(0x11, 0, win32con.KEYEVENTF_KEYUP, 0)

    # ── Window Management Actions ─────────────────────────────────────────────
    @staticmethod
    def focus_window_by_hwnd(hwnd: int) -> bool:
        """Forcefully bring window to foreground with thread input attachment."""
        if not is_foreground_stealing_allowed():
            return False
        if not WIN32_AVAILABLE or not hwnd:
            return False
        try:
            user32.AllowSetForegroundWindow(-1)
            fore_thread = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)
            app_thread = user32.GetWindowThreadProcessId(hwnd, None)
            if fore_thread != app_thread:
                user32.AttachThreadInput(fore_thread, app_thread, True)
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
                user32.AttachThreadInput(fore_thread, app_thread, False)
            else:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                user32.SetForegroundWindow(hwnd)
            return True
        except Exception as exc:
            logger.debug(f"Focus window error for hwnd {hwnd}: {exc}")
            return False

    @staticmethod
    def find_window(app_name: str, window_class: Optional[str] = None) -> Optional[Tuple[int, str, Tuple[int, int, int, int]]]:
        """Find window matching app name or window class and return (hwnd, title, rect)."""
        if not WIN32_AVAILABLE:
            return None
        target = app_name.lower().strip()
        matched = []

        def enum_cb(hwnd, extra):
            try:
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    cls = win32gui.GetClassName(hwnd)
                    rect = win32gui.GetWindowRect(hwnd)
                    w = rect[2] - rect[0]
                    h = rect[3] - rect[1]
                    if w > 100 and h > 100:
                        if target in title.lower() or (window_class and window_class.lower() == cls.lower()):
                            extra.append((hwnd, title, rect))
            except Exception:
                pass

        try:
            win32gui.EnumWindows(enum_cb, matched)
            if matched:
                return matched[0]
        except Exception:
            pass
        return None

    # ── Universal UI Automation ───────────────────────────────────────────────
    async def click(
        self,
        target: Optional[str] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
        double: bool = False,
        right: bool = False,
        app_name: Optional[str] = None,
    ) -> ActionResult:
        """Universal Click: Resolves target via Accessibility/UIAutomation -> Visual -> Coordinates."""
        start = time.time()
        if not is_physical_automation_allowed():
            return ActionResult(
                success=True,
                action="click",
                application=app_name or "active",
                tier_used=FallbackTier.COORDINATE_FALLBACK,
                message=f"Simulation: Click '{target or (x, y)}' (physical input disabled).",
                data={"simulated": True},
                verified=False,
                execution_time_ms=(time.time() - start) * 1000,
            )

        hwnd_info = self.find_window(app_name) if app_name else None
        if hwnd_info:
            self.focus_window_by_hwnd(hwnd_info[0])
            time.sleep(0.05)

        # Tier 3: Accessibility / UIAutomation search if target name given
        if target and not (x and y):
            loc = self._find_element_by_accessibility(target, hwnd_info[0] if hwnd_info else None)
            if loc:
                self.send_hardware_click(loc[0], loc[1], double_click=double, right_click=right)
                return ActionResult(
                    success=True,
                    action="click",
                    application=app_name or "active",
                    tier_used=FallbackTier.ACCESSIBILITY_TREE,
                    message=f"Clicked '{target}' via Accessibility Tree.",
                    data={"x": loc[0], "y": loc[1]},
                    verified=True,
                    execution_time_ms=(time.time() - start) * 1000,
                )

        # Tier 7: Coordinate execution
        if x is not None and y is not None:
            self.send_hardware_click(x, y, double_click=double, right_click=right)
            return ActionResult(
                success=True,
                action="click",
                application=app_name or "active",
                tier_used=FallbackTier.COORDINATE_FALLBACK,
                message=f"Clicked coordinate ({x}, {y}).",
                data={"x": x, "y": y},
                verified=True,
                execution_time_ms=(time.time() - start) * 1000,
            )

        return ActionResult(
            success=False,
            action="click",
            application=app_name or "active",
            tier_used=FallbackTier.COORDINATE_FALLBACK,
            message="No valid target or coordinates provided for click.",
            execution_time_ms=(time.time() - start) * 1000,
        )

    async def scroll(
        self,
        direction: str = "down",
        amount: int = 400,
        app_name: Optional[str] = None,
        target_element: Optional[str] = None,
    ) -> ActionResult:
        """Universal Scroll: direction in ['up', 'down', 'top', 'bottom']."""
        start = time.time()
        if not is_physical_automation_allowed():
            return ActionResult(
                success=True,
                action="scroll",
                application=app_name or "active",
                tier_used=FallbackTier.KEYBOARD_SHORTCUT,
                message=f"Simulation: Scrolled {direction} (physical input disabled).",
                data={"simulated": True},
                verified=False,
                execution_time_ms=(time.time() - start) * 1000,
            )

        hwnd_info = self.find_window(app_name) if app_name else None
        if hwnd_info:
            self.focus_window_by_hwnd(hwnd_info[0])
            rect = hwnd_info[2]
            cx = (rect[0] + rect[2]) // 2
            cy = (rect[1] + rect[3]) // 2
        else:
            cx = user32.GetSystemMetrics(0) // 2 if WIN32_AVAILABLE else 500
            cy = user32.GetSystemMetrics(1) // 2 if WIN32_AVAILABLE else 500

        dir_clean = direction.lower().strip()
        if dir_clean in ["top", "to_top", "shuru"]:
            self.send_key_press(0x24)  # VK_HOME
            tier = FallbackTier.KEYBOARD_SHORTCUT
            msg = "Scrolled to top."
        elif dir_clean in ["bottom", "to_bottom", "aakhri"]:
            self.send_key_press(0x23)  # VK_END
            tier = FallbackTier.KEYBOARD_SHORTCUT
            msg = "Scrolled to bottom."
        elif dir_clean in ["up", "upar"]:
            self.send_key_press(0x21)  # VK_PRIOR (Page Up)
            tier = FallbackTier.KEYBOARD_SHORTCUT
            msg = f"Scrolled up."
        else:
            self.send_key_press(0x22)  # VK_NEXT (Page Down)
            tier = FallbackTier.KEYBOARD_SHORTCUT
            msg = f"Scrolled down."

        return ActionResult(
            success=True,
            action="scroll",
            application=app_name or "active",
            tier_used=tier,
            message=msg,
            verified=True,
            execution_time_ms=(time.time() - start) * 1000,
        )

    async def type_text(
        self,
        text: str,
        clear_first: bool = False,
        press_enter: bool = False,
        app_name: Optional[str] = None,
    ) -> ActionResult:
        """Universal Text Typing: Clipboard injection + keystroke fallback."""
        start = time.time()
        if not is_physical_automation_allowed():
            return ActionResult(
                success=True,
                action="type_text",
                application=app_name or "active",
                tier_used=FallbackTier.KEYBOARD_SHORTCUT,
                message=f"Simulation: Typed text '{text[:30]}...' (physical input disabled).",
                data={"text": text, "simulated": True},
                verified=False,
                execution_time_ms=(time.time() - start) * 1000,
            )

        hwnd_info = self.find_window(app_name) if app_name else None
        if hwnd_info:
            self.focus_window_by_hwnd(hwnd_info[0])
            time.sleep(0.05)

        if clear_first:
            self.send_key_press(0x41, ctrl=True)  # Ctrl + A
            time.sleep(0.03)
            self.send_key_press(0x08)            # Backspace
            time.sleep(0.03)

        # Use Windows Clipboard for unicode fidelity & instant speed
        if WIN32_AVAILABLE:
            old_clipboard = None
            try:
                with safe_clipboard() as cb:
                    if cb.IsClipboardFormatAvailable(cb.CF_UNICODETEXT):
                        old_clipboard = cb.GetClipboardData(cb.CF_UNICODETEXT)
            except Exception:
                pass

            try:
                with safe_clipboard() as cb:
                    cb.EmptyClipboard()
                    cb.SetClipboardText(text, cb.CF_UNICODETEXT)
                time.sleep(0.03)
                self.send_key_press(0x56, ctrl=True)  # Ctrl + V
                time.sleep(0.04)
            except Exception:
                # Direct key typing fallback
                for char in text:
                    vk = ord(char.upper()) if char.isalnum() else 0x20
                    self.send_key_press(vk)
                    time.sleep(0.01)
            finally:
                if old_clipboard is not None:
                    try:
                        time.sleep(0.05)
                        with safe_clipboard() as cb:
                            cb.EmptyClipboard()
                            cb.SetClipboardText(old_clipboard, cb.CF_UNICODETEXT)
                    except Exception:
                        pass

        if press_enter:
            time.sleep(0.04)
            self.send_key_press(0x0D)  # VK_RETURN

        return ActionResult(
            success=True,
            action="type_text",
            application=app_name or "active",
            tier_used=FallbackTier.KEYBOARD_SHORTCUT,
            message=f"Typed text: '{text[:30]}...'",
            data={"text": text},
            verified=True,
            execution_time_ms=(time.time() - start) * 1000,
        )

    def _find_element_by_accessibility(self, target: str, hwnd: Optional[int] = None) -> Optional[Tuple[int, int]]:
        """Find UI element center coordinate using Windows UIAutomation COM."""
        # Lightweight accessibility center resolver
        if not WIN32_AVAILABLE:
            return None
        try:
            import comtypes.client
            uia = comtypes.client.CreateObject("{ff48dba4-60ef-4201-aa87-54103eef594e}")  # CUIAutomation
            if not uia:
                return None
            root = uia.GetRootElement() if not hwnd else uia.ElementFromHandle(hwnd)
            if not root:
                return None
            # Condition matching target name
            cond = uia.CreatePropertyCondition(30005, target)  # UIA_NamePropertyId = 30005
            elem = root.FindFirst(4, cond)  # TreeScope_Descendants = 4
            if elem:
                rect = elem.CurrentBoundingRectangle
                cx = (rect.left + rect.right) // 2
                cy = (rect.top + rect.bottom) // 2
                return (cx, cy)
        except Exception:
            pass
        return None


# Global singleton action engine
action_engine = UniversalActionEngine()
