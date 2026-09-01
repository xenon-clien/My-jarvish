"""JARVIS 3.0 - Feature Health Manager.

Tracks health states (HEALTHY, DEGRADED, BROKEN, DISABLED) across all
integrated subsystems and prevents failures in one feature from crashing JARVIS.
"""
from enum import Enum
import threading
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from core.events import EventType, JarvisEvent, event_bus
from core.logger import get_logger

logger = get_logger("FeatureHealth")


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    BROKEN = "BROKEN"
    DISABLED = "DISABLED"


class SubsystemHealth(BaseModel):
    feature_name: str
    status: HealthStatus = HealthStatus.HEALTHY
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    last_error: Optional[str] = None
    last_verified_at: Optional[float] = None
    degraded_reason: Optional[str] = None

    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 100.0
        return round((self.successful_calls / self.total_calls) * 100, 1)


class FeatureHealthManager:
    """Monitors telemetry and manages subsystem degradation boundaries."""

    SUBSYSTEMS = [
        "Gemini",
        "Voice",
        "YouTube",
        "WhatsApp",
        "Browser",
        "System",
        "Filesystem",
        "Diagnostics",
    ]

    def __init__(self):
        self._health: Dict[str, SubsystemHealth] = {
            name: SubsystemHealth(feature_name=name) for name in self.SUBSYSTEMS
        }
        self._lock = threading.RLock()

    def record_call(self, feature_name: str, success: bool, error: Optional[str] = None) -> None:
        """Record success or failure for a feature and adjust health score dynamically."""
        feat = self._normalize_name(feature_name)
        with self._lock:
            if feat not in self._health:
                self._health[feat] = SubsystemHealth(feature_name=feat)

            item = self._health[feat]
            item.total_calls += 1
            if success:
                item.successful_calls += 1
                item.last_verified_at = time.time()
                # Recover to healthy if successful
                if item.status in [HealthStatus.DEGRADED, HealthStatus.BROKEN]:
                    item.status = HealthStatus.HEALTHY
                    item.degraded_reason = None
            else:
                item.failed_calls += 1
                item.last_error = error
                rate = item.success_rate()
                if rate < 40.0:
                    item.status = HealthStatus.BROKEN
                    item.degraded_reason = f"Failure rate > 60% ({error})"
                elif rate < 80.0:
                    item.status = HealthStatus.DEGRADED
                    item.degraded_reason = f"Occasional failures detected ({error})"

    def set_status(self, feature_name: str, status: HealthStatus, reason: Optional[str] = None) -> None:
        feat = self._normalize_name(feature_name)
        with self._lock:
            if feat in self._health:
                self._health[feat].status = status
                self._health[feat].degraded_reason = reason
                event_bus.publish(JarvisEvent(
                    event_type=EventType.FEATURE_HEALTH_CHANGED,
                    data={"feature": feat, "status": status.value, "reason": reason},
                ))

    def get_health(self) -> Dict[str, SubsystemHealth]:
        with self._lock:
            return {k: v.model_copy() for k, v in self._health.items()}

    def get_formatted_health_report(self) -> str:
        """Generate human-readable CLI / Voice health report."""
        with self._lock:
            lines = ["JARVIS 3.0 HEALTH CHECK"]
            lines.append("=" * 32)
            for name, h in self._health.items():
                dots = "." * max(2, 16 - len(name))
                stat_str = h.status.value
                lines.append(f"{name} {dots} {stat_str}")
                if h.degraded_reason and h.status != HealthStatus.HEALTHY:
                    lines.append(f"  └ Reason: {h.degraded_reason}")
            lines.append("=" * 32)
            return "\n".join(lines)

    def _normalize_name(self, name: str) -> str:
        clean = name.lower().strip()
        for sub in self.SUBSYSTEMS:
            if sub.lower() in clean:
                return sub
        return name.title()


# Global FeatureHealthManager singleton
health_manager = FeatureHealthManager()
