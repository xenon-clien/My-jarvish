"""JARVIS 3.0 - Base Application Adapter.

Every external application integration inherits from BaseAdapter.
Isolates UI logic, state detection, and platform interactions.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from core.logger import get_logger
from core.models import ToolCategory
from core.tool_registry import ToolRegistry, default_registry

logger = get_logger("BaseAdapter")


class BaseAdapter(ABC):
    """Abstract Base Class for all Application Adapters."""

    def __init__(self, name: str, category: ToolCategory):
        self.name = name
        self.category = category
        self.is_initialized = False

    @abstractmethod
    def register_tools(self, registry: Optional[ToolRegistry] = None) -> None:
        """Register all tools provided by this adapter."""
        pass

    @abstractmethod
    def get_application_state(self) -> Dict[str, Any]:
        """Inspect current state (URL, active title, process status, etc.)."""
        pass
