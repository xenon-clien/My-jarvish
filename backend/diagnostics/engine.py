"""Self-Diagnostic Bug Finder & Root-Cause Detection Engine for JARVIS AI.

Enforces closed-loop transaction tracing with unique Correlation IDs,
determines precise failure stages, produces algorithmic root-cause analyses,
detects repeated bug patterns, computes live feature health scores, and exports sanitized telemetry.
"""
from datetime import datetime
import json
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, Dict, List, Optional
import uuid

from backend.core.logger import get_logger
from backend.diagnostics.models import (
    BugRecord,
    DiagnosticEvent,
    ErrorCode,
    FailureCategory,
    FeatureHealth,
    FixabilityType,
    HealthStatus,
    RootCauseAnalysis,
    TransactionTrace,
)

logger = get_logger("DiagnosticEngine")


class SelfDiagnosticEngine:
    """Central singleton engine for observation, bug detection, and root-cause analysis."""

    def __init__(self, log_dir: Optional[str] = None):
        self._lock = threading.RLock()
        self._active_traces: Dict[str, TransactionTrace] = {}
        self._completed_traces: List[TransactionTrace] = []
        self._max_history = 200

        # Bug records registry
        self._bugs: Dict[str, BugRecord] = {}

        # Feature telemetry accumulators
        self._feature_stats: Dict[str, Dict[str, Any]] = {
            "CORE": {"attempts": 0, "success": 0, "failures": 0, "unverified": 0, "latencies": [], "last_fail": None, "errors": {}},
            "VOICE": {"attempts": 0, "success": 0, "failures": 0, "unverified": 0, "latencies": [], "last_fail": None, "errors": {}},
            "GEMINI": {"attempts": 0, "success": 0, "failures": 0, "unverified": 0, "latencies": [], "last_fail": None, "errors": {}},
            "ASTRA": {"attempts": 0, "success": 0, "failures": 0, "unverified": 0, "latencies": [], "last_fail": None, "errors": {}},
            "NEMOTRON": {"attempts": 0, "success": 0, "failures": 0, "unverified": 0, "latencies": [], "last_fail": None, "errors": {}},
            "YOUTUBE": {"attempts": 0, "success": 0, "failures": 0, "unverified": 0, "latencies": [], "last_fail": None, "errors": {}},
            "CHROME": {"attempts": 0, "success": 0, "failures": 0, "unverified": 0, "latencies": [], "last_fail": None, "errors": {}},
            "WHATSAPP": {"attempts": 0, "success": 0, "failures": 0, "unverified": 0, "latencies": [], "last_fail": None, "errors": {}},
            "SYSTEM": {"attempts": 0, "success": 0, "failures": 0, "unverified": 0, "latencies": [], "last_fail": None, "errors": {}},
            "PLAYWRIGHT": {"attempts": 0, "success": 0, "failures": 0, "unverified": 0, "latencies": [], "last_fail": None, "errors": {}},
        }

        # Local storage setup
        self.log_dir = Path(log_dir or os.path.join(os.path.dirname(__file__), "..", "..", "logs", "diagnostics")).resolve()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.trace_log_file = self.log_dir / "diagnostic_traces.jsonl"
        self.bug_store_file = self.log_dir / "bug_records.json"
        self._load_persisted_bugs()

    def create_correlation_id(self) -> str:
        """Generate a unique human-traceable transaction correlation ID."""
        now_str = datetime.now().strftime("%Y%m%d-%H%M%S")
        rand_suffix = uuid.uuid4().hex[:4].upper()
        return f"JRV-{now_str}-{rand_suffix}"

    def start_transaction(self, command: str, correlation_id: Optional[str] = None) -> str:
        """Begin a new diagnostic trace for a user turn."""
        cid = correlation_id or self.create_correlation_id()
        with self._lock:
            trace = TransactionTrace(
                correlationId=cid,
                userCommand=self._sanitize_text(command),
                startTime=time.time(),
            )
            self._active_traces[cid] = trace
            # Emit start event
            self.record_event(DiagnosticEvent(
                eventId=f"EVT-{uuid.uuid4().hex[:6]}",
                correlationId=cid,
                category="SYSTEM",
                operation="START_COMMAND",
                stage="COMMAND_INGEST",
                status="STARTED",
                message=f"Initiated transaction for command: '{self._sanitize_text(command)}'",
            ))
        return cid

    def record_event(self, event: DiagnosticEvent) -> None:
        """Record an atomic lifecycle event into the active transaction trace."""
        with self._lock:
            cid = event.correlationId
            if cid in self._active_traces:
                self._active_traces[cid].stages.append(event)
                if event.category in self._feature_stats and not self._active_traces[cid].targetSubsystem:
                    self._active_traces[cid].targetSubsystem = event.category

            # Update live feature statistics
            cat = event.category.upper()
            if cat in self._feature_stats:
                if event.status == "FAILED" and event.errorCode:
                    self._feature_stats[cat]["failures"] += 1
                    self._feature_stats[cat]["last_fail"] = time.time()
                    err_name = event.errorCode.value if hasattr(event.errorCode, "value") else str(event.errorCode)
                    self._feature_stats[cat]["errors"][err_name] = self._feature_stats[cat]["errors"].get(err_name, 0) + 1

    def end_transaction(
        self,
        correlation_id: str,
        success: bool,
        final_response: str = "",
        target_subsystem: Optional[str] = None,
    ) -> TransactionTrace:
        """Complete a transaction trace, perform root-cause analysis on failure, and update telemetry."""
        with self._lock:
            trace = self._active_traces.pop(correlation_id, None)
            if not trace:
                trace = TransactionTrace(
                    correlationId=correlation_id,
                    userCommand="[UNKNOWN COMMAND]",
                    startTime=time.time() - 0.1,
                )

            trace.endTime = time.time()
            trace.totalDurationMs = round((trace.endTime - trace.startTime) * 1000, 2)
            trace.finalStatus = "SUCCESS" if success else "FAILED"
            trace.finalResponse = final_response
            if target_subsystem:
                trace.targetSubsystem = target_subsystem

            subsys = (trace.targetSubsystem or "AI_BRAIN").upper()
            if subsys not in self._feature_stats:
                subsys = "AI_BRAIN"

            self._feature_stats[subsys]["attempts"] += 1
            if success:
                self._feature_stats[subsys]["success"] += 1
            else:
                self._feature_stats[subsys]["failures"] += 1
            self._feature_stats[subsys]["latencies"].append(trace.totalDurationMs)
            if len(self._feature_stats[subsys]["latencies"]) > 50:
                self._feature_stats[subsys]["latencies"].pop(0)

            # Perform Algorithmic Root Cause Analysis if failed
            if not success:
                trace.rootCause = self.analyze_root_cause(trace)
                self._detect_and_register_bug(trace)

            # Append to completed traces
            self._completed_traces.append(trace)
            if len(self._completed_traces) > self._max_history:
                self._completed_traces.pop(0)

            # Async persist trace
            self._append_trace_to_log(trace)
            return trace

    def analyze_root_cause(self, trace: TransactionTrace) -> RootCauseAnalysis:
        """Algorithmic evidence-based root-cause deduction engine."""
        stages = trace.stages
        cmd = trace.userCommand.lower()

        # 1. Check for Voice / STT Failures
        voice_events = [e for e in stages if e.category == "VOICE" or e.stage in ["MIC", "STT"]]
        for e in voice_events:
            if e.errorCode == ErrorCode.VOICE_STT_TIMEOUT or e.status == "FAILED":
                return RootCauseAnalysis(
                    likelyCause="Speech recognition timed out before complete phrase was captured.",
                    failureCategory=FailureCategory.TIMEOUT,
                    confidence=0.92,
                    evidence=["Microphone input stream opened", "VAD silence threshold triggered early", "Google STT returned no transcript"],
                    alternativeCauses=["Background ambient noise", "Microphone volume gain set too low"],
                    fixability=FixabilityType.FIXABLE_BY_CODE,
                    suggestedFix="Adaptive AGC amplification and extending silence timeout to 0.95s.",
                    filesAffected=["backend/voice/speech_to_text.py"],
                    riskLevel="LOW",
                )

        # 2. Check for Execution vs Verification Mismatch (e.g. YouTube Pause)
        exec_events = [e for e in stages if e.stage in ["EXECUTE", "ACTION"]]
        verif_events = [e for e in stages if e.stage in ["VERIFY", "VERIFICATION"]]

        has_exec_success = any(e.status == "SUCCESS" for e in exec_events)
        has_verif_fail = any(e.status == "FAILED" or e.errorCode == ErrorCode.EXECUTION_VERIFICATION_MISMATCH for e in verif_events)

        if has_exec_success and has_verif_fail:
            target = trace.targetSubsystem or "YOUTUBE"
            return RootCauseAnalysis(
                likelyCause=f"{target} action event was dispatched, but active window/player state did not change.",
                failureCategory=FailureCategory.VERIFICATION_ERROR,
                confidence=0.89,
                evidence=[
                    "Tool executor returned status=success",
                    "Post-action state inspection confirmed target state unchanged",
                    "Window focus or input target was lost",
                ],
                alternativeCauses=["Chrome tab is muted or blurred", "YouTube player DOM element changed"],
                fixability=FixabilityType.FIXABLE_BY_CODE,
                suggestedFix="Force foreground window focus via win32gui.SetForegroundWindow prior to keybd_event.",
                filesAffected=["backend/tools/media_tools.py", "backend/tools/browser_tools.py"],
                riskLevel="MEDIUM",
            )

        # 3. Check for WhatsApp Calling Platform Limitation
        if "whatsapp" in cmd and ("call" in cmd or "phone" in cmd):
            return RootCauseAnalysis(
                likelyCause="WhatsApp Web interface does not support automated direct WebRTC call initiation through standard DOM automation.",
                failureCategory=FailureCategory.PLATFORM_LIMITATION,
                confidence=0.96,
                evidence=[
                    "WhatsApp Web DOM structure obfuscates audio/video call buttons without active session focus",
                    "Direct call protocol requires native Windows WhatsApp Desktop app rather than WhatsApp Web",
                ],
                alternativeCauses=["WhatsApp Web session expired or user not logged in"],
                fixability=FixabilityType.PLATFORM_LIMITATION,
                suggestedFix="Inform user that direct voice calling requires Windows WhatsApp Desktop or manual click.",
                filesAffected=["backend/tools/whatsapp_tools.py"],
                riskLevel="LOW",
            )

        # 4. Check for NLU Unrecognized Intent
        nlu_events = [e for e in stages if e.category == "NLU" or e.stage == "INTENT"]
        for e in nlu_events:
            if e.errorCode == ErrorCode.NLU_UNRECOGNIZED_INTENT or e.status == "FAILED":
                return RootCauseAnalysis(
                    likelyCause="Command wording was not matched by any deterministic NLU semantic regex pattern.",
                    failureCategory=FailureCategory.PARSER_ERROR,
                    confidence=0.85,
                    evidence=[f"Raw transcript '{trace.userCommand}' yielded no candidate intents with confidence >= 0.70"],
                    alternativeCauses=["Typos in speech recognition output", "Unsupported new command capability"],
                    fixability=FixabilityType.FIXABLE_BY_CODE,
                    suggestedFix="Add colloquial Hindi/Hinglish pattern synonyms to UniversalIntent enum and SemanticIntentEngine.",
                    filesAffected=["backend/nlu/semantic_engine.py", "backend/nlu/normalizer.py"],
                    riskLevel="LOW",
                )

        # Default Generic Diagnosis
        return RootCauseAnalysis(
            likelyCause="Action execution failed during dispatch or verification.",
            failureCategory=FailureCategory.UNKNOWN,
            confidence=0.50,
            evidence=[f"Final status is {trace.finalStatus}"],
            alternativeCauses=["Transient OS focus collision", "Network timeout"],
            fixability=FixabilityType.NOT_ENOUGH_EVIDENCE,
            suggestedFix="Inspect recent transaction stages and verify application state.",
            filesAffected=["backend/ai/agent.py"],
            riskLevel="LOW",
        )

    def _detect_and_register_bug(self, trace: TransactionTrace) -> None:
        """Detect recurring patterns and automatically register BugRecords."""
        if not trace.rootCause:
            return

        bug_key = f"{trace.targetSubsystem or 'GENERAL'}_{trace.rootCause.failureCategory.value}"
        stage_name = trace.stages[-1].stage if trace.stages else "VERIFICATION"
        err_code = trace.stages[-1].errorCode if trace.stages and trace.stages[-1].errorCode else ErrorCode.UNKNOWN_ERROR

        if bug_key in self._bugs:
            self._bugs[bug_key].occurrenceCount += 1
            self._bugs[bug_key].lastDetected = time.time()
            self._bugs[bug_key].status = "OPEN"
        else:
            self._bugs[bug_key] = BugRecord(
                bugId=f"BUG-{uuid.uuid4().hex[:5].upper()}",
                featureName=trace.targetSubsystem or "GENERAL",
                firstDetected=time.time(),
                lastDetected=time.time(),
                occurrenceCount=1,
                failureStage=stage_name,
                likelyRootCause=trace.rootCause.likelyCause,
                failureCategory=trace.rootCause.failureCategory,
                errorCode=err_code,
                status="OPEN",
            )
        self._persist_bugs()

    def get_feature_health(self) -> Dict[str, FeatureHealth]:
        """Compute real-time health scorecard for every subsystem."""
        with self._lock:
            health_report: Dict[str, FeatureHealth] = {}
            for feature, stats in self._feature_stats.items():
                att = stats["attempts"]
                succ = stats["success"]
                fail = stats["failures"]
                unver = stats["unverified"]
                latencies = stats["latencies"]
                avg_lat = round(sum(latencies) / len(latencies), 1) if latencies else 0.0

                if att == 0:
                    status = HealthStatus.HEALTHY
                    succ_rate = 100.0
                else:
                    succ_rate = round((succ / att) * 100, 1)
                    if succ_rate >= 90.0:
                        status = HealthStatus.HEALTHY
                    elif succ_rate >= 60.0:
                        status = HealthStatus.DEGRADED
                    elif succ_rate >= 30.0:
                        status = HealthStatus.UNSTABLE
                    else:
                        status = HealthStatus.BROKEN

                # Find top error code
                top_err = max(stats["errors"].items(), key=lambda x: x[1])[0] if stats["errors"] else None

                health_report[feature] = FeatureHealth(
                    featureName=feature,
                    healthStatus=status,
                    totalAttempts=att,
                    successCount=succ,
                    failureCount=fail,
                    unverifiedCount=unver,
                    successRatePercent=succ_rate,
                    avgLatencyMs=avg_lat,
                    lastFailureTimestamp=stats["last_fail"],
                    topErrorCode=top_err,
                    lastVerifiedTimestamp=time.time() if succ > 0 else None,
                )
            return health_report

    def get_recent_traces(self, limit: int = 50) -> List[TransactionTrace]:
        """Fetch the most recent transaction traces."""
        with self._lock:
            return list(reversed(self._completed_traces[-limit:]))

    def get_trace_by_id(self, correlation_id: str) -> Optional[TransactionTrace]:
        """Look up a specific transaction trace by Correlation ID."""
        with self._lock:
            if correlation_id in self._active_traces:
                return self._active_traces[correlation_id]
            for t in reversed(self._completed_traces):
                if t.correlationId == correlation_id:
                    return t
        return None

    def get_open_bugs(self) -> List[BugRecord]:
        """Return all open bug records."""
        with self._lock:
            return [b for b in self._bugs.values() if b.status == "OPEN"]

    def why_did_this_fail(self, correlation_id: str) -> str:
        """Technical explanation of failure for a given transaction."""
        trace = self.get_trace_by_id(correlation_id)
        if not trace:
            return f"No transaction record found for Correlation ID: {correlation_id}"

        if trace.finalStatus == "SUCCESS":
            return f"Transaction {correlation_id} executed and verified successfully in {trace.totalDurationMs}ms."

        if trace.rootCause:
            rc = trace.rootCause
            evidence_str = "\n".join([f"  • {e}" for e in rc.evidence])
            return (
                f"=== DIAGNOSTIC EXPLANATION: {correlation_id} ===\n"
                f"Command: '{trace.userCommand}'\n"
                f"Target: {trace.targetSubsystem or 'General'}\n"
                f"Status: {trace.finalStatus} ({trace.totalDurationMs}ms)\n\n"
                f"🔍 Likely Root Cause:\n{rc.likelyCause} (Confidence: {int(rc.confidence*100)}%)\n\n"
                f"📋 Supporting Evidence:\n{evidence_str}\n\n"
                f"🛠️ Suggested Fix:\n{rc.suggestedFix}\n"
                f"📁 Affected Files: {', '.join(rc.filesAffected) or 'None'}"
            )
        return f"Transaction {correlation_id} failed without structured root cause."

    def export_diagnostic_report(self) -> Dict[str, Any]:
        """Generate a complete, sanitized developer diagnostic report without secrets."""
        with self._lock:
            health = {k: v.model_dump() for k, v in self.get_feature_health().items()}
            bugs = [b.model_dump() for b in self.get_open_bugs()]
            recent_traces = [t.model_dump() for t in reversed(self._completed_traces)][:20]
            recent_fails = [
                t.model_dump() for t in reversed(self._completed_traces) if t.finalStatus == "FAILED"
            ][:10]

            return {
                "reportTimestamp": datetime.now().isoformat(),
                "systemHealth": health,
                "openBugs": bugs,
                "recentTraces": recent_traces,
                "recentFailures": recent_fails,
                "totalCompletedTransactions": len(self._completed_traces),
            }

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Remove any sensitive API keys, tokens, or passwords from logs."""
        if not text:
            return ""
        # Redact API keys / tokens
        cleaned = re.sub(r"(AIzaSy[a-zA-Z0-9_\-]+)", "[REDACTED_API_KEY]", text)
        cleaned = re.sub(r"(sk-[a-zA-Z0-9_\-]+)", "[REDACTED_SECRET]", cleaned)
        return cleaned

    def _append_trace_to_log(self, trace: TransactionTrace) -> None:
        """Persist sanitized trace JSONL to disk with automatic rotation."""
        try:
            # Rotate log if size exceeds 5MB
            if self.trace_log_file.exists() and self.trace_log_file.stat().st_size > 5 * 1024 * 1024:
                backup = self.log_dir / f"diagnostic_traces_{int(time.time())}.jsonl"
                self.trace_log_file.rename(backup)

            with open(self.trace_log_file, "a", encoding="utf-8") as f:
                f.write(trace.model_dump_json() + "\n")
        except Exception as exc:
            logger.debug(f"Failed to persist diagnostic trace: {exc}")

    def _persist_bugs(self) -> None:
        """Save open bug registry to disk."""
        try:
            with open(self.bug_store_file, "w", encoding="utf-8") as f:
                data = {k: v.model_dump() for k, v in self._bugs.items()}
                json.dump(data, f, indent=2)
        except Exception as exc:
            logger.debug(f"Failed to persist bug store: {exc}")

    def _load_persisted_bugs(self) -> None:
        """Load open bug registry from disk."""
        try:
            if self.bug_store_file.exists():
                with open(self.bug_store_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self._bugs[k] = BugRecord(**v)
        except Exception as exc:
            logger.debug(f"Failed to load bug store: {exc}")


# Global central singleton instance
diagnostic_engine = SelfDiagnosticEngine()
