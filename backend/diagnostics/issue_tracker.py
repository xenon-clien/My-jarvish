"""Issue Tracker for JARVIS Diagnostic Architecture.

Tracks active and resolved bugs, failures, and empirical root-cause diagnoses.
"""
from datetime import datetime
import json
import os
from pathlib import Path
import threading
import time
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from backend.core.logger import get_logger

logger = get_logger("IssueTracker")


class DiagnosticIssue(BaseModel):
    """Represents an isolated, trackable runtime issue or bug."""
    issue_id: str
    title: str
    command: str = ""
    domain: str = "general"
    severity: str = "ERROR"  # INFO, WARNING, ERROR, CRITICAL
    status: str = "OPEN"     # OPEN, DIAGNOSED, TESTING, RESOLVED
    expected: str = ""
    actual: str = ""
    root_cause: Optional[str] = None
    affected_layer: Optional[str] = None
    confidence: float = 0.0
    proposed_fix: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    resolved_at: Optional[float] = None


class IssueTracker:
    """Singleton repository for active and resolved diagnostic issues."""

    def __init__(self, persistence_dir: Optional[str] = None):
        self.log_dir = Path(persistence_dir or os.path.join(os.path.dirname(__file__), "..", "..", "logs", "diagnostics")).resolve()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.issue_file = self.log_dir / "issues_registry.json"

        self._lock = threading.RLock()
        self._issues: Dict[str, DiagnosticIssue] = {}
        self._counters: Dict[str, int] = {"YT": 0, "VOICE": 0, "CHROME": 0, "SYS": 0, "WA": 0, "CORE": 0}
        self._load_issues()

    def _load_issues(self) -> None:
        """Load persisted issues from disk."""
        with self._lock:
            if self.issue_file.exists():
                try:
                    with open(self.issue_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for k, v in data.items():
                            issue = DiagnosticIssue(**v)
                            self._issues[k] = issue
                            prefix = k.split("-")[0]
                            num = int(k.split("-")[1])
                            if prefix in self._counters and num > self._counters[prefix]:
                                self._counters[prefix] = num
                except Exception as e:
                    logger.debug(f"Could not load issues: {e}")

    def _save_issues(self) -> None:
        """Persist issues registry to disk."""
        with self._lock:
            try:
                with open(self.issue_file, "w", encoding="utf-8") as f:
                    data = {k: v.model_dump() for k, v in self._issues.items()}
                    json.dump(data, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to persist issues registry: {e}")

    def create_issue(
        self,
        domain: str,
        title: str,
        command: str = "",
        expected: str = "",
        actual: str = "",
        severity: str = "ERROR",
        root_cause: Optional[str] = None,
        affected_layer: Optional[str] = None,
        confidence: float = 0.0,
        proposed_fix: Optional[str] = None,
    ) -> DiagnosticIssue:
        """Register a new diagnostic issue."""
        with self._lock:
            prefix_map = {
                "youtube": "YT",
                "voice": "VOICE",
                "chrome": "CHROME",
                "whatsapp": "WA",
                "system": "SYS",
                "files": "SYS",
            }
            p = prefix_map.get(domain.lower(), "CORE")
            self._counters[p] = self._counters.get(p, 0) + 1
            issue_id = f"{p}-{self._counters[p]:03d}"

            issue = DiagnosticIssue(
                issue_id=issue_id,
                title=title,
                command=command,
                domain=domain,
                severity=severity,
                status="DIAGNOSED" if root_cause else "OPEN",
                expected=expected,
                actual=actual,
                root_cause=root_cause,
                affected_layer=affected_layer,
                confidence=confidence,
                proposed_fix=proposed_fix,
            )
            self._issues[issue_id] = issue
            self._save_issues()
            logger.info(f"📋 Registered Issue #{issue_id}: '{title}' ({severity})")
            return issue

    def get_open_issues(self) -> List[DiagnosticIssue]:
        """Return list of active unresolved issues."""
        with self._lock:
            return [i for i in self._issues.values() if i.status != "RESOLVED"]

    def get_latest_issue(self) -> Optional[DiagnosticIssue]:
        """Return the most recently created issue."""
        with self._lock:
            if not self._issues:
                return None
            return list(self._issues.values())[-1]

    def resolve_issue(self, issue_id: str) -> bool:
        """Mark an issue as verified resolved."""
        with self._lock:
            if issue_id in self._issues:
                self._issues[issue_id].status = "RESOLVED"
                self._issues[issue_id].resolved_at = time.time()
                self._save_issues()
                logger.info(f"✅ Resolved Issue #{issue_id}")
                return True
            return False


# Global Singleton Issue Tracker
issue_tracker = IssueTracker()
