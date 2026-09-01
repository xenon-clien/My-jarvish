"""Structured Command Tracer for JARVIS.

Assigns unique sequential Command IDs (CMD-XXXX) and records the complete
deterministic execution lifecycle from raw speech to tool result.
"""
from datetime import datetime
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.core.logger import get_logger

logger = get_logger("CommandTracer")


class CommandTrace(BaseModel):
    """Complete lifecycle trace for a single user command turn."""
    command_id: str
    raw_transcript: str = ""
    normalized_transcript: str = ""
    domain: str = "general"
    intent: str = "UNKNOWN"
    arguments: Dict[str, Any] = Field(default_factory=dict)
    candidate_tools: List[str] = Field(default_factory=list)
    selected_tool: Optional[str] = None
    executed_function: Optional[str] = None
    active_app: Optional[str] = None
    active_window: Optional[str] = None
    active_url: Optional[str] = None
    execution_start: float = Field(default_factory=time.time)
    execution_end: Optional[float] = None
    duration_ms: float = 0.0
    verification_status: str = "UNVERIFIED"  # PASS, FAIL, RECOVERED, UNVERIFIED
    verification_details: Optional[str] = None
    retry_count: int = 0
    fallback_used: bool = False
    error: Optional[str] = None
    playwright_trace_path: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CommandTracer:
    """Singleton engine for recording and querying structured command traces."""

    def __init__(self, log_dir: Optional[str] = None):
        self._lock = threading.RLock()
        self._counter = 1000
        self._active_traces: Dict[str, CommandTrace] = {}
        self._completed_traces: List[CommandTrace] = []
        self._max_in_memory = 200

        self.log_dir = Path(log_dir or os.path.join(os.path.dirname(__file__), "..", "..", "logs", "observability")).resolve()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.trace_file = self.log_dir / "command_traces.jsonl"
        self._init_counter_from_logs()

    def _init_counter_from_logs(self) -> None:
        """Initialize sequential ID counter from existing log file."""
        if self.trace_file.exists():
            try:
                with open(self.trace_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            cid = data.get("command_id", "")
                            if cid.startswith("CMD-"):
                                try:
                                    num = int(cid.split("-")[1])
                                    if num >= self._counter:
                                        self._counter = num + 1
                                except ValueError:
                                    pass
            except Exception as e:
                logger.debug(f"Could not parse prior trace count: {e}")

    def next_command_id(self) -> str:
        """Generate the next monotonic sequential Command ID."""
        with self._lock:
            self._counter += 1
            return f"CMD-{self._counter}"

    def start_trace(self, raw_transcript: str, command_id: Optional[str] = None) -> CommandTrace:
        """Initialize and register a new CommandTrace."""
        cid = command_id or self.next_command_id()
        trace = CommandTrace(
            command_id=cid,
            raw_transcript=raw_transcript,
            execution_start=time.time(),
        )
        with self._lock:
            self._active_traces[cid] = trace
        logger.info(f"📍 [{cid}] START COMMAND TRACE: '{raw_transcript}'")
        return trace

    def update_trace(
        self,
        command_id: str,
        normalized_transcript: Optional[str] = None,
        domain: Optional[str] = None,
        intent: Optional[str] = None,
        arguments: Optional[Dict[str, Any]] = None,
        candidate_tools: Optional[List[str]] = None,
        selected_tool: Optional[str] = None,
        executed_function: Optional[str] = None,
        active_app: Optional[str] = None,
        active_window: Optional[str] = None,
        active_url: Optional[str] = None,
        playwright_trace_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[CommandTrace]:
        """Update intermediate lifecycle state on an active trace."""
        with self._lock:
            trace = self._active_traces.get(command_id)
            if not trace:
                return None
            if normalized_transcript is not None:
                trace.normalized_transcript = normalized_transcript
            if domain is not None:
                trace.domain = domain
            if intent is not None:
                trace.intent = intent
            if arguments is not None:
                trace.arguments = arguments
            if candidate_tools is not None:
                trace.candidate_tools = candidate_tools
            if selected_tool is not None:
                trace.selected_tool = selected_tool
            if executed_function is not None:
                trace.executed_function = executed_function
            if active_app is not None:
                trace.active_app = active_app
            if active_window is not None:
                trace.active_window = active_window
            if active_url is not None:
                trace.active_url = active_url
            if playwright_trace_path is not None:
                trace.playwright_trace_path = playwright_trace_path
            if metadata:
                trace.metadata.update(metadata)
            return trace

    def finish_trace(
        self,
        command_id: str,
        verification_status: str = "PASS",
        verification_details: Optional[str] = None,
        error: Optional[str] = None,
        retry_count: int = 0,
        fallback_used: bool = False,
    ) -> Optional[CommandTrace]:
        """Finalize, log, and persist the command trace."""
        with self._lock:
            trace = self._active_traces.pop(command_id, None)
            if not trace:
                return None

            trace.execution_end = time.time()
            trace.duration_ms = round((trace.execution_end - trace.execution_start) * 1000, 2)
            trace.verification_status = verification_status
            trace.verification_details = verification_details
            trace.error = error
            trace.retry_count = retry_count
            trace.fallback_used = fallback_used

            self._completed_traces.append(trace)
            if len(self._completed_traces) > self._max_in_memory:
                self._completed_traces.pop(0)

            # Persist to JSONL file asynchronously / thread-safely
            try:
                with open(self.trace_file, "a", encoding="utf-8") as f:
                    f.write(trace.model_dump_json() + "\n")
            except Exception as e:
                logger.error(f"Failed to persist command trace {command_id}: {e}")

            logger.info(
                f"🏁 [{command_id}] FINISH: {trace.domain}.{trace.intent} -> "
                f"tool={trace.selected_tool} status={verification_status} ({trace.duration_ms}ms)"
            )
            return trace

    def get_trace(self, command_id: str) -> Optional[CommandTrace]:
        """Retrieve trace by ID from active or completed records."""
        with self._lock:
            if command_id in self._active_traces:
                return self._active_traces[command_id]
            for t in reversed(self._completed_traces):
                if t.command_id == command_id:
                    return t
        return None

    def get_recent_traces(self, limit: int = 10) -> List[CommandTrace]:
        """Get list of most recent completed command traces."""
        with self._lock:
            return list(reversed(self._completed_traces[-limit:]))

    def format_debug_panel(self, command_id: str) -> str:
        """Format human-readable developer debug panel for CLI / logs."""
        trace = self.get_trace(command_id)
        if not trace:
            return f"No trace found for {command_id}"

        lines = [
            f"COMMAND ID:  {trace.command_id}",
            f"RAW:         {trace.raw_transcript}",
            f"NORMALIZED:  {trace.normalized_transcript}",
            f"DOMAIN:      {trace.domain}",
            f"INTENT:      {trace.intent}",
            f"ARGUMENTS:   {json.dumps(trace.arguments)}",
            f"CANDIDATES:  {trace.candidate_tools}",
            f"SELECTED:    {trace.selected_tool}",
            f"EXECUTED:    {trace.executed_function}",
            f"ACTIVE APP:  {trace.active_app or 'N/A'}",
            f"ACTIVE URL:  {trace.active_url or 'N/A'}",
            f"DURATION:    {trace.duration_ms} ms",
            f"VERIFY:      {trace.verification_status} ({trace.verification_details or 'None'})",
        ]
        if trace.error:
            lines.append(f"ERROR:       {trace.error}")
        if trace.playwright_trace_path:
            lines.append(f"TRACE FILE:  {trace.playwright_trace_path}")
        return "\n".join(lines)


# Global Singleton Command Tracer
command_tracer = CommandTracer()
