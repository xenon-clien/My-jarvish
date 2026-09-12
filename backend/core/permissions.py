"""Permission and confirmation system for JARVIS AI.

Enforces strict boundaries before any tool execution to ensure
destructive, sensitive, or external operations never execute silently.
"""
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from backend.core.config import Settings, get_settings


class PermissionLevel(IntEnum):
    """Hierarchical permission levels for tools."""
    LEVEL_0_SAFE = 0             # Read-only, time, system status, calculator
    LEVEL_1_NORMAL = 1           # Launch app, create folder, move file
    LEVEL_2_COMMUNICATION = 2    # Send message, send email, send file
    LEVEL_3_DESTRUCTIVE = 3      # Delete files, modify system/security settings


class ToolCategory(str, Enum):
    """Functional categories for tools in JARVIS."""
    SYSTEM = "SYSTEM"
    FILE = "FILE"
    BROWSER = "BROWSER"
    SEARCH = "SEARCH"
    COMMUNICATION = "COMMUNICATION"
    PRODUCTIVITY = "PRODUCTIVITY"
    MEDIA = "MEDIA"


class PermissionCheckResult(BaseModel):
    """Result of checking if a tool can execute and if confirmation is needed."""
    allowed: bool
    requires_confirmation: bool
    reason: str
    confirmation_message: Optional[str] = None


class ToolPermissionPolicy:
    """Evaluates whether a tool request requires explicit user confirmation."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    def evaluate(
        self,
        tool_name: str,
        level: PermissionLevel,
        arguments_summary: str = "",
    ) -> PermissionCheckResult:
        """Evaluate whether a tool can be executed automatically or needs user confirmation."""
        # Level 0 - Safe Read-only
        if level == PermissionLevel.LEVEL_0_SAFE:
            if self.settings.AUTO_CONFIRM_LEVEL_0:
                return PermissionCheckResult(
                    allowed=True,
                    requires_confirmation=False,
                    reason="Level 0 safe operation auto-approved.",
                )
            return PermissionCheckResult(
                allowed=True,
                requires_confirmation=True,
                reason="Level 0 auto-confirm is disabled in settings.",
                confirmation_message=f"JARVIS wants to run safe tool '{tool_name}'. Proceed?",
            )

        # Level 1 - Normal Computer Actions
        elif level == PermissionLevel.LEVEL_1_NORMAL:
            if self.settings.AUTO_CONFIRM_LEVEL_1:
                return PermissionCheckResult(
                    allowed=True,
                    requires_confirmation=False,
                    reason="Level 1 normal operation auto-approved by configuration.",
                )
            return PermissionCheckResult(
                allowed=True,
                requires_confirmation=True,
                reason="Level 1 operation requires confirmation.",
                confirmation_message=f"JARVIS wants to execute '{tool_name}' ({arguments_summary}). Allow?",
            )

        # Level 2 - External Communication
        elif level == PermissionLevel.LEVEL_2_COMMUNICATION:
            if self.settings.AUTO_CONFIRM_LEVEL_2:
                return PermissionCheckResult(
                    allowed=True,
                    requires_confirmation=False,
                    reason="Level 2 communication auto-approved.",
                )
            return PermissionCheckResult(
                allowed=True,
                requires_confirmation=True,
                reason="External communication requires explicit verification.",
                confirmation_message=f"JARVIS is about to send external data via '{tool_name}' ({arguments_summary}). Do you approve?",
            )

        # Level 3 - Destructive / Sensitive
        elif level == PermissionLevel.LEVEL_3_DESTRUCTIVE:
            # Level 3 ALWAYS requires confirmation unless explicitly overridden
            if self.settings.AUTO_CONFIRM_LEVEL_3:
                return PermissionCheckResult(
                    allowed=True,
                    requires_confirmation=False,
                    reason="Level 3 operation auto-approved by override.",
                )
            return PermissionCheckResult(
                allowed=True,
                requires_confirmation=True,
                reason="Destructive / sensitive operation requires mandatory confirmation.",
                confirmation_message=f"[WARNING] JARVIS is requesting a DESTRUCTIVE action '{tool_name}' ({arguments_summary}). Are you sure you want to proceed?",
            )

        return PermissionCheckResult(
            allowed=False,
            requires_confirmation=False,
            reason=f"Unknown permission level: {level}",
        )


class SystemPermission(BaseModel):
    name: str
    enabled: bool
    purpose: str
    data_uploaded: bool = False
    data_stored: bool = False
    last_used: Optional[str] = None


class PermissionCenter:
    """Manages system-wide permissions (Camera, Mic, File System, Browser, Messaging, File Sending, System Control, Clipboard)."""

    def __init__(self):
        self.permissions: Dict[str, SystemPermission] = {
            "camera": SystemPermission(
                name="Camera",
                enabled=False,
                purpose="Hand gesture detection (Local landmark extraction only)",
                data_uploaded=False,
                data_stored=False,
            ),
            "microphone": SystemPermission(
                name="Microphone",
                enabled=True,
                purpose="Voice command recognition and audio VAD streaming",
                data_uploaded=False,
                data_stored=False,
            ),
            "file_system": SystemPermission(
                name="File System",
                enabled=True,
                purpose="Reading allowed user directories and organizing files",
                data_uploaded=False,
                data_stored=False,
            ),
            "browser_control": SystemPermission(
                name="Browser Control",
                enabled=True,
                purpose="Navigating web pages and structured YouTube playback",
                data_uploaded=False,
                data_stored=False,
            ),
            "messaging": SystemPermission(
                name="Messaging",
                enabled=True,
                purpose="Sending WhatsApp messages and calls",
                data_uploaded=False,
                data_stored=False,
            ),
            "file_sending": SystemPermission(
                name="File Sending",
                enabled=True,
                purpose="2-step preview file transfer confirmation",
                data_uploaded=False,
                data_stored=False,
            ),
            "system_control": SystemPermission(
                name="System Control",
                enabled=True,
                purpose="App launching, volume adjustment, and window state management",
                data_uploaded=False,
                data_stored=False,
            ),
            "clipboard": SystemPermission(
                name="Clipboard",
                enabled=True,
                purpose="Safe text pasting for automation",
                data_uploaded=False,
                data_stored=False,
            ),
        }

    def get_all_permissions(self) -> List[Dict[str, Any]]:
        return [p.model_dump() for p in self.permissions.values()]

    def set_permission(self, key: str, enabled: bool) -> bool:
        if key in self.permissions:
            self.permissions[key].enabled = enabled
            import time
            self.permissions[key].last_used = time.strftime("%Y-%m-%d %H:%M:%S")
            return True
        return False


permission_center = PermissionCenter()
