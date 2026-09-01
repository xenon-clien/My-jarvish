"""Nemotron Usage Guard & Free-Tier Cost Safety Hard-Stop Engine.

Enforces absolute cost-safety invariants:
1. Model Allowlist: strictly 'nvidia/nemotron-3.5-lightning:free'. Zero paid model switching.
2. Local Warning Threshold: 40 requests/day -> automatically stops automatic Nemotron usage.
3. Local Hard Cap: 45 requests/day -> hard stop, zero further requests.
4. Provider Overrides: 429 quota exhaustion immediately disables Nemotron.
5. Zero Paid Fallback: Never purchase credits, enable billing, or remove ':free'.
6. Persistence: Counters survive restarts and only reset at day boundary.
"""
from datetime import datetime, date
from enum import Enum
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from backend.core.config import get_settings
from backend.core.logger import get_logger

logger = get_logger("NemotronUsageGuard")

# ABSOLUTE HARD ALLOWLIST: ONLY THIS FREE MODEL IS PERMITTED
NVIDIA_ALLOWED_MODELS: List[str] = [
    "nvidia/nemotron-3.5-lightning:free"
]


class NemotronState(str, Enum):
    AVAILABLE = "AVAILABLE"
    DEBUGGING = "DEBUGGING"
    NEAR_FREE_LIMIT = "NEAR_FREE_LIMIT"
    COOLDOWN = "COOLDOWN"
    LOCAL_FREE_LIMIT_REACHED = "LOCAL_FREE_LIMIT_REACHED"
    PROVIDER_FREE_LIMIT_REACHED = "PROVIDER_FREE_LIMIT_REACHED"
    DISABLED = "DISABLED"
    ERROR = "ERROR"


class NemotronPersistedState(BaseModel):
    """Persisted usage counters and safety state across restarts."""
    date_str: str = Field(default_factory=lambda: date.today().isoformat())
    requests_today: int = 0
    successful_requests_today: int = 0
    failed_requests_today: int = 0
    max_daily_requests: int = 45
    warning_threshold: int = 40
    last_request_time: float = 0.0
    rate_limited_until: float = 0.0
    quota_exhausted: bool = False
    enabled: bool = True
    manual_override_warning: bool = False


class NemotronUsageGuard:
    """Singleton cost-safety guard controlling NVIDIA Nemotron free-tier invocation."""

    def __init__(self, persistence_dir: Optional[str] = None):
        self.settings = get_settings()
        self.log_dir = Path(persistence_dir or os.path.join(os.path.dirname(__file__), "..", "..", "logs", "diagnostics")).resolve()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.log_dir / "nemotron_quota.json"

        self._lock = threading.RLock()
        self.max_daily_requests = int(getattr(self.settings, "NEMOTRON_MAX_FREE_REQUESTS_PER_DAY", 45))
        self.warning_threshold = int(getattr(self.settings, "NEMOTRON_WARNING_THRESHOLD", 40))
        self.enabled = str(getattr(self.settings, "NEMOTRON_ENABLED", "true")).lower() == "true"
        self.debug_only = str(getattr(self.settings, "NEMOTRON_DEBUG_ONLY", "true")).lower() == "true"
        self.model_name = getattr(self.settings, "NEMOTRON_MODEL", "nvidia/nemotron-3.5-lightning:free")
        self.cooldown_seconds = 2.0

        self.state = NemotronPersistedState(
            max_daily_requests=self.max_daily_requests,
            warning_threshold=self.warning_threshold,
            enabled=self.enabled,
        )
        self._load_state()

    def _load_state(self) -> None:
        """Load persisted quota counters from disk."""
        with self._lock:
            if self.state_file.exists():
                try:
                    with open(self.state_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.state = NemotronPersistedState(**data)
                except Exception as e:
                    logger.debug(f"Could not load Nemotron quota state: {e}")

            # Check if date has rolled over (midnight reset only)
            today_str = date.today().isoformat()
            if self.state.date_str != today_str:
                self.state.date_str = today_str
                self.state.requests_today = 0
                self.state.successful_requests_today = 0
                self.state.failed_requests_today = 0
                self.state.quota_exhausted = False
                self.state.manual_override_warning = False
                self.state.rate_limited_until = 0.0
                self._save_state()

    def _save_state(self) -> None:
        """Persist quota counters to disk."""
        with self._lock:
            try:
                with open(self.state_file, "w", encoding="utf-8") as f:
                    f.write(self.state.model_dump_json(indent=2))
            except Exception as e:
                logger.error(f"Failed to persist Nemotron quota state: {e}")

    def get_current_state(self) -> NemotronState:
        """Evaluate the current operational state of the Nemotron debugger."""
        with self._lock:
            self._load_state()
            if not self.enabled or not self.state.enabled:
                return NemotronState.DISABLED
            if self.model_name not in NVIDIA_ALLOWED_MODELS:
                return NemotronState.ERROR
            if self.state.quota_exhausted:
                return NemotronState.PROVIDER_FREE_LIMIT_REACHED
            if self.state.requests_today >= self.state.max_daily_requests:
                return NemotronState.LOCAL_FREE_LIMIT_REACHED
            now = time.time()
            if now < self.state.rate_limited_until:
                return NemotronState.COOLDOWN
            if self.state.requests_today >= self.state.warning_threshold and not self.state.manual_override_warning:
                return NemotronState.NEAR_FREE_LIMIT
            return NemotronState.AVAILABLE

    def canUseNemotron(self, is_automatic: bool = True) -> Tuple[bool, str]:
        """Perform mandatory 9-point pre-flight cost-safety check before ANY request.
        
        Args:
            is_automatic: True if triggered by automated system failure; False if explicit user CLI command.
        """
        with self._lock:
            self._load_state()

            # 1. Check master enabled flag
            if not self.enabled or not self.state.enabled:
                return False, "DISABLED"

            # 2. Strict model allowlist verification (Never remove ':free')
            if self.model_name not in NVIDIA_ALLOWED_MODELS:
                logger.error(f"🛑 BLOCKED: Unauthorized model '{self.model_name}'. Only {NVIDIA_ALLOWED_MODELS} allowed.")
                return False, f"UNAUTHORIZED_MODEL_{self.model_name}"

            # 3. Provider free quota exhaustion check
            if self.state.quota_exhausted:
                return False, "PROVIDER_FREE_LIMIT_REACHED"

            # 4. Absolute local hard cap check (45 requests)
            if self.state.requests_today >= self.state.max_daily_requests:
                return False, "LOCAL_FREE_LIMIT_REACHED"

            # 5. Warning threshold check (40 requests -> stop automatic usage)
            if is_automatic and self.state.requests_today >= self.state.warning_threshold:
                if not self.state.manual_override_warning:
                    logger.warning("⚠️ Nemotron warning threshold reached (40/45). Automatic debugging stopped.")
                    return False, "NEAR_FREE_LIMIT"

            # 6. Rate limit backoff check
            now = time.time()
            if now < self.state.rate_limited_until:
                wait_sec = round(self.state.rate_limited_until - now, 1)
                return False, f"COOLDOWN_{wait_sec}S"

            # 7. Rapid cooldown check
            if now - self.state.last_request_time < self.cooldown_seconds:
                return False, "COOLDOWN_ACTIVE"

            # 8. All checks passed safely
            return True, "AVAILABLE"

    def can_call(self) -> Tuple[bool, str]:
        """Legacy alias for canUseNemotron."""
        return self.canUseNemotron(is_automatic=True)

    def record_request(self, success: bool = True) -> None:
        """Record an executed Nemotron diagnostic request."""
        with self._lock:
            self.state.requests_today += 1
            if success:
                self.state.successful_requests_today += 1
            else:
                self.state.failed_requests_today += 1
            self.state.last_request_time = time.time()
            self._save_state()
            logger.info(
                f"[NemotronGuard] Request recorded ({self.state.requests_today}/{self.state.max_daily_requests} today, "
                f"Warning: {self.state.warning_threshold})"
            )

    def record_rate_limit(self, is_quota_exhausted: bool = False, retry_after: float = 60.0) -> None:
        """Handle 429 response or provider quota exhaustion from OpenRouter."""
        with self._lock:
            if is_quota_exhausted:
                self.state.quota_exhausted = True
                logger.warning("[NemotronGuard] OpenRouter reports Nemotron free quota exhausted for today. Immediate Hard Stop active.")
            else:
                self.state.rate_limited_until = time.time() + retry_after
                logger.warning(f"[NemotronGuard] Nemotron temporary rate limit backoff active for {retry_after}s.")
            self._save_state()

    def set_enabled(self, enabled: bool) -> None:
        """Toggle debugger availability via manual kill switch."""
        with self._lock:
            self.enabled = enabled
            self.state.enabled = enabled
            self._save_state()
            logger.info(f"Nemotron debugger toggled: {enabled}")

    def set_warning_override(self, override: bool = True) -> None:
        """Allow explicit developer override between warning threshold (40) and hard cap (45)."""
        with self._lock:
            self.state.manual_override_warning = override
            self._save_state()

    def get_status_summary(self) -> Dict[str, Any]:
        """Return formatted diagnostic telemetry for developer CLI."""
        with self._lock:
            self._load_state()
            state_enum = self.get_current_state()
            return {
                "status": state_enum.value,
                "model": self.model_name,
                "requests_today": self.state.requests_today,
                "successful_today": self.state.successful_requests_today,
                "failed_today": self.state.failed_requests_today,
                "warning_threshold": self.state.warning_threshold,
                "max_daily_requests": self.state.max_daily_requests,
                "quota_remaining": max(0, self.state.max_daily_requests - self.state.requests_today),
                "enabled": self.enabled and self.state.enabled,
                "paid_fallback": "BLOCKED (100% Free Guarantee)",
                "billing_automation": "BLOCKED",
                "quota_exhausted": self.state.quota_exhausted,
            }


# Global Singleton Usage Guard
nemotron_guard = NemotronUsageGuard()
