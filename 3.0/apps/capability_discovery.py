"""JARVIS 3.0 - Capability Discovery Engine.

Generates explicit capability manifests for all discovered applications,
distinguishing between verified supported tools, generic desktop automation, and unsupported features.
"""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from apps.application_discovery import DiscoveredApp
from apps.application_registry import application_registry
from core.health_manager import HealthStatus, health_manager
from core.logger import get_logger
from core.tool_registry import default_registry

logger = get_logger("CapabilityDiscovery")


class CapabilityStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    AVAILABLE = "AVAILABLE"
    SUPPORTED = "SUPPORTED"
    DEGRADED = "DEGRADED"
    UNSUPPORTED = "UNSUPPORTED"
    DISABLED = "DISABLED"


class AppCapability(BaseModel):
    name: str
    tool_id: Optional[str] = None
    description: str
    status: CapabilityStatus = CapabilityStatus.SUPPORTED
    is_verified: bool = True


class AppCapabilityManifest(BaseModel):
    app_id: str
    app_name: str
    category: str
    adapter: str
    overall_health: str = "HEALTHY"
    supported_capabilities_count: int = 0
    capabilities: List[AppCapability] = Field(default_factory=list)


class CapabilityDiscoveryEngine:
    """Discovers and manages capabilities for all installed applications."""

    GENERIC_CAPABILITIES = [
        AppCapability(name="open", tool_id="desktop.open_app", description="Launch the application window", status=CapabilityStatus.SUPPORTED),
        AppCapability(name="close", tool_id="desktop.close_app", description="Close the active application window", status=CapabilityStatus.SUPPORTED),
        AppCapability(name="focus", tool_id="desktop.focus_app", description="Bring application to foreground", status=CapabilityStatus.SUPPORTED),
        AppCapability(name="minimize", tool_id="desktop.minimize_app", description="Minimize application window", status=CapabilityStatus.SUPPORTED),
        AppCapability(name="maximize", tool_id="desktop.maximize_app", description="Maximize application window", status=CapabilityStatus.SUPPORTED),
        AppCapability(name="status", tool_id="desktop.app_status", description="Inspect whether application process is running", status=CapabilityStatus.SUPPORTED),
    ]

    @classmethod
    def get_manifest_for_app(cls, app: DiscoveredApp) -> AppCapabilityManifest:
        """Generate comprehensive capability manifest for an application."""
        caps: List[AppCapability] = []

        # 1. Add generic desktop window controls
        caps.extend(cls.GENERIC_CAPABILITIES)

        # 2. Check if tools registered specifically for this adapter/app prefix
        app_prefix = app.id.replace("_", ".")
        all_tools = default_registry.list_tools(only_enabled=False)

        for t in all_tools:
            if t.name.startswith(app.id) or (app.adapter_name.lower().replace("adapter", "") in t.name.lower()):
                caps.append(AppCapability(
                    name=t.name.split(".")[-1],
                    tool_id=t.name,
                    description=t.description,
                    status=CapabilityStatus.SUPPORTED if t.is_enabled else CapabilityStatus.DISABLED,
                    is_verified=True,
                ))

        # Deduplicate capabilities by name
        unique_caps = {}
        for c in caps:
            unique_caps[c.name] = c

        caps_list = list(unique_caps.values())
        h_score = health_manager.get_health().get(app.name, None)
        health_val = h_score.status.value if h_score else "HEALTHY"

        return AppCapabilityManifest(
            app_id=app.id,
            app_name=app.name,
            category=app.category.value,
            adapter=app.adapter_name,
            overall_health=health_val,
            supported_capabilities_count=len(caps_list),
            capabilities=caps_list,
        )

    @classmethod
    def get_manifest_by_id_or_name(cls, app_identifier: str) -> Optional[AppCapabilityManifest]:
        """Lookup capability manifest for application by ID or fuzzy name."""
        app = application_registry.get_app(app_identifier) or application_registry.find_app_by_name(app_identifier)
        if not app:
            return None
        return cls.get_manifest_for_app(app)


capability_discovery_engine = CapabilityDiscoveryEngine()
