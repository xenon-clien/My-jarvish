"""WhatsApp Application Adapter for JARVIS.

Non-destructively wraps existing WhatsApp automation in whatsapp_tools
with resource locking and closed-loop state management.
"""
from typing import Any, Dict, Optional
from backend.core.logger import get_logger
from backend.core.task_manager import task_manager

logger = get_logger("WhatsAppAdapter")


class WhatsAppAdapter:
    """Standardized, verifiable adapter for all WhatsApp operations."""

    RESOURCE_LOCK = "whatsapp"

    def send_message(self, contact_or_phone: str, message: str = "", auto_send: bool = True) -> Dict[str, Any]:
        """Send or draft a message to a WhatsApp contact."""
        from backend.tools.whatsapp_tools import send_whatsapp_message
        task = task_manager.create_task(
            command=f"WhatsApp {contact_or_phone} ko message",
            tool_name="whatsapp.send_message",
            arguments={"contact_or_phone": contact_or_phone, "message": message, "auto_send": auto_send},
            required_locks=[self.RESOURCE_LOCK],
            immediate_response=f"Ji Boss, WhatsApp par {contact_or_phone} ko message {'bhej diya.' if message else 'chat open kar diya.'}",
        )
        return task_manager.execute_task_sync(task=task, executor_fn=send_whatsapp_message).result or {"status": "success"}

    def voice_call(self, contact_or_phone: str) -> Dict[str, Any]:
        """Initiate WhatsApp voice call."""
        from backend.tools.whatsapp_tools import call_whatsapp_contact
        task = task_manager.create_task(
            command=f"WhatsApp {contact_or_phone} ko voice call",
            tool_name="whatsapp.voice_call",
            arguments={"contact_or_phone": contact_or_phone, "call_type": "voice"},
            required_locks=[self.RESOURCE_LOCK, "microphone"],
            immediate_response=f"Ji Boss, WhatsApp par {contact_or_phone} ko voice call laga di hai.",
        )
        return task_manager.execute_task_sync(task=task, executor_fn=call_whatsapp_contact).result or {"status": "success"}

    def video_call(self, contact_or_phone: str) -> Dict[str, Any]:
        """Initiate WhatsApp video call."""
        from backend.tools.whatsapp_tools import call_whatsapp_contact
        task = task_manager.create_task(
            command=f"WhatsApp {contact_or_phone} ko video call",
            tool_name="whatsapp.video_call",
            arguments={"contact_or_phone": contact_or_phone, "call_type": "video"},
            required_locks=[self.RESOURCE_LOCK, "microphone"],
            immediate_response=f"Ji Boss, WhatsApp par {contact_or_phone} ko video call laga di hai.",
        )
        return task_manager.execute_task_sync(task=task, executor_fn=call_whatsapp_contact).result or {"status": "success"}

    def end_call(self) -> Dict[str, Any]:
        """End ongoing WhatsApp call."""
        from backend.tools.whatsapp_tools import control_whatsapp_call
        task = task_manager.create_task(
            command="WhatsApp call end karo",
            tool_name="whatsapp.end_call",
            arguments={"action": "end"},
            required_locks=[self.RESOURCE_LOCK],
            immediate_response="Ji Boss, WhatsApp call end kar di.",
        )
        return task_manager.execute_task_sync(task=task, executor_fn=control_whatsapp_call).result or {"status": "success"}

    def toggle_call_mute(self) -> Dict[str, Any]:
        """Mute / Unmute call microphone."""
        from backend.tools.whatsapp_tools import control_whatsapp_call
        task = task_manager.create_task(
            command="WhatsApp call mic mute",
            tool_name="whatsapp.mute_call",
            arguments={"action": "mute"},
            required_locks=[self.RESOURCE_LOCK],
            immediate_response="Ji Boss, call mic mute toggle kar diya.",
        )
    def open(self) -> Dict[str, Any]:
        """Open WhatsApp Desktop application."""
        return self.send_message(contact_or_phone="active", message="", auto_send=False)

    def mute_call(self) -> Dict[str, Any]:
        """Alias for toggle call mute."""
        return self.toggle_call_mute()

    def view_status(self) -> Dict[str, Any]:
        """View WhatsApp Status feed."""
        from backend.tools.whatsapp_tools import control_whatsapp_status
        return control_whatsapp_status(action="open")

    def delete_message(self, mode: str = "last_sent") -> Dict[str, Any]:
        """Delete / unsend message."""
        from backend.tools.whatsapp_tools import delete_whatsapp_message
        return delete_whatsapp_message(mode=mode)


# Global Singleton WhatsApp Adapter
whatsapp_adapter = WhatsAppAdapter()
