"""JARVIS 3.0 - Universal Generic Desktop Application Adapter.

Provides accessibility-first automation, window management, and input control
for all 93+ discovered desktop software programs.
"""
import ctypes
import os
import subprocess
import time
from typing import Any, Dict, List, Optional
import psutil
from pydantic import BaseModel, Field

from adapters.base_adapter import BaseAdapter
from apps.application_registry import application_registry
from core.logger import get_logger
from core.models import PermissionLevel, PermissionType, ToolCategory, ToolExecutionResult
from core.tool_contract import FunctionalTool
from core.tool_registry import ToolRegistry, default_registry

logger = get_logger("GenericDesktop")

try:
    import win32api
    import win32con
    import win32gui
    import win32process
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


class AppTargetArgs(BaseModel):
    app_name: str = Field(..., description="Name or ID of application (e.g. 'Spotify', 'Discord', 'VS Code', 'Notepad').")


class ScrollArgs(BaseModel):
    direction: str = Field(default="down", description="'up' or 'down'")
    clicks: int = Field(default=3, description="Number of scroll clicks")


class GenericDesktopAdapter(BaseAdapter):
    """Universal controller for desktop windows and processes."""

    def __init__(self):
        super().__init__(name="generic_desktop", category=ToolCategory.SYSTEM)

    def register_tools(self, registry: Optional[ToolRegistry] = None) -> None:
        reg = registry or default_registry

        # 1. desktop.open_app
        reg.register(FunctionalTool(
            name="desktop.open_app",
            description="Launch any installed application discovered on the computer.",
            category=ToolCategory.SYSTEM,
            func=self.open_app,
            parameters_schema=AppTargetArgs,
            permission_level=PermissionLevel.LEVEL_1_NORMAL,
        ))

        # 2. desktop.close_app
        reg.register(FunctionalTool(
            name="desktop.close_app",
            description="Close any running application window or process.",
            category=ToolCategory.SYSTEM,
            func=self.close_app,
            parameters_schema=AppTargetArgs,
            permission_level=PermissionLevel.LEVEL_1_NORMAL,
        ))

        # 3. desktop.focus_app
        reg.register(FunctionalTool(
            name="desktop.focus_app",
            description="Bring an open application window to foreground focus.",
            category=ToolCategory.SYSTEM,
            func=self.focus_app,
            parameters_schema=AppTargetArgs,
            permission_level=PermissionLevel.LEVEL_1_NORMAL,
        ))

        # 4. desktop.minimize_app
        reg.register(FunctionalTool(
            name="desktop.minimize_app",
            description="Minimize an open application window.",
            category=ToolCategory.SYSTEM,
            func=self.minimize_app,
            parameters_schema=AppTargetArgs,
            permission_level=PermissionLevel.LEVEL_1_NORMAL,
        ))

        # 5. desktop.maximize_app
        reg.register(FunctionalTool(
            name="desktop.maximize_app",
            description="Maximize an application window to full screen.",
            category=ToolCategory.SYSTEM,
            func=self.maximize_app,
            parameters_schema=AppTargetArgs,
            permission_level=PermissionLevel.LEVEL_1_NORMAL,
        ))

        # 6. desktop.app_status
        reg.register(FunctionalTool(
            name="desktop.app_status",
            description="Check if an application is installed and currently running.",
            category=ToolCategory.SYSTEM,
            func=self.app_status,
            parameters_schema=AppTargetArgs,
            permission_level=PermissionLevel.LEVEL_0_SAFE,
        ))

        # 7. desktop.list_apps
        reg.register(FunctionalTool(
            name="desktop.list_apps",
            description="List all installed applications discovered on the computer.",
            category=ToolCategory.SYSTEM,
            func=self.list_discovered_apps,
            permission_level=PermissionLevel.LEVEL_0_SAFE,
        ))

        # 8. desktop.app_capabilities
        reg.register(FunctionalTool(
            name="desktop.app_capabilities",
            description="Inspect the capability manifest and verified tools for an application.",
            category=ToolCategory.SYSTEM,
            func=self.get_app_capabilities,
            parameters_schema=AppTargetArgs,
            permission_level=PermissionLevel.LEVEL_0_SAFE,
        ))

        # 9. desktop.scroll
        reg.register(FunctionalTool(
            name="desktop.scroll",
            description="Scroll up or down in the active window.",
            category=ToolCategory.SYSTEM,
            func=self.scroll_window,
            parameters_schema=ScrollArgs,
            permission_level=PermissionLevel.LEVEL_1_NORMAL,
        ))

        self.is_initialized = True
        logger.info("Registered GenericDesktopAdapter 9 universal tools.")

    def get_application_state(self) -> Dict[str, Any]:
        return {"active_window": win32gui.GetWindowText(win32gui.GetForegroundWindow()) if WIN32_AVAILABLE else ""}

    def _find_window_for_app(self, app_name: str) -> Optional[int]:
        if not WIN32_AVAILABLE:
            return None
        clean = app_name.lower().strip()
        matched = []

        def enum_cb(hwnd, extra):
            try:
                if win32gui.IsWindowVisible(hwnd):
                    t = win32gui.GetWindowText(hwnd).lower()
                    if clean in t:
                        extra.append(hwnd)
            except Exception:
                pass

        try:
            win32gui.EnumWindows(enum_cb, matched)
            if matched:
                return matched[0]
        except Exception:
            pass
        return None

    def _bring_to_front(self, hwnd: int) -> bool:
        if not WIN32_AVAILABLE or not hwnd:
            return False
        try:
            from adapters.browser_adapter import browser_adapter
            return browser_adapter.force_foreground(hwnd)
        except Exception:
            return False

    # ── UNIVERSAL TOOL IMPLEMENTATIONS ────────────────────────────────────────
    async def open_app(self, app_name: str) -> ToolExecutionResult:
        """Launch discovered or known application."""
        clean = app_name.strip()
        app_obj = application_registry.find_app_by_name(clean)

        cmd = app_obj.launch_command if app_obj else clean
        try:
            subprocess.Popen(cmd, shell=True)
            return ToolExecutionResult(
                success=True,
                data={"app": clean, "command": cmd},
                message=f"Ji Boss, {clean.title()} open kar diya.",
            )
        except Exception as exc:
            return ToolExecutionResult(
                success=False,
                error=f"Could not open '{clean}': {exc}",
            )

    async def close_app(self, app_name: str) -> ToolExecutionResult:
        """Close running application window or terminate process."""
        clean = app_name.lower().strip()
        hwnd = self._find_window_for_app(clean)
        if hwnd and WIN32_AVAILABLE:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            return ToolExecutionResult(
                success=True,
                message=f"Ji Boss, {app_name.title()} close kar diya.",
            )

        # Process termination fallback
        for proc in psutil.process_iter(["name"]):
            name = (proc.info.get("name") or "").lower()
            if clean in name:
                try:
                    proc.terminate()
                    return ToolExecutionResult(
                        success=True,
                        message=f"Ji Boss, {app_name.title()} close kar diya.",
                    )
                except Exception:
                    pass

        return ToolExecutionResult(
            success=False,
            error=f"'{app_name}' ka koi active window nahi mila.",
        )

    async def focus_app(self, app_name: str) -> ToolExecutionResult:
        hwnd = self._find_window_for_app(app_name)
        if hwnd:
            self._bring_to_front(hwnd)
            return ToolExecutionResult(success=True, message=f"Ji Boss, {app_name.title()} focus kar diya.")
        return ToolExecutionResult(success=False, error=f"'{app_name}' open nahi hai.")

    async def minimize_app(self, app_name: str) -> ToolExecutionResult:
        hwnd = self._find_window_for_app(app_name)
        if hwnd and WIN32_AVAILABLE:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            return ToolExecutionResult(success=True, message=f"Ji Boss, {app_name.title()} minimize kar diya.")
        return ToolExecutionResult(success=False, error=f"'{app_name}' window nahi mila.")

    async def maximize_app(self, app_name: str) -> ToolExecutionResult:
        hwnd = self._find_window_for_app(app_name)
        if hwnd and WIN32_AVAILABLE:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            return ToolExecutionResult(success=True, message=f"Ji Boss, {app_name.title()} maximize kar diya.")
        return ToolExecutionResult(success=False, error=f"'{app_name}' window nahi mila.")

    async def app_status(self, app_name: str) -> ToolExecutionResult:
        clean = app_name.lower().strip()
        app_obj = application_registry.find_app_by_name(clean)
        is_running = False

        for proc in psutil.process_iter(["name"]):
            p_name = (proc.info.get("name") or "").lower()
            if clean in p_name:
                is_running = True
                break

        installed_str = "installed hai" if app_obj else "system registry mein nahi mila"
        running_str = "currently chal raha hai" if is_running else "closed hai"

        return ToolExecutionResult(
            success=True,
            data={"is_installed": app_obj is not None, "is_running": is_running},
            message=f"Boss, {app_name.title()} {installed_str} aur abhi {running_str}.",
        )

    async def list_discovered_apps(self) -> ToolExecutionResult:
        apps = application_registry.list_apps()
        summary = application_registry.get_summary_report()
        return ToolExecutionResult(
            success=True,
            data={"total_apps": len(apps), "breakdown": application_registry.get_category_breakdown()},
            message=summary,
        )

    async def get_app_capabilities(self, app_name: str) -> ToolExecutionResult:
        from apps.capability_discovery import capability_discovery_engine
        manifest = capability_discovery_engine.get_manifest_by_id_or_name(app_name)
        if not manifest:
            return ToolExecutionResult(success=False, error=f"Application '{app_name}' not found.")
        caps_str = ", ".join([c.name for c in manifest.capabilities])
        msg = f"App: {manifest.app_name} [{manifest.category}]\nAdapter: {manifest.adapter}\nHealth: {manifest.overall_health}\nCapabilities ({len(manifest.capabilities)}): {caps_str}"
        return ToolExecutionResult(
            success=True,
            data=manifest.model_dump(),
            message=msg,
        )

    async def scroll_window(self, direction: str = "down", clicks: int = 3) -> ToolExecutionResult:
        if WIN32_AVAILABLE:
            user32 = ctypes.windll.user32
            amount = -120 * clicks if direction.lower() == "down" else 120 * clicks
            user32.mouse_event(0x0800, 0, 0, amount, 0)  # MOUSEEVENTF_WHEEL
            return ToolExecutionResult(success=True, message=f"Ji Boss, scroll {direction} kar diya.")
        return ToolExecutionResult(success=False, error="Win32 unavailable")


generic_desktop_adapter = GenericDesktopAdapter()
