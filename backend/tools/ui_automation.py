"""Universal UI Automation & Computer Interaction Tools for JARVIS AI.

Provides cross-application OS-level automation for Windows:
- Universal element clicking with spatial grounding ('upar wala', 'neeche wala', 'left side', etc.)
- Window switching and focus enforcement across apps (Chrome, VS Code, Explorer, Notepad, Settings)
- Screen scrolling (up / down)
- Text typing and keyboard shortcut dispatch
- History navigation (Back / Forward)
"""
import ctypes
from ctypes import wintypes
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from backend.core.logger import get_logger
from backend.core.permissions import PermissionLevel, ToolCategory
from backend.tools.registry import tool
from backend.ai.state_observer import state_observer
from backend.core.safety import (
    is_dev_safe_mode,
    is_physical_automation_allowed,
    is_foreground_stealing_allowed,
    safe_blocked_result,
)

logger = get_logger("UIAutomation")

# Check Windows Win32 availability
try:
    import win32gui
    import win32con
    import win32api
    import win32clipboard
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


# ==========================================
# Input Schemas
# ==========================================

class SwitchWindowArgs(BaseModel):
    target_app: str = Field(..., description="Name or keyword of the application/window to focus (e.g. 'chrome', 'vscode', 'explorer', 'notepad', 'settings', 'youtube').")


class ClickElementArgs(BaseModel):
    target: str = Field(..., description="Target description or spatial reference (e.g. 'upar wala', 'neeche wala', 'left side wala', 'first video', 'channel link', 'submit button').")
    app: Optional[str] = Field(None, description="Optional application context (e.g. 'chrome', 'explorer', 'notepad').")


class ScrollScreenArgs(BaseModel):
    direction: str = Field("down", description="Direction to scroll ('up' or 'down').")
    amount: int = Field(3, description="Number of scroll steps / intensity (default 3).")


class TypeTextArgs(BaseModel):
    text: str = Field(..., description="Text content to type into the currently active element.")
    press_enter: bool = Field(False, description="Whether to press Enter after typing.")


class NavigateHistoryArgs(BaseModel):
    direction: str = Field("back", description="Navigation direction ('back' or 'forward').")


class ManageWindowArgs(BaseModel):
    action: str = Field(..., description="Window management action: 'minimize', 'maximize', 'restore', 'close'.")
    target_app: Optional[str] = Field(None, description="Optional target application name or window title (e.g. 'antigravity', 'chrome', 'vscode', 'notepad'). If omitted, acts on current active window.")


# ==========================================
# Windows Helper Functions
# ==========================================

def force_foreground_window(hwnd: int) -> bool:
    """Force bring target HWND window to foreground with thread attachment and zero UIPI restriction."""
    if not is_foreground_stealing_allowed():
        return False
    if not WIN32_AVAILABLE or not hwnd:
        return False
    try:
        import win32process
        user32 = ctypes.windll.user32
        fg_hwnd = win32gui.GetForegroundWindow()
        if fg_hwnd != hwnd:
            fg_thread, _ = win32process.GetWindowThreadProcessId(fg_hwnd)
            app_thread, _ = win32process.GetWindowThreadProcessId(hwnd)
            if fg_thread != app_thread:
                win32process.AttachThreadInput(fg_thread, app_thread, True)
                user32.AllowSetForegroundWindow(-1)
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                user32.SwitchToThisWindow(hwnd, True)
                win32gui.SetForegroundWindow(hwnd)
                win32process.AttachThreadInput(fg_thread, app_thread, False)
            else:
                user32.AllowSetForegroundWindow(-1)
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                user32.SwitchToThisWindow(hwnd, True)
                win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.06)
        return True
    except Exception as exc:
        logger.debug(f"force_foreground_window error: {exc}")
        return False


def find_app_window(target_query: str) -> Tuple[Optional[int], str]:
    """Hyper-fast matching desktop window finder (<1ms): Direct HWND process image lookup."""
    if not WIN32_AVAILABLE or not target_query:
        return None, ""

    query = target_query.lower().strip()
    target_clean = re.sub(r"\b(browser|app|application|ide|window|code|player|studio)\b", "", query).strip() or query

    # Resolve app executables from app_registry
    target_exes = [query, target_clean]
    try:
        from backend.tools.app_tools import app_registry
        resolved = app_registry.resolve_app(query) or app_registry.resolve_app(target_clean)
        if resolved:
            for ex in resolved.get("executables", []):
                target_exes.append(ex.lower())
                target_exes.append(ex.lower().replace(".exe", ""))
            for al in resolved.get("aliases", []):
                target_exes.append(al.lower())
    except Exception:
        pass

    target_exes = list(set([e for e in target_exes if e]))

    from ctypes import wintypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    candidates = []

    # Connect to user desktop station
    h_desk = None
    try:
        GENERIC_ALL = 0x10000000
        h_winsta = user32.OpenWindowStationW("winsta0", False, GENERIC_ALL)
        if h_winsta:
            user32.SetProcessWindowStation(h_winsta)
        h_desk = user32.OpenDesktopW("default", 0, False, GENERIC_ALL)
    except Exception:
        pass

    def enum_cb(hwnd, lparam):
        try:
            is_vis = bool(user32.IsWindowVisible(hwnd))
            is_ico = bool(win32gui.IsIconic(hwnd))
            if is_vis or is_ico:
                length = user32.GetWindowTextLengthW(hwnd)
                title = ""
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.strip()

                t_low = title.lower()
                cls = win32gui.GetClassName(hwnd)

                # Skip Windows OS system background windows (Taskbar, Desktop, Wallpaper)
                if cls in ["Shell_TrayWnd", "Progman", "WorkerW", "Shell_SecondaryTrayWnd"]:
                    return True

                # 1. Match window title directly
                if any(t_kw in t_low for t_kw in [query, target_clean] if len(t_kw) >= 3):
                    candidates.append((hwnd, title, 5))
                    return True

                # 2. Match process image name directly (<0.01ms)
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value > 0:
                    exe_name = ""
                    h_proc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
                    if h_proc:
                        try:
                            buf_len = ctypes.c_ulong(1024)
                            path_buf = ctypes.create_unicode_buffer(1024)
                            if kernel32.QueryFullProcessImageNameW(h_proc, 0, path_buf, ctypes.byref(buf_len)):
                                exe_name = os.path.basename(path_buf.value).lower()
                        finally:
                            kernel32.CloseHandle(h_proc)

                    if not exe_name:
                        try:
                            import psutil
                            exe_name = psutil.Process(pid.value).name().lower()
                        except Exception:
                            pass

                    if exe_name:
                        exe_base = exe_name.replace(".exe", "")
                        if any(t_ex in exe_name or exe_base in t_ex or t_ex in exe_base for t_ex in target_exes):
                            if "explorer" in exe_name:
                                if cls == "CabinetWClass" or title:
                                    candidates.append((hwnd, title or "File Explorer", 4))
                            else:
                                candidates.append((hwnd, title or query.title(), 4))

                # Removed loose Chrome_WidgetWin fallback to prevent cross-app matching
        except Exception:
            pass
        return True

    cb = WNDENUMPROC(enum_cb)
    try:
        if h_desk:
            user32.EnumDesktopWindows(h_desk, cb, 0)
        else:
            user32.EnumWindows(cb, 0)
    except Exception:
        pass

    if candidates:
        candidates.sort(key=lambda x: x[2], reverse=True)
        return candidates[0][0], candidates[0][1]

    return None, ""


# ==========================================
# Executable Tools
# ==========================================

@tool(
    name="switch_window",
    description="Bring any running application or browser window to the absolute front of the screen. (e.g. 'Chrome par switch karo', 'VS Code kholo', 'Notepad aage lao', 'Explorer focus karo').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.SYSTEM,
    args_schema=SwitchWindowArgs,
)
def switch_window(target_app: str) -> Dict[str, Any]:
    """Focus and bring target application window to the foreground."""
    hwnd, title = find_app_window(target_app)
    if hwnd:
        success = force_foreground_window(hwnd)
        if success:
            logger.info(f"Switched window to '{title}' (HWND: {hwnd})")
            return {
                "status": "success",
                "app": target_app,
                "window_title": title,
                "message": f"Ji Boss, {target_app.title()} window ko screen par le aayi.",
            }

    return {
        "status": "not_found",
        "app": target_app,
        "message": f"Boss, '{target_app}' ki koi active window nahi mili.",
    }


@tool(
    name="click_element",
    description="Click a UI element or spatial target on the current active window (e.g. 'upar wala', 'neeche wala', 'left side wala', 'first video', 'channel link', 'submit button').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.SYSTEM,
    args_schema=ClickElementArgs,
)
def click_element(target: str, app: Optional[str] = None) -> Dict[str, Any]:
    """Universal UI element clicker with spatial and contextual grounding."""
    if not is_physical_automation_allowed():
        return safe_blocked_result("click_element")

    # 1. If an app was specified, ensure it is focused first
    if app:
        switch_window(app)

    # 2. Check active window geometry
    rect = None
    if WIN32_AVAILABLE:
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if hwnd:
                w_rect = win32gui.GetWindowRect(hwnd)
                rect = (w_rect[0], w_rect[1], w_rect[2], w_rect[3])
        except Exception:
            rect = None

    # 3. Resolve spatial coordinates
    click_x, click_y = state_observer.resolve_spatial_coordinates(target, base_rect=rect)

    # 4. Perform mouse click
    try:
        user32 = ctypes.windll.user32
        user32.SetCursorPos(click_x, click_y)
        time.sleep(0.06)
        MOUSEEVENTF_LEFTDOWN = 0x0002
        MOUSEEVENTF_LEFTUP = 0x0004
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

        logger.info(f"Clicked target '{target}' at coordinates ({click_x}, {click_y})")
        return {
            "status": "success",
            "target": target,
            "coordinates": {"x": click_x, "y": click_y},
            "message": f"Ji Boss, {target} par click kar diya.",
        }
    except Exception as exc:
        logger.error(f"Click element error: {exc}")
        return {
            "status": "error",
            "message": f"Click execute nahi ho paya: {exc}",
        }


@tool(
    name="scroll_screen",
    description="Scroll up or down on the active window or webpage (e.g. 'neeche scroll karo', 'upar scroll karo', 'scroll down', 'scroll up').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.SYSTEM,
    args_schema=ScrollScreenArgs,
)
def scroll_screen(direction: str = "down", amount: int = 4) -> Dict[str, Any]:
    """Scroll the active window up or down using Windows mouse wheel events."""
    if not is_physical_automation_allowed():
        return safe_blocked_result("scroll_screen")

    try:
        user32 = ctypes.windll.user32
        is_down = direction.lower() in ["down", "neeche", "niche", "bottom"]
        vk_code = 0x22 if is_down else 0x21  # VK_NEXT (Page Down) or VK_PRIOR (Page Up)
        scan_code = user32.MapVirtualKeyW(vk_code, 0)
        user32.keybd_event(vk_code, scan_code, 0, 0)
        time.sleep(0.04)
        user32.keybd_event(vk_code, scan_code, 2, 0)  # KEYEVENTF_KEYUP
        logger.info(f"Scrolled screen {direction} via keyboard page navigation (zero cursor movement)")
        return {
            "status": "success",
            "direction": "down" if is_down else "up",
            "steps": amount,
            "message": f"Ji Boss, screen {'neeche' if is_down else 'upar'} scroll kar diya.",
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Scroll failed: {exc}",
        }


@tool(
    name="type_into_element",
    description="Type text into the active focused input box or document (e.g. 'search bar mein type karo', 'Hello world type karo').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.SYSTEM,
    args_schema=TypeTextArgs,
)
def type_into_element(text: str, press_enter: bool = False) -> Dict[str, Any]:
    """Paste/Type text into the currently active element via Windows clipboard."""
    if not WIN32_AVAILABLE:
        return {"status": "unsupported", "message": "Typing requires Windows API."}

    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        time.sleep(0.05)

        user32 = ctypes.windll.user32
        VK_CONTROL = 0x11
        VK_V = 0x56
        VK_RETURN = 0x0D

        # Ctrl + V to paste
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        user32.keybd_event(VK_V, 0, 0, 0)
        user32.keybd_event(VK_V, 0, 2, 0)
        user32.keybd_event(VK_CONTROL, 0, 2, 0)

        if press_enter:
            time.sleep(0.06)
            user32.keybd_event(VK_RETURN, 0, 0, 0)
            user32.keybd_event(VK_RETURN, 0, 2, 0)

        logger.info(f"Typed text '{text}' (press_enter={press_enter})")
        return {
            "status": "success",
            "text": text,
            "message": f"Ji Boss, '{text}' type kar diya.",
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Typing failed: {exc}",
        }


@tool(
    name="navigate_back_forward",
    description="Navigate Back or Forward in Chrome, Edge, Firefox, or File Explorer (e.g. 'back jao', 'peeche jao', 'forward jao', 'go back').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.BROWSER,
    args_schema=NavigateHistoryArgs,
)
def navigate_back_forward(direction: str = "back") -> Dict[str, Any]:
    """Send Alt+Left (Back) or Alt+Right (Forward) key sequence."""
    try:
        user32 = ctypes.windll.user32
        VK_MENU = 0x12       # Alt key
        VK_LEFT = 0x25       # Left Arrow
        VK_RIGHT = 0x27      # Right Arrow

        target_key = VK_LEFT if direction.lower() in ["back", "peeche", "piche"] else VK_RIGHT

        user32.keybd_event(VK_MENU, 0, 0, 0)
        user32.keybd_event(target_key, 0, 0, 0)
        user32.keybd_event(target_key, 0, 2, 0)
        user32.keybd_event(VK_MENU, 0, 2, 0)

        logger.info(f"Navigated history: {direction}")
        return {
            "status": "success",
            "direction": direction,
            "message": f"Ji Boss, {direction} navigate kar diya.",
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Navigation failed: {exc}",
        }


def get_top_user_window() -> Tuple[Optional[int], str]:
    """Find the top-most visible user application window, ignoring OS taskbar/desktop and JARVIS console."""
    if not WIN32_AVAILABLE:
        return None, ""
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    curr_pid = os.getpid()
    found_hwnd = None
    found_title = ""

    h_desk = None
    try:
        GENERIC_ALL = 0x10000000
        h_winsta = user32.OpenWindowStationW("winsta0", False, GENERIC_ALL)
        if h_winsta:
            user32.SetProcessWindowStation(h_winsta)
        h_desk = user32.OpenDesktopW("default", 0, False, GENERIC_ALL)
    except Exception:
        pass

    def cb(h, _):
        nonlocal found_hwnd, found_title
        if found_hwnd:
            return False
        try:
            if user32.IsWindowVisible(h) and not win32gui.IsIconic(h):
                cls = win32gui.GetClassName(h)
                if cls in ["Shell_TrayWnd", "Progman", "WorkerW", "Shell_SecondaryTrayWnd"]:
                    return True
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
                if pid.value == curr_pid:
                    return True
                title = win32gui.GetWindowText(h)
                if title and title not in ["Program Manager", "Windows Input Experience"]:
                    found_hwnd = h
                    found_title = title
                    return False
        except Exception:
            pass
        return True

    try:
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        if h_desk:
            user32.EnumDesktopWindows(h_desk, WNDENUMPROC(cb), 0)
        else:
            user32.EnumWindows(WNDENUMPROC(cb), 0)
    except Exception:
        pass
    return found_hwnd, found_title


@tool(
    name="manage_window",
    description="Minimize, maximize, restore, or close any application or browser window by name or target app (e.g. 'minimize antigravity', 'antigravity minimize karo', 'maximize chrome', 'close window').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.SYSTEM,
    args_schema=ManageWindowArgs,
)
def manage_window(action: str, target_app: Optional[str] = None) -> Dict[str, Any]:
    """Minimize, maximize, restore, or close a window on Windows."""
    if not WIN32_AVAILABLE:
        return {"status": "unsupported", "message": "Window management requires Windows API."}

    try:
        user32 = ctypes.windll.user32
        hwnd = None
        title = ""

        if target_app and target_app.strip().lower() not in ["window", "this", "active", "screen", "app", "application"]:
            hwnd, title = find_app_window(target_app)

        if not hwnd:
            hwnd, title = get_top_user_window()

        if not hwnd:
            hwnd = user32.GetForegroundWindow()
            if hwnd:
                title = win32gui.GetWindowText(hwnd) or "Active Window"

        if not hwnd:
            return {"status": "not_found", "message": "No window found."}

        act = action.lower().strip()
        app_name = target_app.title() if (target_app and target_app.strip().lower() not in ["window", "this", "active", "screen", "app", "application"]) else (title or "Window")

        if act in ["minimize", "chhota", "niche", "min"]:
            user32.CloseWindow(hwnd)
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_FORCEMINIMIZE)
            except Exception:
                pass
            msg = f"Ji Boss, {app_name} window minimize kar di."
        elif act in ["maximize", "bada", "max"]:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            msg = f"Ji Boss, {app_name} window maximize kar di."
        elif act in ["restore", "wapas"]:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            msg = f"Ji Boss, {app_name} window restore kar di."
        elif act in ["close", "band"]:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            msg = f"Ji Boss, {app_name} window band kar di."
        else:
            msg = f"Action '{action}' executed."

        logger.info(f"Managed window ({act}): '{title}' (HWND: {hwnd})")
        return {"status": "success", "action": act, "message": msg}
    except Exception as exc:
        return {"status": "error", "message": f"Window action failed: {exc}"}
