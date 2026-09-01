"""JARVIS 3.0 - WhatsApp Desktop & Web Application Adapter.

Handles legitimate WhatsApp automation: opening chats, prefilling/sending messages,
triggering voice/video calls on WhatsApp Desktop, and ending calls.
"""
import ctypes
import os
import re
import threading
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

logger = get_logger("WhatsAppAdapter")

try:
    import win32api
    import win32con
    import win32gui
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


class SendMessageArgs(BaseModel):
    contact: str = Field(..., description="Name or phone number of recipient.")
    message: str = Field(default="", description="Message text to send.")
    auto_send: bool = Field(default=False, description="Whether to press Enter automatically to send.")


class CallArgs(BaseModel):
    contact: str = Field(default="active", description="Contact name or 'active' for currently open chat.")


class WhatsAppAdapter(BaseAdapter):
    """Encapsulates all WhatsApp automation."""

    KNOWN_CONTACTS: Dict[str, str] = {
        "harsh": "8054840494",
        "shivam": "9501445740",
    }

    def __init__(self):
        super().__init__(name="whatsapp", category=ToolCategory.COMMUNICATION)

    def register_tools(self, registry: Optional[ToolRegistry] = None) -> None:
        reg = registry or default_registry

        # 1. whatsapp.open
        reg.register(FunctionalTool(
            name="whatsapp.open",
            description="Open WhatsApp Desktop application or Web interface.",
            category=ToolCategory.COMMUNICATION,
            func=self.open_whatsapp,
            permission_level=PermissionLevel.LEVEL_1_NORMAL,
            required_permissions=[PermissionType.COMMUNICATE],
        ))

        # 2. whatsapp.send_message
        reg.register(FunctionalTool(
            name="whatsapp.send_message",
            description="Open chat and send or pre-fill a WhatsApp message.",
            category=ToolCategory.COMMUNICATION,
            func=self.send_message,
            permission_level=PermissionLevel.LEVEL_2_COMMUNICATION,
            required_permissions=[PermissionType.COMMUNICATE],
            parameters_schema=SendMessageArgs,
        ))

        # 3. whatsapp.voice_call
        reg.register(FunctionalTool(
            name="whatsapp.voice_call",
            description="Initiate a WhatsApp voice call to a contact or active chat.",
            category=ToolCategory.COMMUNICATION,
            func=self.voice_call,
            permission_level=PermissionLevel.LEVEL_2_COMMUNICATION,
            required_permissions=[PermissionType.COMMUNICATE],
            parameters_schema=CallArgs,
        ))

        # 4. whatsapp.video_call
        reg.register(FunctionalTool(
            name="whatsapp.video_call",
            description="Initiate a WhatsApp video call to a contact.",
            category=ToolCategory.COMMUNICATION,
            func=self.video_call,
            permission_level=PermissionLevel.LEVEL_2_COMMUNICATION,
            required_permissions=[PermissionType.COMMUNICATE],
            parameters_schema=CallArgs,
        ))

        # 5. whatsapp.end_call
        reg.register(FunctionalTool(
            name="whatsapp.end_call",
            description="Disconnect / hang up the active WhatsApp call.",
            category=ToolCategory.COMMUNICATION,
            func=self.end_call,
            permission_level=PermissionLevel.LEVEL_1_NORMAL,
            required_permissions=[PermissionType.COMMUNICATE],
        ))

        self.is_initialized = True
        logger.info("Registered WhatsAppAdapter tools: whatsapp.open, whatsapp.send_message, whatsapp.voice_call, whatsapp.video_call, whatsapp.end_call")

    def get_application_state(self) -> Dict[str, Any]:
        hwnd = self._find_whatsapp_window()
        return {"whatsapp_open": hwnd is not None}

    def _find_whatsapp_window(self) -> Optional[int]:
        if not WIN32_AVAILABLE:
            return None
        matched = []
        def enum_cb(hwnd, extra):
            try:
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd).lower()
                    cls = win32gui.GetClassName(hwnd).lower()
                    if "whatsapp" in title or "whatsapp" in cls:
                        extra.append(hwnd)
            except Exception:
                pass
        win32gui.EnumWindows(enum_cb, matched)
        return matched[0] if matched else None

    def _focus_whatsapp(self) -> bool:
        hwnd = self._find_whatsapp_window()
        if hwnd and WIN32_AVAILABLE:
            try:
                from adapters.browser_adapter import browser_adapter
                return browser_adapter.force_foreground(hwnd)
            except Exception:
                pass
        return False

    def _resolve_phone(self, contact_or_phone: str) -> Optional[tuple[str, str]]:
        raw = contact_or_phone.strip()
        # Direct phone digits
        digits = re.sub(r"[^\d+]", "", raw)
        if len(digits) >= 10:
            if len(digits) == 10 and not digits.startswith("91"):
                digits = f"91{digits}"
            return (raw, digits.lstrip("+"))

        # Look in known contacts
        for name, num in self.KNOWN_CONTACTS.items():
            if name in raw.lower():
                return (name.title(), num)

        return None

    async def open_whatsapp(self) -> ToolExecutionResult:
        """Launch WhatsApp Desktop via protocol."""
        launched = False
        try:
            os.startfile("whatsapp:")
            launched = True
        except Exception:
            pass

        if not launched:
            webbrowser.open("https://web.whatsapp.com")

        return ToolExecutionResult(
            success=True,
            message="Ji Boss, WhatsApp open kar diya.",
        )

    async def send_message(self, contact: str, message: str = "", auto_send: bool = False) -> ToolExecutionResult:
        """Send message or open chat."""
        res = self._resolve_phone(contact)
        if not res:
            return ToolExecutionResult(
                success=False,
                error=f"Contact '{contact}' ka phone number save nahi hai.",
                message=f"Boss, '{contact}' ka number address book mein nahi mila.",
            )

        name, phone = res
        encoded_msg = urllib.parse.quote(message.strip()) if message else ""
        app_uri = f"whatsapp://send?phone={phone}&text={encoded_msg}" if encoded_msg else f"whatsapp://send?phone={phone}"
        web_uri = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_msg}" if encoded_msg else f"https://web.whatsapp.com/send?phone={phone}"

        launched = False
        try:
            os.startfile(app_uri)
            launched = True
        except Exception:
            pass

        if not launched:
            webbrowser.open(web_uri)

        if auto_send and message and WIN32_AVAILABLE:
            def _press_enter():
                time.sleep(1.4)
                self._focus_whatsapp()
                user32 = ctypes.windll.user32
                user32.keybd_event(0x0D, 0, 0, 0)
                time.sleep(0.04)
                user32.keybd_event(0x0D, 0, 2, 0)
            threading.Thread(target=_press_enter, daemon=True).start()

        return ToolExecutionResult(
            success=True,
            data={"recipient": name, "phone": phone},
            message=f"WhatsApp par {name} ko message {'bhej diya.' if auto_send else 'chat open kar di.'}",
        )

    async def voice_call(self, contact: str = "active") -> ToolExecutionResult:
        """Place voice call on WhatsApp."""
        res = self._resolve_phone(contact)
        if res:
            name, phone = res
            call_url = f"whatsapp://send?phone={phone}"
            try:
                os.startfile(call_url)
            except Exception:
                pass
            time.sleep(1.2)
        else:
            name = contact

        self._focus_whatsapp()
        # Shortcut Ctrl+Shift+C on WhatsApp Desktop
        if WIN32_AVAILABLE:
            user32 = ctypes.windll.user32
            user32.keybd_event(0x11, 0, 0, 0)  # Ctrl
            user32.keybd_event(0x10, 0, 0, 0)  # Shift
            user32.keybd_event(0x43, 0, 0, 0)  # 'C'
            time.sleep(0.05)
            user32.keybd_event(0x43, 0, 2, 0)
            user32.keybd_event(0x10, 0, 2, 0)
            user32.keybd_event(0x11, 0, 2, 0)

        return ToolExecutionResult(
            success=True,
            data={"recipient": name, "call_type": "voice"},
            message=f"WhatsApp par {name} ko voice call laga di.",
        )

    async def video_call(self, contact: str = "active") -> ToolExecutionResult:
        """Place video call on WhatsApp."""
        res = self._resolve_phone(contact)
        if res:
            name, phone = res
            try:
                os.startfile(f"whatsapp://send?phone={phone}")
            except Exception:
                pass
            time.sleep(1.2)
        else:
            name = contact

        self._focus_whatsapp()
        # Shortcut Ctrl+Shift+V on WhatsApp Desktop
        if WIN32_AVAILABLE:
            user32 = ctypes.windll.user32
            user32.keybd_event(0x11, 0, 0, 0)  # Ctrl
            user32.keybd_event(0x10, 0, 0, 0)  # Shift
            user32.keybd_event(0x56, 0, 0, 0)  # 'V'
            time.sleep(0.05)
            user32.keybd_event(0x56, 0, 2, 0)
            user32.keybd_event(0x10, 0, 2, 0)
            user32.keybd_event(0x11, 0, 2, 0)

        return ToolExecutionResult(
            success=True,
            data={"recipient": name, "call_type": "video"},
            message=f"WhatsApp par {name} ko video call laga di.",
        )

    async def end_call(self) -> ToolExecutionResult:
        """Disconnect WhatsApp call (Escape key)."""
        self._focus_whatsapp()
        if WIN32_AVAILABLE:
            user32 = ctypes.windll.user32
            user32.keybd_event(0x1B, 0, 0, 0)  # Escape
            time.sleep(0.04)
            user32.keybd_event(0x1B, 0, 2, 0)
        return ToolExecutionResult(success=True, message="WhatsApp call disconnect kar di.")


whatsapp_adapter = WhatsAppAdapter()
