"""Persistent Audit History Engine for PC Problem Solver Diagnostics and Repairs."""
import json
import os
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

from backend.core.logger import get_logger
from backend.problem_solver.models import ProblemCategory, RepairHistoryEntry

logger = get_logger("RepairHistory")


class RepairHistory:
    """Stores and retrieves safe audit history of PC problem diagnostics and repair attempts."""

    _entries: List[RepairHistoryEntry] = []
    _history_file = os.path.join(os.path.expanduser("~"), ".jarvis_repair_history.json")

    @classmethod
    def record_entry(
        cls,
        problem_text: str,
        category: ProblemCategory,
        diagnosis_summary: str,
        root_cause_title: Optional[str] = None,
        repair_summary: Optional[str] = None,
        verification_passed: bool = False,
        rollback_applied: bool = False,
    ) -> RepairHistoryEntry:
        """Record a completed diagnosis/repair event."""
        entry = RepairHistoryEntry(
            entry_id=f"hist_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(),
            problem_text=problem_text,
            category=category,
            diagnosis_summary=diagnosis_summary,
            root_cause_title=root_cause_title,
            repair_summary=repair_summary,
            verification_passed=verification_passed,
            rollback_applied=rollback_applied,
        )
        cls._entries.append(entry)
        cls._save_to_disk()
        logger.info(f"Recorded repair history entry: {entry.entry_id} ({category})")
        return entry

    @classmethod
    def get_recent_entries(cls, limit: int = 10) -> List[RepairHistoryEntry]:
        """Retrieve recent troubleshooting history entries."""
        cls._load_from_disk()
        return sorted(cls._entries, key=lambda x: x.timestamp, reverse=True)[:limit]

    @classmethod
    def _save_to_disk(cls):
        """Save history safely to JSON file."""
        try:
            data = [e.model_dump(mode="json") for e in cls._entries]
            with open(cls._history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.debug(f"History save error: {e}")

    @classmethod
    def _load_from_disk(cls):
        """Load history from JSON file."""
        if not os.path.exists(cls._history_file):
            return
        try:
            with open(cls._history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                cls._entries = [RepairHistoryEntry(**d) for d in data]
        except Exception as e:
            logger.debug(f"History load error: {e}")
