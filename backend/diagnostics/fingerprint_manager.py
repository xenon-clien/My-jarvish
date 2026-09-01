"""Error Fingerprint Manager and Diagnostic Cache for JARVIS.

Computes unique deterministic fingerprints for runtime failures and caches
diagnostic root-cause analyses to prevent duplicate API consumption.
"""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from backend.core.logger import get_logger

logger = get_logger("ErrorFingerprintManager")


class DiagnosticCacheEntry(BaseModel):
    """Cached diagnostic analysis for a specific failure fingerprint."""
    fingerprint: str
    issue_type: str
    affected_layer: str
    root_cause: str
    confidence: float
    reproduction_test: str
    recommended_fix: str
    timestamp: float = Field(default_factory=time.time)
    occurrence_count: int = 1


class ErrorFingerprintManager:
    """Computes error fingerprints and manages caching of diagnostic analyses."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.log_dir = Path(cache_dir or os.path.join(os.path.dirname(__file__), "..", "..", "logs", "diagnostics")).resolve()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.log_dir / "diagnosis_cache.json"

        self._lock = threading.RLock()
        self._cache: Dict[str, DiagnosticCacheEntry] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cached diagnoses from disk."""
        with self._lock:
            if self.cache_file.exists():
                try:
                    with open(self.cache_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for k, v in data.items():
                            self._cache[k] = DiagnosticCacheEntry(**v)
                except Exception as e:
                    logger.debug(f"Could not load diagnosis cache: {e}")

    def _save_cache(self) -> None:
        """Persist diagnosis cache to disk."""
        with self._lock:
            try:
                with open(self.cache_file, "w", encoding="utf-8") as f:
                    data = {k: v.model_dump() for k, v in self._cache.items()}
                    json.dump(data, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to persist diagnosis cache: {e}")

    def compute_fingerprint(
        self,
        domain: str,
        intent: str,
        error_type: str,
        affected_module: Optional[str] = None,
        target_info: Optional[str] = None,
    ) -> str:
        """Generate a deterministic normalized fingerprint hash & human-readable tag."""
        norm_domain = (domain or "general").strip().lower()
        norm_intent = (intent or "unknown").strip().lower()
        norm_err = (error_type or "runtime_error").strip().upper()
        norm_mod = (affected_module or "core").strip().lower()
        norm_tgt = (target_info or "").strip().lower()

        raw_str = f"{norm_domain}:{norm_intent}:{norm_err}:{norm_mod}:{norm_tgt}"
        short_hash = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:8].upper()
        return f"{norm_domain.upper()}-{norm_err}-{short_hash}"

    def get_cached_diagnosis(self, fingerprint: str) -> Optional[DiagnosticCacheEntry]:
        """Check if an unresolved diagnosis already exists for this fingerprint."""
        with self._lock:
            entry = self._cache.get(fingerprint)
            if entry:
                entry.occurrence_count += 1
                self._save_cache()
                logger.info(f"⚡ Reused cached Nemotron diagnosis for fingerprint: {fingerprint}")
                return entry
            return None

    def store_diagnosis(
        self,
        fingerprint: str,
        issue_type: str,
        affected_layer: str,
        root_cause: str,
        confidence: float,
        reproduction_test: str,
        recommended_fix: str,
    ) -> DiagnosticCacheEntry:
        """Cache a newly generated Nemotron diagnostic report."""
        with self._lock:
            entry = DiagnosticCacheEntry(
                fingerprint=fingerprint,
                issue_type=issue_type,
                affected_layer=affected_layer,
                root_cause=root_cause,
                confidence=confidence,
                reproduction_test=reproduction_test,
                recommended_fix=recommended_fix,
                timestamp=time.time(),
            )
            self._cache[fingerprint] = entry
            self._save_cache()
            return entry


# Global Singleton Fingerprint Manager
fingerprint_manager = ErrorFingerprintManager()
