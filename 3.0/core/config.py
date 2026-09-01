"""JARVIS 3.0 - Configuration Management.

Handles environment configuration, AI Studio API keys, system paths,
and safety settings without exposing secrets.
"""
from functools import lru_cache
import os
from pathlib import Path
from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class JarvisSettings(BaseSettings):
    """Central configuration class for JARVIS 3.0."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core Application Settings
    APP_NAME: str = "JARVIS"
    APP_VERSION: str = "3.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Assistant Identity
    WAKE_WORD: str = "Jarvis"
    USER_NAME: str = "Shivam"
    DEFAULT_LANGUAGE: str = "hinglish"  # hindi, english, hinglish

    # AI Brain Provider Settings
    AI_PROVIDER: str = "gemini"  # gemini, openrouter, mock
    AI_API_KEY: str = Field(default="", description="Google AI Studio Gemini API Key")
    AI_MODEL: str = "gemini-3.6-flash"  # standard fast reasoning model
    AI_TEMPERATURE: float = 0.2
    AI_TIMEOUT_SECONDS: float = 25.0
    AI_MAX_RETRIES: int = 3

    # Secondary / OpenRouter & NVIDIA Nemotron Debugger Settings
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "nvidia/nemotron-3.5-lightning:free"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    NEMOTRON_MODEL: str = "nvidia/nemotron-3.5-lightning:free"

    # Voice Settings
    VOICE_ENABLED: bool = True
    VOICE_STT_LANGUAGE: str = "en-IN"
    VOICE_STT_FALLBACK_LANGUAGE: str = "hi-IN"
    VOICE_ENERGY_THRESHOLD: int = 200
    VOICE_PAUSE_THRESHOLD: float = 0.55
    VOICE_RATE: int = 200
    VOICE_VOLUME: float = 1.0

    # Sandboxing & Security
    ALLOWED_DIRECTORIES: Union[List[str], str] = [
        str(Path.home()),
        str(Path.home() / "Downloads"),
        str(Path.home() / "Desktop"),
        str(Path.home() / "Documents"),
    ]

    # Database
    DATABASE_PATH: str = "jarvis_3.db"

    # Timeouts (in seconds)
    BROWSER_TIMEOUT: float = 15.0
    YOUTUBE_TIMEOUT: float = 15.0
    WHATSAPP_TIMEOUT: float = 20.0
    SYSTEM_COMMAND_TIMEOUT: float = 10.0

    @field_validator("ALLOWED_DIRECTORIES", mode="before")
    @classmethod
    def parse_allowed_directories(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            paths = [p.strip() for p in v.split(",") if p.strip()]
            return [str(Path(p).resolve()) for p in paths]
        if isinstance(v, list):
            return [str(Path(p).resolve()) for p in v]
        return []


@lru_cache()
def get_settings() -> JarvisSettings:
    """Return singleton cached configuration."""
    return JarvisSettings()
