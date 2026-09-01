"""JARVIS Plugin Architecture Base Interface.

Every plugin exposes a standardized interface:
- name, description, category, permissions
- validate(), execute(), rollback()
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.core.permissions import PermissionLevel, ToolCategory


class PluginActionResult(BaseModel):
    """Result of a plugin action execution."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    requires_confirmation: bool = False
    confirmation_preview: Optional[Dict[str, Any]] = None


class BasePlugin(ABC):
    """Abstract base class for all JARVIS plugins."""

    def __init__(self, name: str, description: str, category: ToolCategory, required_permissions: List[PermissionLevel]):
        self.name = name
        self.description = description
        self.category = category
        self.required_permissions = required_permissions
        self.enabled: bool = True

    @abstractmethod
    def get_actions(self) -> List[str]:
        """Return list of supported action names."""
        pass

    @abstractmethod
    def validate(self, action: str, params: Dict[str, Any]) -> bool:
        """Validate whether the action and parameters are valid."""
        pass

    @abstractmethod
    async def execute(self, action: str, params: Dict[str, Any]) -> PluginActionResult:
        """Execute the specified action with parameters."""
        pass

    async def rollback(self, action: str, params: Dict[str, Any]) -> bool:
        """Rollback an action if supported."""
        return False
