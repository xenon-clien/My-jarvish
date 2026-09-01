"""JARVIS 3.0 - Dedicated Google Chrome Application Adapter.

Provides tab management, page navigation, zoom controls, history,
bookmarks, downloads inspection, and in-page search for Google Chrome.
"""
import ctypes
import os
import subprocess
import time
import urllib.parse
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from adapters.base_adapter import BaseAdapter
from adapters.browser_adapter import browser_adapter
from adapters.download_manager import download_manager
from core.logger import get_logger
from core.models import PermissionLevel, PermissionType, ToolCategory, ToolExecutionResult
from core.tool_contract import FunctionalTool
from core.tool_registry import ToolRegistry, default_registry

logger = get_logger("ChromeAdapter")

try:
    import win32api
    import win32con
    import win32gui
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


class ChromeSearchArgs(BaseModel):
    query: str = Field(..., description="Query to search on Google Chrome.")


class ChromeFindArgs(BaseModel):
    text: str = Field(..., description="Text to find on the active web page.")


class ChromeTabSwitchArgs(BaseModel):
    tab_index: int = Field(default=1, ge=1, le=9, description="Tab index from 1 to 9.")


class ChromeAdapter(BaseAdapter):
    """Encapsulates Google Chrome desktop browser automation."""

    def __init__(self):
        super().__init__(name="chrome", category=ToolCategory.BROWSER)

    def register_tools(self, registry: Optional[ToolRegistry] = None) -> None:
        reg = registry or default_registry

        # 1. chrome.open
        reg.register(self._make_tool("chrome.open", "Open Google Chrome browser.", self.open_chrome))

        # 2. chrome.new_tab
        reg.register(self._make_tool("chrome.new_tab", "Open a new tab in Chrome (Ctrl+T).", self.new_tab))

        # 3. chrome.close_tab
        reg.register(self._make_tool("chrome.close_tab", "Close the active tab in Chrome (Ctrl+W).", self.close_tab))

        # 4. chrome.next_tab
        reg.register(self._make_tool("chrome.next_tab", "Switch to the next tab in Chrome (Ctrl+Tab).", self.next_tab))

        # 5. chrome.previous_tab
        reg.register(self._make_tool("chrome.previous_tab", "Switch to the previous tab in Chrome (Ctrl+Shift+Tab).", self.prev_tab))

        # 6. chrome.switch_tab
        reg.register(self._make_tool("chrome.switch_tab", "Switch to tab by index 1-9 in Chrome.", self.switch_tab, parameters_schema=ChromeTabSwitchArgs))

        # 7. chrome.reopen_closed_tab
        reg.register(self._make_tool("chrome.reopen_closed_tab", "Reopen the last closed tab in Chrome (Ctrl+Shift+T).", self.reopen_closed_tab))

        # 8. chrome.refresh
        reg.register(self._make_tool("chrome.refresh", "Refresh the active web page (Ctrl+R).", self.refresh_page))

        # 9. chrome.back
        reg.register(self._make_tool("chrome.back", "Navigate back in browser history (Alt+Left).", self.go_back))

        # 10. chrome.forward
        reg.register(self._make_tool("chrome.forward", "Navigate forward in browser history (Alt+Right).", self.go_forward))

        # 11. chrome.zoom_in
        reg.register(self._make_tool("chrome.zoom_in", "Zoom in on the active web page (Ctrl+Plus).", self.zoom_in))

        # 12. chrome.zoom_out
        reg.register(self._make_tool("chrome.zoom_out", "Zoom out on the active web page (Ctrl+Minus).", self.zoom_out))

        # 13. chrome.reset_zoom
        reg.register(self._make_tool("chrome.reset_zoom", "Reset page zoom to 100% (Ctrl+0).", self.reset_zoom))

        # 14. chrome.find_on_page
        reg.register(self._make_tool("chrome.find_on_page", "Search for text on active web page (Ctrl+F).", self.find_on_page, parameters_schema=ChromeFindArgs))

        # 15. chrome.open_incognito
        reg.register(self._make_tool("chrome.open_incognito", "Open a new Incognito window (Ctrl+Shift+N).", self.open_incognito))

        # 16. chrome.open_history
        reg.register(self._make_tool("chrome.open_history", "Open Chrome browsing history (Ctrl+H).", self.open_history))

        # 17. chrome.open_bookmarks
        reg.register(self._make_tool("chrome.open_bookmarks", "Open Chrome bookmarks manager (Ctrl+Shift+O).", self.open_bookmarks))

        # 18. chrome.open_downloads
        reg.register(self._make_tool("chrome.open_downloads", "Open Chrome downloads page (Ctrl+J).", self.open_downloads_page))

        # 19. downloads.status
        reg.register(self._make_tool("downloads.status", "Check status of recent and active browser downloads.", self.check_downloads_status))

        # 20. downloads.last_downloaded
        reg.register(self._make_tool("downloads.last_downloaded", "Locate and report the most recently downloaded file.", self.get_last_download))

        # 21. downloads.open_folder
        reg.register(self._make_tool("downloads.open_folder", "Open the user Downloads folder in File Explorer.", self.open_downloads_folder))

        self.is_initialized = True
        logger.info("Registered ChromeAdapter 21 tools.")

    def _make_tool(self, name: str, desc: str, func: Any, parameters_schema: Optional[type] = None) -> FunctionalTool:
        return FunctionalTool(
            name=name,
            description=desc,
            category=ToolCategory.BROWSER,
            func=func,
            permission_level=PermissionLevel.LEVEL_1_NORMAL,
            required_permissions=[PermissionType.BROWSER_AUTOMATION],
            parameters_schema=parameters_schema,
            dependencies=["browser"],
        )

    def get_application_state(self) -> Dict[str, Any]:
        return browser_adapter.get_application_state()

    def _focus_chrome(self) -> bool:
        hwnd, _ = browser_adapter.find_browser_window("chrome")
        if not hwnd:
            hwnd, _ = browser_adapter.find_browser_window()
        if hwnd:
            return browser_adapter.force_foreground(hwnd)
        return False

    def _send_shortcut(self, *vk_keys: int) -> None:
        if not WIN32_AVAILABLE:
            return
        user32 = ctypes.windll.user32
        for k in vk_keys:
            user32.keybd_event(k, 0, 0, 0)
        time.sleep(0.04)
        for k in reversed(vk_keys):
            user32.keybd_event(k, 0, 2, 0)

    # ── TOOL METHODS ──────────────────────────────────────────────────────────
    async def open_chrome(self) -> ToolExecutionResult:
        return await browser_adapter.open_url("https://www.google.com")

    async def new_tab(self) -> ToolExecutionResult:
        self._focus_chrome()
        self._send_shortcut(0x11, 0x54)  # Ctrl + T
        return ToolExecutionResult(success=True, message="Ji Boss, Chrome mein new tab open kar diya.")

    async def close_tab(self) -> ToolExecutionResult:
        return await browser_adapter.close_active_tab()

    async def next_tab(self) -> ToolExecutionResult:
        self._focus_chrome()
        self._send_shortcut(0x11, 0x09)  # Ctrl + Tab
        return ToolExecutionResult(success=True, message="Ji Boss, agle tab par switch kar diya.")

    async def prev_tab(self) -> ToolExecutionResult:
        self._focus_chrome()
        self._send_shortcut(0x11, 0x10, 0x09)  # Ctrl + Shift + Tab
        return ToolExecutionResult(success=True, message="Ji Boss, pichle tab par switch kar diya.")

    async def switch_tab(self, tab_index: int = 1) -> ToolExecutionResult:
        self._focus_chrome()
        vk_digit = 0x30 + min(9, max(1, tab_index))  # '1' to '9'
        self._send_shortcut(0x11, vk_digit)
        return ToolExecutionResult(success=True, message=f"Ji Boss, tab #{tab_index} par switch kar diya.")

    async def reopen_closed_tab(self) -> ToolExecutionResult:
        self._focus_chrome()
        self._send_shortcut(0x11, 0x10, 0x54)  # Ctrl + Shift + T
        return ToolExecutionResult(success=True, message="Ji Boss, closed tab reopen kar diya.")

    async def refresh_page(self) -> ToolExecutionResult:
        self._focus_chrome()
        self._send_shortcut(0x74)  # F5
        return ToolExecutionResult(success=True, message="Ji Boss, page refresh kar diya.")

    async def go_back(self) -> ToolExecutionResult:
        self._focus_chrome()
        self._send_shortcut(0x12, 0x25)  # Alt + Left
        return ToolExecutionResult(success=True, message="Ji Boss, back navigate kiya.")

    async def go_forward(self) -> ToolExecutionResult:
        self._focus_chrome()
        self._send_shortcut(0x12, 0x27)  # Alt + Right
        return ToolExecutionResult(success=True, message="Ji Boss, forward navigate kiya.")

    async def zoom_in(self) -> ToolExecutionResult:
        self._focus_chrome()
        self._send_shortcut(0x11, 0xBB)  # Ctrl + Plus
        return ToolExecutionResult(success=True, message="Ji Boss, zoom in kiya.")

    async def zoom_out(self) -> ToolExecutionResult:
        self._focus_chrome()
        self._send_shortcut(0x11, 0xBD)  # Ctrl + Minus
        return ToolExecutionResult(success=True, message="Ji Boss, zoom out kiya.")

    async def reset_zoom(self) -> ToolExecutionResult:
        self._focus_chrome()
        self._send_shortcut(0x11, 0x30)  # Ctrl + 0
        return ToolExecutionResult(success=True, message="Ji Boss, zoom reset kar diya.")

    async def find_on_page(self, text: str) -> ToolExecutionResult:
        self._focus_chrome()
        self._send_shortcut(0x11, 0x46)  # Ctrl + F
        time.sleep(0.08)
        # Paste search text
        if WIN32_AVAILABLE:
            import win32clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            self._send_shortcut(0x11, 0x56)  # Ctrl + V
            self._send_shortcut(0x0D)        # Enter
        return ToolExecutionResult(success=True, message=f"Ji Boss, page par '{text}' search kiya.")

    async def open_incognito(self) -> ToolExecutionResult:
        self._focus_chrome()
        self._send_shortcut(0x11, 0x10, 0x4E)  # Ctrl + Shift + N
        return ToolExecutionResult(success=True, message="Ji Boss, Incognito window open kar di.")

    async def open_history(self) -> ToolExecutionResult:
        self._focus_chrome()
        self._send_shortcut(0x11, 0x48)  # Ctrl + H
        return ToolExecutionResult(success=True, message="Ji Boss, browsing history open kar di.")

    async def open_bookmarks(self) -> ToolExecutionResult:
        self._focus_chrome()
        self._send_shortcut(0x11, 0x10, 0x4F)  # Ctrl + Shift + O
        return ToolExecutionResult(success=True, message="Ji Boss, bookmarks open kar diye.")

    async def open_downloads_page(self) -> ToolExecutionResult:
        self._focus_chrome()
        self._send_shortcut(0x11, 0x4A)  # Ctrl + J
        return ToolExecutionResult(success=True, message="Ji Boss, Chrome downloads open kar diye.")

    # ── DOWNLOAD SYSTEM HELPERS ───────────────────────────────────────────────
    async def check_downloads_status(self) -> ToolExecutionResult:
        active = download_manager.get_active_downloads()
        if active:
            names = ", ".join([d.filename for d in active])
            return ToolExecutionResult(
                success=True,
                data={"active_downloads": [d.model_dump() for d in active]},
                message=f"Boss, abhi {len(active)} files download ho rahi hain: {names}.",
            )
        last = download_manager.get_last_downloaded_file()
        if last:
            return ToolExecutionResult(
                success=True,
                data={"last_file": last.model_dump()},
                message=f"Boss, koi active download nahi hai. Last download: '{last.filename}' ({last.size_mb} MB).",
            )
        return ToolExecutionResult(success=True, message="Boss, Downloads folder mein koi active file download nahi ho rahi hai.")

    async def get_last_download(self) -> ToolExecutionResult:
        last = download_manager.get_last_downloaded_file()
        if not last:
            return ToolExecutionResult(success=False, error="Koi downloaded file nahi mili.")
        return ToolExecutionResult(
            success=True,
            data=last.model_dump(),
            message=f"Boss, last downloaded file hai: '{last.filename}' ({last.size_mb} MB) at {last.file_path}",
        )

    async def open_downloads_folder(self) -> ToolExecutionResult:
        return download_manager.open_downloads_folder()


chrome_adapter = ChromeAdapter()
