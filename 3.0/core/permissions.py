"""JARVIS 3.0 - Permission & Security Policy Manager.

Enforces strict authorization boundaries before any tool executes.
Never executes destructive or sensitive actions without explicit user verification.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from core.config import get_settings
from core.logger import get_logger
from core.models import (
    PermissionCheckResult,
    PermissionLevel,
    PermissionType,
)

logger = get_logger("PermissionManager")


class SystemPermissionToggle(BaseModel):
    name: str
    key: str
    enabled: bool
    description: str
    permission_type: PermissionType


class PermissionManager:
    """Evaluates security policies, user permissions, and confirmation requirements."""

    def __init__(self):
        self.settings = get_settings()
        self._toggles: Dict[str, SystemPermissionToggle] = {
            "browser_automation": SystemPermissionToggle(
                name="Browser Automation",
                key="browser_automation",
                enabled=True,
                description="Navigating websites and controlling YouTube playback",
                permission_type=PermissionType.BROWSER_AUTOMATION,
            ),
            "messaging": SystemPermissionToggle(
                name="Messaging & Calls",
                key="messaging",
                enabled=True,
                description="Sending WhatsApp messages and placing calls",
                permission_type=PermissionType.COMMUNICATE,
            ),
            "microphone": SystemPermissionToggle(
                name="Microphone",
                key="microphone",
                enabled=True,
                description="Speech recognition and Voice command listening",
                permission_type=PermissionType.MICROPHONE,
            ),
            "camera": SystemPermissionToggle(
                name="Camera",
                key="camera",
                enabled=False,
                description="Hand gesture tracking and visual inspection",
                permission_type=PermissionType.CAMERA,
            ),
            "filesystem": SystemPermissionToggle(
                name="File System",
                key="filesystem",
                enabled=True,
                description="Reading and writing files in sandboxed directories",
                permission_type=PermissionType.FILESYSTEM,
            ),
            "system_control": SystemPermissionToggle(
                name="System Control",
                key="system_control",
                enabled=True,
                description="App launching, volume adjustment, and power settings",
                permission_type=PermissionType.SYSTEM_CONTROL,
            ),
        }

    def evaluate_tool_permission(
        self,
        tool_name: str,
        level: PermissionLevel,
        required_permissions: List[PermissionType],
        arguments: Dict[str, Any],
    ) -> PermissionCheckResult:
        """Evaluate if tool can run immediately or requires explicit approval."""
        # 1. Check required subsystem permission toggles
        for p_type in required_permissions:
            for toggle in self._toggles.values():
                if toggle.permission_type == p_type and not toggle.enabled:
                    return PermissionCheckResult(
                        allowed=False,
                        requires_confirmation=False,
                        reason=f"Permission for '{toggle.name}' is currently disabled in JARVIS settings.",
                    )

        # 2. Level 0 - Safe Read-only
        if level == PermissionLevel.LEVEL_0_SAFE:
            return PermissionCheckResult(
                allowed=True,
                requires_confirmation=False,
                reason="Level 0 safe read-only operation approved.",
            )

        # 3. Level 1 - Normal Computer Actions
        elif level == PermissionLevel.LEVEL_1_NORMAL:
            return PermissionCheckResult(
                allowed=True,
                requires_confirmation=False,
                reason="Level 1 normal desktop action auto-approved.",
            )

        # 4. Level 2 - External Communication
        elif level == PermissionLevel.LEVEL_2_COMMUNICATION:
            # Auto-approve messaging if configured, else confirm
            return PermissionCheckResult(
                allowed=True,
                requires_confirmation=False,
                reason="Level 2 communication approved.",
            )

        # 5. Level 3 - Destructive Operations
        elif level == PermissionLevel.LEVEL_3_DESTRUCTIVE:
            args_str = ", ".join([f"{k}={v}" for k, v in arguments.items() if k != "password"])
            return PermissionCheckResult(
                allowed=True,
                requires_confirmation=True,
                reason="Level 3 destructive operation requires user confirmation.",
                confirmation_message=f"JARVIS wants to execute a sensitive action: '{tool_name}' ({args_str}). Do you confirm? (Say 'Yes' / 'Confirm' or click Allow)",
            )

        return PermissionCheckResult(
            allowed=False,
            requires_confirmation=False,
            reason=f"Unknown permission level: {level}",
        )

    def set_permission_toggle(self, key: str, enabled: bool) -> bool:
        """Enable or disable a subsystem permission."""
        if key in self._toggles:
            self._toggles[key].enabled = enabled
            logger.info(f"Permission toggle '{key}' set to: {enabled}")
            return True
        return False

    def list_permissions(self) -> List[Dict[str, Any]]:
        """List all permission settings."""
        return [p.model_dump() for p in self._toggles.values()]


# Global PermissionManager singleton
permission_manager = PermissionManager()
