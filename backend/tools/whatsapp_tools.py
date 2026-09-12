"""Complete 360-Degree WhatsApp Automation & Address Book Suite for JARVIS AI.

Features:
- Send text message & pre-fill draft
- Voice Call (Ctrl+Shift+C) & Video Call (Ctrl+Shift+V)
- End Call / Hang Up & Call Mute toggle
- Status / Story Viewer (Open status, Next, Previous, Pause)
- Search Chat (Ctrl+F), Next Chat (Ctrl+Tab), Previous Chat (Ctrl+Shift+Tab)
- Mute Chat (Ctrl+Shift+M), Archive Chat (Ctrl+E), Pin Chat (Ctrl+Shift+P), Mark Unread (Ctrl+Shift+U)
- New Chat (Ctrl+N), New Group (Ctrl+Shift+N)
- Delete / Recall Last Message & Clear Draft Box
- Permanent Address Book / Contact Repository
"""
import os
import re
import threading
import time
import urllib.parse
import webbrowser
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

try:
    import win32api
    import win32con
    import win32gui
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

from backend.core.logger import get_logger
from backend.core.permissions import PermissionLevel, ToolCategory
from backend.database.repositories import contact_repo
from backend.tools.registry import tool
from backend.core.safety import (
    is_physical_automation_allowed,
    is_foreground_stealing_allowed,
)

logger = get_logger("WhatsAppTools")


def _sanitize_phone_number(raw: str) -> str:
    """Format and normalize phone number with country code."""
    digits = re.sub(r"[^\d+]", "", raw.strip())
    if digits.startswith("+"):
        digits = digits[1:]
    if len(digits) == 10 and not digits.startswith("91"):
        digits = f"91{digits}"
    return digits


def _focus_whatsapp_window() -> bool:
    """Find and focus the WhatsApp Desktop or Web window."""
    if not is_foreground_stealing_allowed():
        return False
    if not WIN32_AVAILABLE:
        return False
    windows = []
    def enum_cb(hwnd, extra):
        try:
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).lower()
                cls = win32gui.GetClassName(hwnd).lower()
                if "whatsapp" in title or "whatsapp" in cls:
                    extra.append(hwnd)
        except Exception:
            pass
    try:
        win32gui.EnumWindows(enum_cb, windows)
        if windows:
            from backend.tools.browser_tools import force_foreground_window
            force_foreground_window(windows[0])
            time.sleep(0.1)
            return True
    except Exception as exc:
        logger.debug(f"Focus WhatsApp error: {exc}")
    return False


def _send_hotkey(vk_code: int, ctrl: bool = False, shift: bool = False, alt: bool = False, delay_s: float = 0.1) -> None:
    """Send virtual key combination with modifiers."""
    if not is_physical_automation_allowed():
        return
    if not WIN32_AVAILABLE:
        return
    def _worker():
        time.sleep(delay_s)
        try:
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
        except Exception as e:
            logger.debug(f"Hotkey error: {e}")

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


# ==========================================
# Input Schemas
# ==========================================

class SendWhatsAppMessageArgs(BaseModel):
    contact_or_phone: str = Field(..., description="Name of the contact (e.g. 'Shivam', 'Harsh') or phone number.")
    message: str = Field("", description="The message text to send. If empty, opens the chat.")
    auto_send: bool = Field(False, description="Whether to automatically hit Enter to send the message.")


class CallWhatsAppArgs(BaseModel):
    contact_or_phone: str = Field("active", description="Name of the contact or 'active' for current chat.")
    call_type: str = Field("voice", description="Type of call: 'voice' or 'video'.")


class ControlWhatsAppCallArgs(BaseModel):
    action: str = Field("end", description="Call action: 'end' (hang up), 'mute' (toggle mic mute), 'accept' (answer incoming).")


class ManageWhatsAppChatArgs(BaseModel):
    action: str = Field(..., description="Chat action: 'search', 'next_chat', 'prev_chat', 'archive', 'mute', 'pin', 'unread', 'new_chat', 'new_group', 'settings'.")
    query: Optional[str] = Field(None, description="Search query or contact name when searching.")


class ControlWhatsAppStatusArgs(BaseModel):
    action: str = Field("open", description="Status action: 'open' (view status), 'next' (next story), 'prev' (previous story), 'pause' (pause/resume).")


class SaveContactArgs(BaseModel):
    name: str = Field(..., description="Contact full name or nickname.")
    phone: str = Field(..., description="Contact phone number.")
    email: Optional[str] = Field(None, description="Optional email.")
    relationship: Optional[str] = Field(None, description="Optional relationship.")


class GetContactArgs(BaseModel):
    name: str = Field(..., description="Contact name to search.")


class DeleteContactArgs(BaseModel):
    name: str = Field(..., description="Name of the contact to delete.")


class DeleteWhatsAppMessageArgs(BaseModel):
    mode: str = Field("last_sent", description="Deletion mode: 'last_sent' (unsend last sent message) or 'draft' (clear draft box).")


KNOWN_CONTACTS = {
    "harsh": "8054840494",
    "shivam": "9501445740",
}


def _resolve_contact_info(target: str) -> Optional[tuple[str, str]]:
    """Smart contact resolver handling typos, Hindi suffixes (ka, lka, ko, bhai), and phone digits."""
    raw = (target or "").strip()
    if not raw:
        return None

    # Check if raw number given
    if re.match(r"^[\+]?[\d\s\-]{7,15}$", raw):
        return (raw, _sanitize_phone_number(raw))

    # Strip Hindi grammar particles & common typos
    clean = re.sub(r"\b(lka|ka|ki|ke|ko|bhai|bro|ji|contact|number|whatsapp|chat|par|pe)\b", "", raw, flags=re.IGNORECASE).strip()

    # 1. Match against in-memory known contacts dictionary
    for name, num in KNOWN_CONTACTS.items():
        if name in clean.lower() or name in raw.lower():
            return (name.capitalize(), _sanitize_phone_number(num))

    # 2. Match against SQLite database
    contact = contact_repo.get_contact(clean) or contact_repo.get_contact(raw)
    if contact:
        return (contact.name, _sanitize_phone_number(contact.phone))

    return None


@tool(
    name="send_whatsapp_message",
    description="Send or draft a WhatsApp message to a contact or phone number. (e.g. 'Harsh ko message karo: hello', 'Send message to Shivam').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.MEDIA,
    args_schema=SendWhatsAppMessageArgs,
)
def send_whatsapp_message(contact_or_phone: str, message: str = "", auto_send: bool = False) -> Dict[str, Any]:
    """Send or pre-fill a WhatsApp message to a contact or phone number."""
    target = contact_or_phone.strip()
    res = _resolve_contact_info(target)
    if not res:
        return {
            "status": "contact_not_found",
            "recipient": target,
            "message": f"Contact '{target}' ka number save nahi hai. Please boliye: 'Save {target}'s number as <number>'.",
        }

    recipient_name, phone_number = res

    encoded_msg = urllib.parse.quote(message.strip()) if message else ""
    whatsapp_app_url = f"whatsapp://send?phone={phone_number}&text={encoded_msg}" if encoded_msg else f"whatsapp://send?phone={phone_number}"
    whatsapp_web_url = f"https://web.whatsapp.com/send?phone={phone_number}&text={encoded_msg}" if encoded_msg else f"https://web.whatsapp.com/send?phone={phone_number}"

    launched = False
    try:
        if hasattr(os, "startfile"):
            os.startfile(whatsapp_app_url)
            launched = True
        else:
            ret = os.system(f'start "" "{whatsapp_app_url}"')
            if ret == 0:
                launched = True
    except Exception:
        pass

    if not launched:
        webbrowser.open(whatsapp_web_url, new=0, autoraise=True)

    if auto_send and message:
        _send_hotkey(0x0D, delay_s=1.2)  # Enter

    return {
        "status": "success",
        "recipient": recipient_name,
        "phone": phone_number,
        "message": f"WhatsApp par {recipient_name} ko message {'bhej diya' if auto_send else 'chat open kar diya'}.",
    }


def _trigger_whatsapp_call_action(call_type: str = "voice") -> bool:
    """Execute triple-tier call trigger: Accessibility UIAutomation -> Header Coordinate Click -> Native Hotkey."""
    if not WIN32_AVAILABLE:
        return False

    windows = []
    def enum_cb(hwnd, extra):
        try:
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).lower()
                cls = win32gui.GetClassName(hwnd).lower()
                if "whatsapp" in title or "whatsapp" in cls:
                    rect = win32gui.GetWindowRect(hwnd)
                    if (rect[2] - rect[0]) > 200 and (rect[3] - rect[1]) > 200:
                        extra.append((hwnd, rect))
        except Exception:
            pass

    win32gui.EnumWindows(enum_cb, windows)
    if not windows:
        return False

    hwnd, rect = windows[0]
    from backend.tools.browser_tools import force_foreground_window
    force_foreground_window(hwnd)
    time.sleep(0.2)

    is_voice = call_type.lower() == "voice"

    # Tier 1: UIAutomation Call Button Find & Click
    try:
        import comtypes.client
        uia = comtypes.client.CreateObject("{ff48dba4-60ef-4201-aa87-54103eef594e}")
        root = uia.ElementFromHandle(hwnd)
        if root:
            cond = uia.CreatePropertyCondition(30003, 50000)  # ControlType = Button
            buttons = root.FindAll(4, cond)
            for i in range(buttons.Length):
                btn = buttons.GetElement(i)
                b_name = (btn.CurrentName or "").lower()
                b_id = (btn.CurrentAutomationId or "").lower()
                if is_voice and any(k in b_name or k in b_id for k in ["voice call", "audio call", "call"]):
                    btn_rect = btn.CurrentBoundingRectangle
                    cx = (btn_rect.left + btn_rect.right) // 2
                    cy = (btn_rect.top + btn_rect.bottom) // 2
                    from backend.skills.actions import action_engine
                    action_engine.send_hardware_click(cx, cy, double_click=True)
                    logger.info(f"Clicked Voice Call button via UIAutomation at ({cx}, {cy})")
                    return True
                elif not is_voice and any(k in b_name or k in b_id for k in ["video call", "video"]):
                    btn_rect = btn.CurrentBoundingRectangle
                    cx = (btn_rect.left + btn_rect.right) // 2
                    cy = (btn_rect.top + btn_rect.bottom) // 2
                    from backend.skills.actions import action_engine
                    action_engine.send_hardware_click(cx, cy, double_click=True)
                    logger.info(f"Clicked Video Call button via UIAutomation at ({cx}, {cy})")
                    return True
    except Exception as exc:
        logger.debug(f"UIAutomation call button click error: {exc}")

    # Tier 2: Calibrated Header Button Coordinates for WhatsApp Desktop & Web
    # In Windows WhatsApp App: Voice Call is ~110px from right, Video Call is ~155px from right
    if is_voice:
        coords = [
            (rect[2] - 110, rect[1] + 65),  # Windows App Voice Call icon
            (rect[2] - 55, rect[1] + 50),   # Alternate layout
            (rect[2] - 120, rect[1] + 55),  # Web layout
        ]
    else:
        coords = [
            (rect[2] - 155, rect[1] + 65),  # Windows App Video Call icon
            (rect[2] - 95, rect[1] + 50),   # Alternate layout
            (rect[2] - 165, rect[1] + 55),  # Web layout
        ]

    from backend.skills.actions import action_engine
    for cx, cy in coords:
        action_engine.send_hardware_click(cx, cy, double_click=True)
        time.sleep(0.08)

    # Tier 3: Keyboard Shortcut Backup (Ctrl+Shift+C / Ctrl+Shift+V)
    vk = 0x43 if is_voice else 0x56
    _send_hotkey(vk, ctrl=True, shift=True, delay_s=0.15)

    return True


@tool(
    name="call_whatsapp_contact",
    description="Initiate a WhatsApp voice or video call to a contact. (e.g. 'Harsh ko voice call lagao', 'Video call lagao', 'WhatsApp call').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.MEDIA,
    args_schema=CallWhatsAppArgs,
)
def call_whatsapp_contact(contact_or_phone: str = "active", call_type: str = "voice") -> Dict[str, Any]:
    """Start WhatsApp Voice Call or Video Call using robust triple-tier automation."""
    target = (contact_or_phone or "").strip()
    recipient_name = target or "Active Contact"

    if not is_physical_automation_allowed():
        return {
            "status": "SIMULATED",
            "recipient": recipient_name,
            "call_type": call_type,
            "message": f"Simulation: WhatsApp {call_type} call to {recipient_name} (physical automation disabled).",
            "simulated": True,
            "verified": False,
        }

    # If calling the active chat directly
    if not target or target.lower() in ["active", "this contact", "this person", "current chat", "isko", "usko", "chat"]:
        _trigger_whatsapp_call_action(call_type=call_type)
        return {
            "status": "success",
            "recipient": "Active Chat",
            "call_type": call_type,
            "message": f"WhatsApp par {call_type} call connect kar di hai.",
        }

    # Calling specific contact by name/number
    res = _resolve_contact_info(target)
    if res:
        recipient_name, phone_number = res
    else:
        _trigger_whatsapp_call_action(call_type=call_type)
        return {
            "status": "success",
            "recipient": target,
            "call_type": call_type,
            "message": f"WhatsApp par {target} ko {call_type} call laga di hai.",
        }

    call_url = f"whatsapp://send?phone={phone_number}"
    try:
        if hasattr(os, "startfile"):
            os.startfile(call_url)
        else:
            os.system(f'start "" "{call_url}"')
    except Exception:
        webbrowser.open(f"https://web.whatsapp.com/send?phone={phone_number}")

    # Wait for chat to open and execute call
    def _call_after_open():
        time.sleep(2.2)
        _trigger_whatsapp_call_action(call_type=call_type)

    threading.Thread(target=_call_after_open, daemon=True).start()

    return {
        "status": "success",
        "recipient": recipient_name,
        "phone": phone_number,
        "call_type": call_type,
        "message": f"WhatsApp par {recipient_name} ko {call_type} call laga raha hu.",
    }


@tool(
    name="control_whatsapp_call",
    description="Control active WhatsApp call: end call/hang up, mute microphone, or answer incoming. (e.g. 'Call cut karo', 'Call end karo', 'Mute call', 'Hang up').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.MEDIA,
    args_schema=ControlWhatsAppCallArgs,
)
def control_whatsapp_call(action: str = "end") -> Dict[str, Any]:
    """Control active WhatsApp call state."""
    if not is_physical_automation_allowed():
        return {
            "status": "SIMULATED",
            "action": action,
            "message": f"Simulation: WhatsApp call action '{action}' (physical automation disabled).",
            "simulated": True,
            "verified": False,
        }
    _focus_whatsapp_window()
    act = action.lower().strip()

    if act in ["end", "cut", "disconnect", "hangup", "band"]:
        # Escape or Alt+F4 on active call overlay
        _send_hotkey(0x1B, delay_s=0.05)  # VK_ESCAPE
        msg = "WhatsApp call end kar di."
    elif act in ["mute", "unmute", "mic"]:
        # Ctrl+Shift+M
        _send_hotkey(0x4D, ctrl=True, shift=True, delay_s=0.05)
        msg = "WhatsApp call mute/unmute toggle kar diya."
    else:
        _send_hotkey(0x1B, delay_s=0.05)
        msg = f"WhatsApp call action '{action}' execute kiya."

    return {"status": "success", "action": action, "message": msg}


@tool(
    name="manage_whatsapp_chat",
    description="Manage WhatsApp chats: search chat, next/previous chat, mute chat, archive chat, pin chat, mark as unread, new chat dialog. (e.g. 'Next chat', 'Pichla chat', 'Mute this chat', 'Archive chat', 'Search chat Karan', 'New chat kholo').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.MEDIA,
    args_schema=ManageWhatsAppChatArgs,
)
def manage_whatsapp_chat(action: str, query: Optional[str] = None) -> Dict[str, Any]:
    """Execute WhatsApp chat management shortcuts."""
    if not is_physical_automation_allowed():
        return {
            "status": "SIMULATED",
            "action": action,
            "message": f"Simulation: WhatsApp chat action '{action}' (physical automation disabled).",
            "simulated": True,
            "verified": False,
        }
    _focus_whatsapp_window()
    act = action.lower().strip()

    if act in ["search", "find", "search_chat"]:
        _send_hotkey(0x46, ctrl=True, delay_s=0.05)  # Ctrl+F
        if query and is_physical_automation_allowed():
            time.sleep(0.1)
            from backend.skills.actions import action_engine
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(action_engine.type_text(query, press_enter=True))
            except RuntimeError:
                try:
                    asyncio.run(action_engine.type_text(query, press_enter=True))
                except Exception as exc:
                    logger.debug(f"Failed to type whatsapp query: {exc}")
        msg = f"WhatsApp chat search kiya: '{query or ''}'."
    elif act in ["next", "next_chat", "agla"]:
        _send_hotkey(0x09, ctrl=True, delay_s=0.05)  # Ctrl+Tab
        msg = "Agla chat select kiya."
    elif act in ["prev", "prev_chat", "previous", "pichla"]:
        _send_hotkey(0x09, ctrl=True, shift=True, delay_s=0.05)  # Ctrl+Shift+Tab
        msg = "Pichla chat select kiya."
    elif act in ["mute", "mute_chat"]:
        _send_hotkey(0x4D, ctrl=True, shift=True, delay_s=0.05)  # Ctrl+Shift+M
        msg = "Chat notifications mute toggle kiya."
    elif act in ["archive", "archive_chat"]:
        _send_hotkey(0x45, ctrl=True, delay_s=0.05)  # Ctrl+E
        msg = "Chat archive kar diya."
    elif act in ["pin", "pin_chat"]:
        _send_hotkey(0x50, ctrl=True, shift=True, delay_s=0.05)  # Ctrl+Shift+P
        msg = "Chat pin/unpin toggle kiya."
    elif act in ["unread", "mark_unread"]:
        _send_hotkey(0x55, ctrl=True, shift=True, delay_s=0.05)  # Ctrl+Shift+U
        msg = "Chat unread mark kiya."
    elif act in ["new_chat", "new"]:
        _send_hotkey(0x4E, ctrl=True, delay_s=0.05)  # Ctrl+N
        msg = "New chat window open ki."
    elif act in ["new_group"]:
        _send_hotkey(0x4E, ctrl=True, shift=True, delay_s=0.05)  # Ctrl+Shift+N
        msg = "New group window open ki."
    elif act in ["settings"]:
        _send_hotkey(0xBC, ctrl=True, delay_s=0.05)  # Ctrl+,
        msg = "WhatsApp settings open ki."
    else:
        msg = f"Executed WhatsApp chat action: {action}"

    return {"status": "success", "action": action, "message": msg}


@tool(
    name="control_whatsapp_status",
    description="WhatsApp Status / Story controls: open status tab, next status, previous status, pause status. (e.g. 'Status dekho', 'WhatsApp status', 'Next status', 'Previous status', 'Pause status').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.MEDIA,
    args_schema=ControlWhatsAppStatusArgs,
)
def control_whatsapp_status(action: str = "open") -> Dict[str, Any]:
    """Control WhatsApp status stories."""
    if not is_physical_automation_allowed():
        return {
            "status": "SIMULATED",
            "action": action,
            "message": f"Simulation: WhatsApp status action '{action}' (physical automation disabled).",
            "simulated": True,
            "verified": False,
        }
    _focus_whatsapp_window()
    act = action.lower().strip()

    if act in ["open", "status", "dekho", "kholo"]:
        # Click status icon or send Tab navigation
        _send_hotkey(0x09, alt=True, delay_s=0.05)
        msg = "WhatsApp status tab open kiya."
    elif act in ["next", "agla"]:
        _send_hotkey(0x27, delay_s=0.05)  # Right Arrow
        msg = "Agla status story play kiya."
    elif act in ["prev", "previous", "pichla"]:
        _send_hotkey(0x25, delay_s=0.05)  # Left Arrow
        msg = "Pichla status story play kiya."
    elif act in ["pause", "resume", "rok"]:
        _send_hotkey(0x20, delay_s=0.05)  # Spacebar
        msg = "Status pause/resume toggle kiya."
    else:
        msg = f"Executed status action: {action}"

    return {"status": "success", "action": action, "message": msg}


@tool(
    name="delete_whatsapp_message",
    description="Delete or unsend the last sent WhatsApp message, or clear current draft box. (e.g. 'Message delete karo', 'Unsend message', 'Draft clear karo').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.MEDIA,
    args_schema=DeleteWhatsAppMessageArgs,
)
def delete_whatsapp_message(mode: str = "last_sent") -> Dict[str, Any]:
    """Delete last sent message or clear input draft."""
    if not is_physical_automation_allowed():
        return {
            "status": "SIMULATED",
            "mode": mode,
            "message": f"Simulation: WhatsApp delete message ({mode}) (physical automation disabled).",
            "simulated": True,
            "verified": False,
        }
    _focus_whatsapp_window()
    if mode.lower() in ["draft", "input", "box", "clear_draft"]:
        _send_hotkey(0x41, ctrl=True, delay_s=0.05)  # Ctrl+A
        _send_hotkey(0x08, delay_s=0.05)            # Backspace
        msg = "WhatsApp draft message clear kar diya."
    else:
        _send_hotkey(0x26, delay_s=0.05)  # Up Arrow
        _send_hotkey(0x2E, delay_s=0.1)   # Delete
        _send_hotkey(0x0D, delay_s=0.15)  # Enter confirmation
        msg = "Last sent WhatsApp message delete & recall kar diya."

    return {"status": "success", "mode": mode, "message": msg}


@tool(
    name="send_active_message",
    description="Press Send / Enter on active messaging window. (e.g. 'Send karo', 'Bhejo').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.SYSTEM,
)
def send_active_message() -> Dict[str, Any]:
    """Press Enter to send active drafted message."""
    if not is_physical_automation_allowed():
        return {
            "status": "SIMULATED",
            "message": "Simulation: Send active message (physical automation disabled).",
            "simulated": True,
            "verified": False,
        }
    _focus_whatsapp_window()
    _send_hotkey(0x0D, delay_s=0.05)
    return {"status": "success", "message": "Message send kar diya."}


@tool(
    name="save_contact",
    description="Save a new contact in JARVIS persistent address book. (e.g. 'Save Harsh's number as 8054840494').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.MEDIA,
    args_schema=SaveContactArgs,
)
def save_contact(name: str, phone: str, email: Optional[str] = None, relationship: Optional[str] = None) -> Dict[str, Any]:
    """Save or update contact in database."""
    record = contact_repo.save_contact(name=name, phone=phone, email=email, relationship=relationship)
    return {
        "status": "success",
        "name": record.name,
        "phone": record.phone,
        "message": f"Saved '{record.name}' ({record.phone}) in your address book.",
    }


@tool(
    name="get_contact",
    description="Search and view details of a contact from address book. (e.g. 'Harsh ka number kya hai', 'Get contact Shivam').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.MEDIA,
    args_schema=GetContactArgs,
)
def get_contact(name: str) -> Dict[str, Any]:
    """Get contact from database."""
    c = contact_repo.get_contact(name)
    if not c:
        return {"status": "not_found", "message": f"No contact found for '{name}'."}
    return {"status": "success", "name": c.name, "phone": c.phone, "message": f"{c.name}: {c.phone}"}


@tool(
    name="list_contacts",
    description="List all saved contacts in the address book. (e.g. 'Saare contacts dikhao', 'List contacts').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.MEDIA,
)
def list_contacts() -> Dict[str, Any]:
    """List all saved contacts."""
    contacts = contact_repo.list_all()
    c_list = [f"{c.name}: {c.phone}" for c in contacts]
    return {"status": "success", "total": len(contacts), "contacts": c_list, "message": f"{len(contacts)} contacts saved."}


@tool(
    name="delete_contact",
    description="Delete a contact from the address book. (e.g. 'Delete contact Harsh').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.MEDIA,
    args_schema=DeleteContactArgs,
)
def delete_contact(name: str) -> Dict[str, Any]:
    """Delete contact by name."""
    deleted = contact_repo.delete_contact(name)
    return {
        "status": "success" if deleted else "not_found",
        "message": f"Deleted contact '{name}'." if deleted else f"Contact '{name}' not found.",
    }
