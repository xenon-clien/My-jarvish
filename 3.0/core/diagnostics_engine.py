"""JARVIS 3.0 - Diagnostics & Root Cause Analysis Engine.

Tracks end-to-end transaction traces, logs structured error telemetry,
and computes algorithmic root causes for failed actions.
"""
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional
import uuid

from core.logger import get_logger

logger = get_logger("Diagnostics")


class FailureCategory(str, Enum):
    SELECTOR_CHANGED = "SELECTOR_CHANGED"
    TIMEOUT = "TIMEOUT"
    WINDOW_NOT_FOCUSED = "WINDOW_NOT_FOCUSED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    APPLICATION_NOT_RUNNING = "APPLICATION_NOT_RUNNING"
    NETWORK_ERROR = "NETWORK_ERROR"
    AI_RATE_LIMIT = "AI_RATE_LIMIT"
    UNKNOWN = "UNKNOWN"


class RootCauseReport(BaseModel := type("BaseModel", (), {})):
    pass


class DiagnosticEvent:
    def __init__(
        self,
        category: str,
        operation: str,
        stage: str,
        status: str,
        message: str,
        correlation_id: str,
        duration_ms: float = 0.0,
        error_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.event_id = f"EVT-{uuid.uuid4().hex[:6].upper()}"
        self.correlation_id = correlation_id
        self.category = category
        self.operation = operation
        self.stage = stage
        self.status = status
        self.message = message
        self.duration_ms = duration_ms
        self.error_code = error_code
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "correlation_id": self.correlation_id,
            "category": self.category,
            "operation": self.operation,
            "stage": self.stage,
            "status": self.status,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "error_code": self.error_code,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class TransactionTrace:
    def __init__(self, correlation_id: str, command: str):
        self.correlation_id = correlation_id
        self.command = command
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.total_duration_ms: float = 0.0
        self.final_status: str = "IN_PROGRESS"
        self.stages: List[DiagnosticEvent] = []
        self.target_subsystem: Optional[str] = None
        self.root_cause: Optional[Dict[str, Any]] = None

    def finish(self, success: bool, final_response: str = "") -> None:
        self.end_time = time.time()
        self.total_duration_ms = round((self.end_time - self.start_time) * 1000, 2)
        self.final_status = "SUCCESS" if success else "FAILED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "command": self.command,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_duration_ms": self.total_duration_ms,
            "final_status": self.final_status,
            "target_subsystem": self.target_subsystem,
            "root_cause": self.root_cause,
            "stages": [s.to_dict() for s in self.stages],
        }


class DiagnosticsEngine:
    """Central manager for telemetry tracing, health metrics, and failure explanation."""

    def __init__(self):
        self._traces: Dict[str, TransactionTrace] = {}
        self._history: List[TransactionTrace] = []
        self._lock = threading.RLock()

    def create_correlation_id(self) -> str:
        now_str = datetime.now().strftime("%Y%m%d-%H%M%S")
        rand = uuid.uuid4().hex[:4].upper()
        return f"JRV-{now_str}-{rand}"

    def start_trace(self, command: str) -> str:
        cid = self.create_correlation_id()
        with self._lock:
            trace = TransactionTrace(correlation_id=cid, command=command)
            self._traces[cid] = trace
        return cid

    def record_event(
        self,
        correlation_id: str,
        category: str,
        operation: str,
        stage: str,
        status: str,
        message: str,
        duration_ms: float = 0.0,
        error_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self._lock:
            if correlation_id in self._traces:
                ev = DiagnosticEvent(
                    category=category,
                    operation=operation,
                    stage=stage,
                    status=status,
                    message=message,
                    correlation_id=correlation_id,
                    duration_ms=duration_ms,
                    error_code=error_code,
                    metadata=metadata,
                )
                self._traces[correlation_id].stages.append(ev)

    def end_trace(self, correlation_id: str, success: bool, final_response: str = "") -> TransactionTrace:
        with self._lock:
            trace = self._traces.pop(correlation_id, None)
            if not trace:
                trace = TransactionTrace(correlation_id=correlation_id, command="")
            trace.finish(success, final_response)

            if not success:
                trace.root_cause = self.deduce_root_cause(trace)

            self._history.append(trace)
            if len(self._history) > 100:
                self._history.pop(0)
            return trace

    def deduce_root_cause(self, trace: TransactionTrace) -> Dict[str, Any]:
        """Analyze transaction stages and determine root cause."""
        cmd = trace.command.lower()
        stages = trace.stages

        for s in stages:
            if "timeout" in s.message.lower() or s.error_code == "TIMEOUT":
                return {
                    "likely_cause": "The operation timed out while waiting for UI response.",
                    "category": FailureCategory.TIMEOUT.value,
                    "confidence": 0.90,
                    "evidence": [s.message],
                    "suggested_fix": "Increase timeout or ensure application has active network connectivity.",
                }
            if "browser_window_missing" in s.message.lower():
                return {
                    "likely_cause": "The target browser window was not open or could not be focused.",
                    "category": FailureCategory.APPLICATION_NOT_RUNNING.value,
                    "confidence": 0.95,
                    "evidence": [s.message],
                    "suggested_fix": "Launch Google Chrome and navigate to the requested page first.",
                }

        return {
            "likely_cause": "The requested action failed during execution or closed-loop verification.",
            "category": FailureCategory.UNKNOWN.value,
            "confidence": 0.60,
            "evidence": [s.message for s in stages if s.status == "FAILED"],
            "suggested_fix": "Check application status and retry command.",
        }

    def explain_failure(self, correlation_id: str) -> str:
        """Produce a helpful explanation of a failure."""
        with self._lock:
            for t in reversed(self._history):
                if t.correlation_id == correlation_id:
                    if t.final_status == "SUCCESS":
                        return f"Transaction {correlation_id} succeeded in {t.total_duration_ms}ms."
                    rc = t.root_cause or {}
                    return (
                        f"Command: '{t.command}' failed.\n"
                        f"Cause: {rc.get('likely_cause', 'Unknown error')}\n"
                        f"Fix: {rc.get('suggested_fix', 'Please retry.')}"
                    )
        return f"No transaction found for ID {correlation_id}"


# Global DiagnosticsEngine singleton
diagnostics_engine = DiagnosticsEngine()
