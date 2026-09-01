"""Universal App Skill & Capability Data Models for JARVIS AI.

Defines the core data structures for application capability mapping, action definitions,
feature matrices, execution states, and self-healing manifests.
"""
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class CapabilityStatus(str, Enum):
    """Status classification for application capabilities."""
    WORKING = "WORKING"
    DEGRADED = "DEGRADED"
    BROKEN = "BROKEN"
    PARTIAL = "PARTIAL"
    UNTESTED = "UNTESTED"
    UNSUPPORTED = "UNSUPPORTED"
    LIMITED = "LIMITED"


class FallbackTier(str, Enum):
    """7-Tier Fallback Execution Hierarchy."""
    OFFICIAL_API = "OFFICIAL_API"
    DOM_SEMANTIC = "DOM_SEMANTIC"
    ACCESSIBILITY_TREE = "ACCESSIBILITY_TREE"
    APP_AUTOMATION_API = "APP_AUTOMATION_API"
    KEYBOARD_SHORTCUT = "KEYBOARD_SHORTCUT"
    VISUAL_RECOGNITION = "VISUAL_RECOGNITION"
    COORDINATE_FALLBACK = "COORDINATE_FALLBACK"


class ActionParameter(BaseModel):
    """Parameter definition for an application action."""
    name: str
    type: str = "string"
    description: str = ""
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[List[str]] = None


class AppActionDefinition(BaseModel):
    """Specification of an actionable capability on an application."""
    name: str
    description: str
    tier: FallbackTier = FallbackTier.ACCESSIBILITY_TREE
    target_selector: Optional[str] = None
    dom_selector: Optional[str] = None
    aria_label: Optional[str] = None
    keyboard_shortcut: Optional[str] = None
    key_codes: Optional[List[int]] = None
    parameters: Dict[str, ActionParameter] = Field(default_factory=dict)
    requires_confirmation: bool = False
    confirmation_message: Optional[str] = None
    verification_rule: Optional[str] = None  # e.g. 'state_changed', 'url_matches', 'element_visible'
    fallback_tiers: List[FallbackTier] = Field(default_factory=lambda: [
        FallbackTier.OFFICIAL_API,
        FallbackTier.DOM_SEMANTIC,
        FallbackTier.ACCESSIBILITY_TREE,
        FallbackTier.KEYBOARD_SHORTCUT,
        FallbackTier.COORDINATE_FALLBACK,
    ])
    undo_action: Optional[str] = None


class AppFeatureMatrixEntry(BaseModel):
    """Detailed capability tracking entry for health matrix reports."""
    capability: str
    available: bool = True
    implemented: bool = True
    tested: bool = False
    verified: bool = False
    fallback_method: str = "KEYBOARD_SHORTCUT"
    status: CapabilityStatus = CapabilityStatus.UNTESTED
    last_checked: Optional[str] = None
    error_message: Optional[str] = None


class AppCapabilityMap(BaseModel):
    """Complete 360-degree capability profile of an application."""
    application: str
    display_name: str
    version: str = "1.0.0"
    process_names: List[str] = Field(default_factory=list)
    window_classes: List[str] = Field(default_factory=list)
    url_patterns: List[str] = Field(default_factory=list)
    category: str = "general"
    capabilities: List[str] = Field(default_factory=list)
    actions: Dict[str, AppActionDefinition] = Field(default_factory=dict)
    navigation: List[str] = Field(default_factory=list)
    mediaControls: List[str] = Field(default_factory=list)
    inputControls: List[str] = Field(default_factory=list)
    stateInformation: List[str] = Field(default_factory=list)
    accessibilityCapabilities: List[str] = Field(default_factory=list)
    browserCapabilities: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    verificationMethods: List[str] = Field(default_factory=list)
    feature_matrix: Dict[str, AppFeatureMatrixEntry] = Field(default_factory=dict)
    last_updated: Optional[str] = None


class AppContextState(BaseModel):
    """Live state of current interaction context."""
    active_app: Optional[str] = None
    active_window_title: Optional[str] = None
    active_window_hwnd: Optional[int] = None
    active_page_url: Optional[str] = None
    active_tab_index: Optional[int] = None
    selected_element_role: Optional[str] = None
    selected_element_name: Optional[str] = None
    media_state: Optional[str] = None  # 'playing', 'paused', 'stopped'
    media_title: Optional[str] = None
    media_timestamp: Optional[str] = None
    last_action: Optional[str] = None
    last_action_target: Optional[str] = None
    last_action_timestamp: Optional[float] = None
    action_history: List[Dict[str, Any]] = Field(default_factory=list)
    pending_confirmation_action: Optional[Dict[str, Any]] = None


class ActionResult(BaseModel):
    """Outcome of an executed app action with verification metadata."""
    success: bool
    action: str
    application: str
    tier_used: FallbackTier
    message: str
    data: Optional[Dict[str, Any]] = None
    verified: bool = False
    recovery_attempted: bool = False
    execution_time_ms: float = 0.0
