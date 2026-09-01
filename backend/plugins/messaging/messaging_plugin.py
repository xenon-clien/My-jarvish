"""Messaging Plugin for JARVIS."""
from typing import Any, Dict, List
from backend.core.permissions import PermissionLevel, ToolCategory
from backend.plugins.base import BasePlugin, PluginActionResult
from backend.tools.whatsapp_tools import send_whatsapp_message, call_whatsapp_contact


class MessagingPlugin(BasePlugin):
    """Plugin for WhatsApp messaging and calls."""

    def __init__(self):
        super().__init__(
            name="messaging",
            description="WhatsApp messaging, voice calling, and video calling.",
            category=ToolCategory.COMMUNICATION,
            required_permissions=[PermissionLevel.LEVEL_2_COMMUNICATION],
        )

    def get_actions(self) -> List[str]:
        return ["send_message", "start_call"]

    def validate(self, action: str, params: Dict[str, Any]) -> bool:
        return action in self.get_actions()

    async def execute(self, action: str, params: Dict[str, Any]) -> PluginActionResult:
        try:
            if action == "send_message":
                c = params.get("contact_or_phone", "")
                m = params.get("message", "Hello")
                res = send_whatsapp_message(contact_or_phone=c, message=m, auto_send=False)
                return PluginActionResult(success=True, message=res.get("message", "Sent WhatsApp message."), data=res)
            elif action == "start_call":
                c = params.get("contact_or_phone", "")
                t = params.get("call_type", "voice")
                res = call_whatsapp_contact(contact_or_phone=c, call_type=t)
                return PluginActionResult(success=True, message=res.get("message", "Started call."), data=res)
        except Exception as e:
            return PluginActionResult(success=False, message=str(e))
        return PluginActionResult(success=False, message=f"Action '{action}' not handled.")
