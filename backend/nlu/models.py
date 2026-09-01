"""Data models for the Universal Human-Language Understanding Engine."""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class UniversalIntent(str, Enum):
    """Universal application-agnostic intent vocabulary."""
    # Application Lifecycle
    OPEN_APP = "OPEN_APP"
    CLOSE_APP = "CLOSE_APP"
    MINIMIZE = "MINIMIZE"
    MAXIMIZE = "MAXIMIZE"
    CLEAN_JUNK = "CLEAN_JUNK"

    # Communication & Messaging
    CALL_CONTACT = "CALL_CONTACT"
    VIDEO_CALL = "VIDEO_CALL"
    END_CALL = "END_CALL"
    MUTE_CALL = "MUTE_CALL"
    SEND_MESSAGE = "SEND_MESSAGE"
    DELETE_MESSAGE = "DELETE_MESSAGE"
    STATUS_VIEW = "STATUS_VIEW"
    STATUS_NEXT = "STATUS_NEXT"
    STATUS_PREV = "STATUS_PREV"
    STATUS_PAUSE = "STATUS_PAUSE"

    # Media & Playback Controls
    PLAY = "PLAY"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    STOP = "STOP"
    NEXT_MEDIA = "NEXT_MEDIA"
    PREVIOUS_MEDIA = "PREVIOUS_MEDIA"
    SEEK_FORWARD = "SEEK_FORWARD"
    SEEK_BACKWARD = "SEEK_BACKWARD"
    SEEK_TIMESTAMP = "SEEK_TIMESTAMP"
    VOLUME_UP = "VOLUME_UP"
    VOLUME_DOWN = "VOLUME_DOWN"
    MUTE_AUDIO = "MUTE_AUDIO"
    UNMUTE_AUDIO = "UNMUTE_AUDIO"
    FULLSCREEN = "FULLSCREEN"
    THEATER_MODE = "THEATER_MODE"
    MINIPLAYER = "MINIPLAYER"
    CAPTIONS = "CAPTIONS"
    SPEED_UP = "SPEED_UP"
    SPEED_DOWN = "SPEED_DOWN"
    REPLAY = "REPLAY"
    NEXT_SHORT = "NEXT_SHORT"
    PREV_SHORT = "PREV_SHORT"


    # Social & Interaction Actions
    LIKE = "LIKE"
    DISLIKE = "DISLIKE"
    SUBSCRIBE = "SUBSCRIBE"
    SHARE = "SHARE"
    COMMENTS_VIEW = "COMMENTS_VIEW"
    COMMENTS_HIDE = "COMMENTS_HIDE"

    # Navigation & Content Discovery
    SEARCH = "SEARCH"
    SELECT = "SELECT"
    CLICK = "CLICK"
    DOUBLE_CLICK = "DOUBLE_CLICK"
    SCROLL_DOWN = "SCROLL_DOWN"
    SCROLL_UP = "SCROLL_UP"
    GO_BACK = "GO_BACK"
    GO_FORWARD = "GO_FORWARD"
    REFRESH = "REFRESH"
    NEW_TAB = "NEW_TAB"
    CLOSE_TAB = "CLOSE_TAB"
    NEXT_TAB = "NEXT_TAB"
    PREV_TAB = "PREV_TAB"

    # File & Directory Operations
    OPEN_FILE = "OPEN_FILE"
    FIND_FILE = "FIND_FILE"
    SEND_FILE = "SEND_FILE"
    SAVE_FILE = "SAVE_FILE"
    DELETE_FILE = "DELETE_FILE"
    RENAME_FILE = "RENAME_FILE"

    # System & Settings
    SYSTEM_STATUS = "SYSTEM_STATUS"
    OPEN_SETTINGS = "OPEN_SETTINGS"
    LOCK_SCREEN = "LOCK_SCREEN"
    SCREENSHOT = "SCREENSHOT"
    BATTERY_STATUS = "BATTERY_STATUS"
    ANALYZE_APP = "ANALYZE_APP"
    TEST_APP_HEALTH = "TEST_APP_HEALTH"

    # Conversational & Companion Dialogue
    GREETING = "GREETING"
    IDENTITY = "IDENTITY"
    THANK_YOU = "THANK_YOU"
    CONVERSATIONAL_CHAT = "CONVERSATIONAL_CHAT"
    CLARIFICATION_NEEDED = "CLARIFICATION_NEEDED"
    UNKNOWN = "UNKNOWN"


class ExtractedEntities(BaseModel):
    """Structured entities extracted from natural user commands."""
    contact: Optional[str] = None
    phone_number: Optional[str] = None
    application: Optional[str] = None
    query: Optional[str] = None
    message_body: Optional[str] = None
    ordinal_index: Optional[int] = None
    direction: Optional[str] = None           # 'up', 'down', 'left', 'right', 'next', 'previous'
    time_duration_sec: Optional[int] = None   # e.g. 10, 30, 60
    time_str: Optional[str] = None            # e.g. '5m30s', '12m', '45s'
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    pronoun_reference: Optional[str] = None   # 'it', 'this', 'that', 'isko', 'usko', 'ye', 'woh'
    position_relative: Optional[str] = None   # 'first', 'second', 'right side', 'sidebar'
    raw_parameters: Dict[str, Any] = Field(default_factory=dict)


class CandidateInterpretation(BaseModel):
    """A scored candidate interpretation of the user's intent."""
    intent: UniversalIntent
    confidence: float = 0.0
    application: Optional[str] = None
    rationale: str = ""


class SemanticParseResult(BaseModel):
    """Final output of the Semantic Intent Engine."""
    raw_transcript: str
    normalized_transcript: str
    detected_language: str = "hinglish"        # 'hindi', 'english', 'hinglish'
    primary_intent: UniversalIntent
    confidence: float = 0.0
    entities: ExtractedEntities = Field(default_factory=ExtractedEntities)
    target_application: Optional[str] = None
    candidate_interpretations: List[CandidateInterpretation] = Field(default_factory=list)
    requires_clarification: bool = False
    clarification_prompt: Optional[str] = None
    sub_intents: List["SemanticParseResult"] = Field(default_factory=list)


class NluDebugTrace(BaseModel):
    """Developer observability trace payload."""
    raw_transcript: str
    normalized_transcript: str
    detected_language: str
    intent: str
    confidence: float
    entities: Dict[str, Any]
    target_application: Optional[str]
    selected_tool: Optional[str]
    tool_arguments: Dict[str, Any]
    execution_result: Optional[str] = None
    verification_status: Optional[str] = None
    error_or_clarification: Optional[str] = None
