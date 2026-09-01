"""Database data transfer objects and entity models for JARVIS AI."""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class TaskHistoryRecord(BaseModel):
    """Represents a recorded user command and tool execution."""
    id: Optional[int] = None
    timestamp: Optional[str] = None
    command: str
    action: Optional[str] = None
    status: str  # SUCCESS, FAILED, AWAITING_CONFIRMATION, CANCELLED
    result: Optional[str] = None
    execution_time_ms: float = 0.0


class MemoryRecord(BaseModel):
    """Represents a long-term memory key-value pair."""
    id: Optional[int] = None
    category: str  # USER_PREFERENCE, CONTACT_ALIAS, APPLICATION_PREFERENCE, ASSISTANT_SETTING
    key: str
    value: str
    updated_at: Optional[str] = None


class ContactRecord(BaseModel):
    """Represents a user contact in the address book."""
    id: Optional[int] = None
    name: str
    phone: str
    email: Optional[str] = None
    relationship: Optional[str] = None
    created_at: Optional[str] = None
