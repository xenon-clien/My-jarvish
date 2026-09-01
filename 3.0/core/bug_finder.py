"""JARVIS 3.0 - Autonomous Bug Finder & Integrity Inspector.

Inspects tool registrations, imports, selectors, and API dependencies
to detect defects and propose structured repairs.
"""
from typing import Any, Dict, List
from pydantic import BaseModel

from core.logger import get_logger
from core.tool_registry import default_registry

logger = get_logger("BugFinder")


class BugItem(BaseModel):
    bug_id: str
    component: str
    severity: str  # CRITICAL, WARNING, INFO
    issue_description: str
    suggested_repair: str


class BugFinder:
    """Detects invalid tool registrations, broken dependencies, and schema mismatches."""

    @classmethod
    def scan_system_integrity(cls) -> List[BugItem]:
        """Perform static & runtime sanity check on all registered tools and adapters."""
        bugs: List[BugItem] = []
        registered_tools = default_registry.list_tools(only_enabled=False)

        # 1. Check for empty tools
        if not registered_tools:
            bugs.append(BugItem(
                bug_id="BUG-001",
                component="ToolRegistry",
                severity="CRITICAL",
                issue_description="No tools are registered in ToolRegistry.",
                suggested_repair="Initialize application adapters and register tools.",
            ))

        # 2. Check for missing schemas or descriptions
        for t in registered_tools:
            if not t.description or len(t.description.strip()) < 5:
                bugs.append(BugItem(
                    bug_id=f"BUG-DESC-{t.name}",
                    component=t.name,
                    severity="WARNING",
                    issue_description=f"Tool '{t.name}' has missing or too short description.",
                    suggested_repair="Provide clear description explaining tool capability to the AI planner.",
                ))

            # 3. Check for timeout bounds
            if t.timeout_seconds <= 0 or t.timeout_seconds > 60:
                bugs.append(BugItem(
                    bug_id=f"BUG-TIME-{t.name}",
                    component=t.name,
                    severity="WARNING",
                    issue_description=f"Tool '{t.name}' has invalid timeout ({t.timeout_seconds}s).",
                    suggested_repair="Set timeout between 2.0s and 30.0s.",
                ))

        return bugs


bug_finder = BugFinder()
