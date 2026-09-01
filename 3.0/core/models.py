"""JARVIS 3.0 - Core Data Models.

Defines Pydantic models for tool execution results, verification outcomes,
permission checks, and fallback reports.
"""
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PermissionLevel(IntEnum):
    """Hierarchical permission security levels."""
    LEVEL_0_SAFE = 0             # Read-only, time, system status, calculator
    LEVEL_1_NORMAL = 1           # Launch app, navigation, media controls, browser
    LEVEL_2_COMMUNICATION = 2    # Send message, place voice/video call
    LEVEL_3_DESTRUCTIVE = 3      # Delete files, shutdown, reboot, edit system


class PermissionType(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    EXECUTE = "EXECUTE"
    COMMUNICATE = "COMMUNICATE"
    SYSTEM_CONTROL = "SYSTEM_CONTROL"
    FILESYSTEM = "FILESYSTEM"
    MICROPHONE = "MICROPHONE"
    CAMERA = "CAMERA"
    BROWSER_AUTOMATION = "BROWSER_AUTOMATION"


class ToolCategory(str, Enum):
    SYSTEM = "SYSTEM"
    FILE = "FILE"
    BROWSER = "BROWSER"
    SEARCH = "SEARCH"
    COMMUNICATION = "COMMUNICATION"
    MEDIA = "MEDIA"
    DIAGNOSTICS = "DIAGNOSTICS"
    VOICE = "VOICE"


class ToolExecutionResult(BaseModel):
    """Standardized result returned by any tool execution."""
    success: bool
    data: Any = None
    message: str = ""
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    strategy_used: str = "primary"  # primary, fallback_direct_url, fallback_dom, fallback_coord, etc.


class VerificationResult(BaseModel):
    """Strict post-action verification result."""
    is_verified: bool
    verification_type: str       # e.g., "url_match", "playback_active", "window_focused", "process_alive"
    message: str
    target_state_actual: Optional[str] = None
    target_state_expected: Optional[str] = None
    needs_recovery: bool = False
    suggested_fallback: Optional[str] = None


class PermissionCheckResult(BaseModel):
    """Result of evaluating tool permission."""
    allowed: bool
    requires_confirmation: bool
    reason: str
    confirmation_message: Optional[str] = None


class RetryPolicy(BaseModel):
    """Configurable retry policy for tools."""
    max_retries: int = 2
    backoff_delay_seconds: float = 0.5
    exponential_backoff: bool = True
    retryable_error_keywords: List[str] = Field(
        default_factory=lambda: [
            "timeout", "element_not_found", "not_focused", "loading", "window_not_found", "temporarily_unavailable"
        ]
    )
