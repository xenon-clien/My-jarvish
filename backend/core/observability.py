"""Developer Observability & Execution Tracing Engine for JARVIS AI.

Produces structured lifecycle traces for computer actions:
COMMAND -> INTENT -> CURRENT APP -> PLAN -> SELECTED TOOL -> TARGET -> ACTION -> VERIFICATION -> RESULT
100% ASCII-safe and UTF-8 resilient across all Windows console environments.
"""
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.core.logger import get_logger

logger = get_logger("ObservabilityTrace")


class ObservabilityTrace(BaseModel):
    """Structured execution trace for a single user turn or multi-step task."""
    command: str
    understood_intent: str
    current_app: str = "Unknown"
    plan_steps: List[str] = Field(default_factory=list)
    selected_tool: str = "None"
    target: str = ""
    verification_status: str = "PASSED"
    result: str = "SUCCESS"
    execution_time_ms: float = 0.0
    timestamp: float = Field(default_factory=time.time)

    def format_banner(self) -> str:
        """Render a clean ASCII trace banner for terminal and logs."""
        steps_str = " -> ".join(self.plan_steps) if self.plan_steps else self.selected_tool
        banner = (
            f"\n"
            f"+--- [OBSERVABILITY TRACE: {self.understood_intent}] ---+\n"
            f"| COMMAND:      '{self.command}'\n"
            f"| INTENT:       {self.understood_intent}\n"
            f"| CURRENT APP:  {self.current_app}\n"
            f"| PLAN:         {steps_str}\n"
            f"| TOOL:         {self.selected_tool} (Target: '{self.target}')\n"
            f"| VERIFICATION: {self.verification_status}\n"
            f"| RESULT:       {self.result} ({self.execution_time_ms}ms)\n"
            f"+--------------------------------------------------------"
        )
        return banner


class ObservabilityEngine:
    """Singleton trace manager recording execution traces."""

    @classmethod
    def record_trace(cls, trace: ObservabilityTrace) -> None:
        """Record and log structured trace safely."""
        try:
            logger.info(trace.format_banner())
        except Exception:
            pass


# Global singleton observer
observability = ObservabilityEngine()
