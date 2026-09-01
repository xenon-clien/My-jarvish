"""Standardized Data Models, Enums, and Schemas for JARVIS Self-Diagnostic Bug Finder Engine."""
from datetime import datetime
from enum import Enum
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"       # 🟢 90%+ success, low latency
    DEGRADED = "DEGRADED"     # 🟡 60-89% success or high latency
    UNSTABLE = "UNSTABLE"     # 🟠 30-59% success or frequent errors
    BROKEN = "BROKEN"         # 🔴 <30% success or fatal block
    UNKNOWN = "UNKNOWN"       # ⚪ Not enough data


class FailureCategory(str, Enum):
    CODE_BUG = "CODE_BUG"
    LOGIC_BUG = "LOGIC_BUG"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    ASYNC_ERROR = "ASYNC_ERROR"
    RACE_CONDITION = "RACE_CONDITION"
    TIMEOUT = "TIMEOUT"
    STATE_ERROR = "STATE_ERROR"
    STT_ERROR = "STT_ERROR"
    AI_ERROR = "AI_ERROR"
    PARSER_ERROR = "PARSER_ERROR"
    EXECUTOR_ERROR = "EXECUTOR_ERROR"
    VERIFICATION_ERROR = "VERIFICATION_ERROR"
    API_ERROR = "API_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    PERMISSION_ERROR = "PERMISSION_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    BROWSER_ERROR = "BROWSER_ERROR"
    WINDOWS_ERROR = "WINDOWS_ERROR"
    WHATSAPP_ERROR = "WHATSAPP_ERROR"
    FILE_ERROR = "FILE_ERROR"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"
    PLATFORM_LIMITATION = "PLATFORM_LIMITATION"
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
    UNKNOWN = "UNKNOWN"


class FixabilityType(str, Enum):
    FIXABLE_BY_CODE = "FIXABLE_BY_CODE"
    FIXABLE_BY_CONFIGURATION = "FIXABLE_BY_CONFIGURATION"
    FIXABLE_BY_RETRY = "FIXABLE_BY_RETRY"
    REQUIRES_USER_PERMISSION = "REQUIRES_USER_PERMISSION"
    REQUIRES_API_KEY = "REQUIRES_API_KEY"
    REQUIRES_EXTERNAL_SERVICE = "REQUIRES_EXTERNAL_SERVICE"
    PLATFORM_LIMITATION = "PLATFORM_LIMITATION"
    NOT_ENOUGH_EVIDENCE = "NOT_ENOUGH_EVIDENCE"


class ErrorCode(str, Enum):
    # Voice & Audio
    VOICE_MIC_UNAVAILABLE = "VOICE_MIC_UNAVAILABLE"
    VOICE_MIC_PERMISSION_DENIED = "VOICE_MIC_PERMISSION_DENIED"
    VOICE_AUDIO_SILENT = "VOICE_AUDIO_SILENT"
    VOICE_STT_TIMEOUT = "VOICE_STT_TIMEOUT"
    VOICE_STT_ERROR = "VOICE_STT_ERROR"
    VOICE_EMPTY_TRANSCRIPT = "VOICE_EMPTY_TRANSCRIPT"
    VOICE_DUPLICATE_SUPPRESSED = "VOICE_DUPLICATE_SUPPRESSED"

    # NLU & Intent
    NLU_UNRECOGNIZED_INTENT = "NLU_UNRECOGNIZED_INTENT"
    NLU_LOW_CONFIDENCE = "NLU_LOW_CONFIDENCE"
    NLU_ENTITY_MISSING = "NLU_ENTITY_MISSING"
    NLU_AMBIGUOUS_POLYSEMY = "NLU_AMBIGUOUS_POLYSEMY"

    # Routing & Execution
    ROUTER_NO_TOOL_MATCH = "ROUTER_NO_TOOL_MATCH"
    EXEC_TOOL_NOT_FOUND = "EXEC_TOOL_NOT_FOUND"
    EXEC_INVALID_ARGUMENTS = "EXEC_INVALID_ARGUMENTS"
    EXEC_RUNTIME_ERROR = "EXEC_RUNTIME_ERROR"
    EXEC_TIMEOUT = "EXEC_TIMEOUT"
    EXECUTION_VERIFICATION_MISMATCH = "EXECUTION_VERIFICATION_MISMATCH"

    # Target Subsystems
    YOUTUBE_WINDOW_BLURRED = "YOUTUBE_WINDOW_BLURRED"
    YOUTUBE_PLAYER_UNCHANGED = "YOUTUBE_PLAYER_UNCHANGED"
    YOUTUBE_TAB_NOT_FOUND = "YOUTUBE_TAB_NOT_FOUND"
    BROWSER_NOT_RUNNING = "BROWSER_NOT_RUNNING"
    BROWSER_NAVIGATION_FAILED = "BROWSER_NAVIGATION_FAILED"
    WHATSAPP_NOT_LOGGED_IN = "WHATSAPP_NOT_LOGGED_IN"
    WHATSAPP_CONTACT_NOT_FOUND = "WHATSAPP_CONTACT_NOT_FOUND"
    WHATSAPP_CALL_UNSUPPORTED = "WHATSAPP_CALL_UNSUPPORTED"
    APP_LAUNCH_FAILED = "APP_LAUNCH_FAILED"
    SYSTEM_VOLUME_MUTED = "SYSTEM_VOLUME_MUTED"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    PLATFORM_CAPABILITY_LIMITATION = "PLATFORM_CAPABILITY_LIMITATION"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class DiagnosticEvent(BaseModel):
    """Standardized event record emitted at every stage of execution."""
    eventId: str
    correlationId: str
    timestamp: float = Field(default_factory=time.time)
    category: str                             # 'VOICE', 'NLU', 'ROUTING', 'EXECUTOR', 'VERIFICATION', 'SYSTEM'
    operation: str                            # e.g. 'PAUSE_VIDEO', 'SEEK_TIMESTAMP', 'OPEN_APP'
    stage: str                                # 'MIC', 'STT', 'NORMALIZATION', 'INTENT', 'EXECUTE', 'VERIFY'
    status: str                               # 'STARTED', 'SUCCESS', 'FAILED', 'SKIPPED', 'UNVERIFIED'
    durationMs: float = 0.0
    errorCode: Optional[ErrorCode] = None
    message: str = ""
    expected: Optional[str] = None
    actual: Optional[str] = None
    confidence: Optional[float] = None
    retryCount: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RootCauseAnalysis(BaseModel):
    """Detailed algorithmic root-cause determination based on trace evidence."""
    likelyCause: str
    failureCategory: FailureCategory
    confidence: float                         # 0.0 to 1.0 (e.g. 0.92 = 92%)
    evidence: List[str] = Field(default_factory=list)
    alternativeCauses: List[str] = Field(default_factory=list)
    fixability: FixabilityType
    suggestedFix: str
    filesAffected: List[str] = Field(default_factory=list)
    riskLevel: str = "LOW"                    # 'LOW', 'MEDIUM', 'HIGH'


class TransactionTrace(BaseModel):
    """Complete end-to-end transaction trace spanning all stages of a command turn."""
    correlationId: str
    userCommand: str
    startTime: float = Field(default_factory=time.time)
    endTime: Optional[float] = None
    totalDurationMs: float = 0.0
    stages: List[DiagnosticEvent] = Field(default_factory=list)
    finalStatus: str = "PENDING"              # 'SUCCESS', 'FAILED', 'DEGRADED', 'UNVERIFIED'
    targetSubsystem: Optional[str] = None
    rootCause: Optional[RootCauseAnalysis] = None
    finalResponse: Optional[str] = None


class FeatureHealth(BaseModel):
    """Live telemetry and health scorecard for a specific subsystem."""
    featureName: str
    healthStatus: HealthStatus
    totalAttempts: int = 0
    successCount: int = 0
    failureCount: int = 0
    unverifiedCount: int = 0
    successRatePercent: float = 100.0
    verificationFailureRatePercent: float = 0.0
    avgLatencyMs: float = 0.0
    lastFailureTimestamp: Optional[float] = None
    topErrorCode: Optional[str] = None
    lastVerifiedTimestamp: Optional[float] = None


class BugRecord(BaseModel):
    """Persistent record of an identified recurring or critical bug pattern."""
    bugId: str
    featureName: str
    firstDetected: float = Field(default_factory=time.time)
    lastDetected: float = Field(default_factory=time.time)
    occurrenceCount: int = 1
    failureStage: str
    likelyRootCause: str
    failureCategory: FailureCategory
    errorCode: ErrorCode
    status: str = "OPEN"                      # 'OPEN', 'RESOLVED', 'REGRESSION'
    isFixEffective: Optional[bool] = None
