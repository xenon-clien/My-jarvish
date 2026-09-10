from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Status = Literal["LIVE_VERIFIED", "DEGRADED", "FAILED", "UNSUPPORTED"]


@dataclass
class Intent:
    application: str
    action: str
    arguments: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source: str = "local"

    @property
    def canonical(self) -> str:
        return f"{self.application}.{self.action}"


@dataclass
class ActionResult:
    success: bool
    status: Status
    action: str
    message: str
    expected: dict[str, Any] = field(default_factory=dict)
    actual: dict[str, Any] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)
