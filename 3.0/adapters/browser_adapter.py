"""JARVIS 3.0 - Browser Adapter.

Provides resilient browser window control, tab management, in-place navigation,
and web search for Google Chrome, Microsoft Edge, and default Windows browsers.
"""
import ctypes
import os
import subprocess
import time
import urllib.parse
import webbrowser
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from adapters.base_adapter import BaseAdapter
from core.logger import get_logger
from core.models import PermissionLevel, PermissionType, ToolCategory, ToolExecutionResult
from core.tool_contract import FunctionalTool
from core.tool_registry import ToolRegistry, default_registry

logger = get_logger("BrowserAdapter")

try:
    import win32api
    import win32con
    import win32gui
    import win32process
    import win32clipboard
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


class OpenUrlArgs(BaseModel):
    url: str = Field(..., description="Target URL to open (e.g. 'https://github.com')")


class SearchWebArgs(BaseModel):
    query: str = Field(..., description="Search query string")
    engine: str = Field(default="google", description="Search engine: 'google', 'duckduckgo', 'bing'")


class BrowserAdapter(BaseAdapter):
    """Encapsulates all web browser interactions."""

    def __init__(self):
        super().__init__(name="browser", category=ToolCategory.BROWSER)

    def register_tools(self, registry: Optional[ToolRegistry] = None) -> None:
        reg = registry or default_registry

        # 1. browser.open
        reg.register(FunctionalTool(
            name="browser.open",
            description="Open a website URL in Google Chrome or active browser.",
            category=ToolCategory.BROWSER,
            func=self.open_url,
            permission_level=PermissionLevel.LEVEL_1_NORMAL,
            required_permissions=[PermissionType.BROWSER_AUTOMATION],
            parameters_schema=OpenUrlArgs,
        ))

        # 2. browser.close_tab
        reg.register(FunctionalTool(
            name="browser.close_tab",
            description="Close the active browser tab or window (Ctrl+W).",
            category=ToolCategory.BROWSER,
            func=self.close_active_tab,
            permission_level=PermissionLevel.LEVEL_1_NORMAL,
            required_permissions=[PermissionType.BROWSER_AUTOMATION],
        ))

        # 3. browser.search_web
        reg.register(FunctionalTool(
            name="browser.search_web",
            description="Search the web using Google, Bing, or DuckDuckGo.",
            category=ToolCategory.SEARCH,
            func=self.search_web,
            permission_level=PermissionLevel.LEVEL_1_NORMAL,
            required_permissions=[PermissionType.BROWSER_AUTOMATION],
            parameters_schema=SearchWebArgs,
        ))

        self.is_initialized = True
        logger.info("Registered BrowserAdapter tools: browser.open, browser.close_tab, browser.search_web")

    def get_application_state(self) -> Dict[str, Any]:
        """Inspect if browser window is open and which tab is active."""
        hwnd, title = self.find_browser_window()
        return {
            "browser_open": hwnd is not None,
            "active_window_title": title,
            "hwnd": hwnd,
        }

    def find_browser_window(self, keyword: str = "") -> tuple[Optional[int], str]:
        """Find the active Google Chrome or Edge window."""
        if not WIN32_AVAILABLE:
            return None, ""
        matched = []

        def enum_cb(hwnd, extra):
            try:
                if win32gui.IsWindowVisible(hwnd):
                    t = win32gui.GetWindowText(hwnd).lower()
                    c = win32gui.GetClassName(hwnd)
                    # Exclude IDEs and coding editors
                    if any(ex in t for ex in ["antigravity", "vscode", "visual studio", "cmd.exe", "powershell"]):
                        return
                    if any(b in t or b in c.lower() for b in ["chrome", "edge", "brave", "firefox", "youtube"]):
                        if not keyword or keyword.lower() in t:
                            extra.append((hwnd, win32gui.GetWindowText(hwnd)))
            except Exception:
                pass

        try:
            win32gui.EnumWindows(enum_cb, matched)
            if matched:
                return matched[0]
        except Exception:
            pass
        return None, ""

    def force_foreground(self, hwnd: int) -> bool:
        """Bring target window to the front bypassing Windows foreground lock."""
        if not WIN32_AVAILABLE or not hwnd:
            return False
        try:
            user32 = ctypes.windll.user32
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            else:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

            fore_hwnd = win32gui.GetForegroundWindow()
            cur_thread = win32api.GetCurrentThreadId()
            target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)

            if fore_hwnd != hwnd:
                if cur_thread != target_thread:
                    user32.AttachThreadInput(cur_thread, target_thread, True)

                user32.keybd_event(0x12, 0, 0, 0)  # Alt down
                user32.keybd_event(0x12, 0, 2, 0)  # Alt up
                user32.AllowSetForegroundWindow(-1)
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)

                if cur_thread != target_thread:
                    user32.AttachThreadInput(cur_thread, target_thread, False)

            time.sleep(0.06)
            return True
        except Exception as exc:
            logger.debug(f"force_foreground error: {exc}")
            return False

    def navigate_active_tab(self, url: str) -> bool:
        """Navigate the currently active Chrome/Edge tab to target URL in-place."""
        hwnd, title = self.find_browser_window()
        if not hwnd:
            return False

        self.force_foreground(hwnd)
        time.sleep(0.08)

        if not WIN32_AVAILABLE:
            return False

        try:
            user32 = ctypes.windll.user32
            VK_CONTROL = 0x11
            VK_L = 0x4C
            VK_V = 0x56
            VK_RETURN = 0x0D

            # 1. Ctrl + L to focus address bar
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(VK_L, 0, 0, 0)
            time.sleep(0.03)
            user32.keybd_event(VK_L, 0, 2, 0)
            user32.keybd_event(VK_CONTROL, 0, 2, 0)
            time.sleep(0.06)

            # 2. Put URL on clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(url, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            time.sleep(0.03)

            # 3. Ctrl + V to paste
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(VK_V, 0, 0, 0)
            time.sleep(0.03)
            user32.keybd_event(VK_V, 0, 2, 0)
            user32.keybd_event(VK_CONTROL, 0, 2, 0)
            time.sleep(0.04)

            # 4. Press Enter
            user32.keybd_event(VK_RETURN, 0, 0, 0)
            time.sleep(0.03)
            user32.keybd_event(VK_RETURN, 0, 2, 0)

            logger.info(f"Navigated active browser tab to: {url}")
            return True
        except Exception as exc:
            logger.debug(f"navigate_active_tab exception: {exc}")
            return False

    def launch_browser(self, url: str) -> None:
        """Launch Google Chrome full-screen maximized."""
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
        for p in chrome_paths:
            if os.path.exists(p):
                try:
                    subprocess.Popen([p, "--start-maximized", url])
                    return
                except Exception:
                    pass

        # Fallback to start command or webbrowser
        try:
            subprocess.Popen(f'start chrome --start-maximized "{url}"', shell=True)
        except Exception:
            webbrowser.open(url, new=0, autoraise=True)

    async def open_url(self, url: str) -> ToolExecutionResult:
        """Open a website URL in Google Chrome or default browser."""
        clean_url = url.strip()
        if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
            clean_url = f"https://{clean_url}"

        logger.info(f"Opening browser URL: {clean_url}")
        try:
            subprocess.Popen(["cmd", "/c", "start", "chrome", clean_url])
        except Exception:
            webbrowser.open_new_tab(clean_url)

        return ToolExecutionResult(
            success=True,
            data={"url": clean_url, "mode": "browser_opened"},
            message=f"Ji Boss, {clean_url} open kar diya.",
            strategy_used="launch_browser",
        )

    async def close_active_tab(self) -> ToolExecutionResult:
        """Close the active browser tab via Ctrl+W."""
        hwnd, title = self.find_browser_window()
        if hwnd:
            self.force_foreground(hwnd)
            time.sleep(0.08)

        if WIN32_AVAILABLE:
            user32 = ctypes.windll.user32
            VK_CONTROL = 0x11
            VK_W = 0x57
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(VK_W, 0, 0, 0)
            time.sleep(0.04)
            user32.keybd_event(VK_W, 0, 2, 0)
            user32.keybd_event(VK_CONTROL, 0, 2, 0)

            return ToolExecutionResult(
                success=True,
                message="Ji Boss, active browser tab close kar diya.",
            )
        return ToolExecutionResult(
            success=False,
            error="Tab closing requires Windows API.",
        )

    async def search_web(self, query: str, engine: str = "google") -> ToolExecutionResult:
        """Search the web with query."""
        encoded = urllib.parse.quote_plus(query.strip())
        eng = engine.lower()
        if eng == "duckduckgo":
            target_url = f"https://duckduckgo.com/?q={encoded}"
        elif eng == "bing":
            target_url = f"https://www.bing.com/search?q={encoded}"
        else:
            target_url = f"https://www.google.com/search?q={encoded}"

        return await self.open_url(target_url)


browser_adapter = BrowserAdapter()
