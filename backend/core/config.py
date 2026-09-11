"""Configuration management for JARVIS AI using Pydantic Settings.

Reads configuration from environment variables and .env file with strict
type validation and default fallback values.
"""
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration class for JARVIS assistant."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application settings
    APP_NAME: str = "JARVIS"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Assistant Persona
    WAKE_WORD: str = "Jarvis"
    USER_NAME: str = "Shivam"

    # Production Application Allowlist (Single-App Focus)
    PRODUCTION_ENABLED_APPS: List[str] = ["youtube", "chrome", "google chrome", "edge", "browser"]

    # AI Brain Provider Configuration
    AI_PRIMARY_PROVIDER: str = "astra"
    AI_FALLBACK_PROVIDER: str = "gemini"
    AI_PROVIDER: str = "astra"  # backward compatibility alias

    # Astra (Experiential Labs / OpenAI Compatible) Configuration
    ASTRA_API_KEY: str = ""
    ASTRA_MODEL: str = "gpt-6-astra"
    ASTRA_BASE_URL: str = "https://api.experientiallabs.ai/v1"
    ASTRA_TIMEOUT_SECONDS: float = 15.0
    OPENAI_API_KEY: str = ""  # OpenAI standard alias
    OPENAI_BASE_URL: str = ""

    # Google Gemini Standby Fallback Configuration
    AI_API_KEY: str = ""
    AI_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_TIMEOUT_SECONDS: float = 15.0

    # Deprecated / Disabled OpenRouter & NVIDIA Nemotron
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "nvidia/nemotron-3.5-lightning:free"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MAX_TOKENS: int = 2048
    NEMOTRON_MODEL: str = "nvidia/nemotron-3.5-lightning:free"
    NEMOTRON_ENABLED: bool = False
    NEMOTRON_DEBUG_ONLY: bool = False
    NEMOTRON_MAX_FREE_REQUESTS_PER_DAY: int = 45
    NEMOTRON_WARNING_THRESHOLD: int = 40

    # Voice Subsystem Settings (TTS & STT)
    TTS_ENABLED: bool = True
    TTS_RATE: int = 205
    TTS_VOLUME: float = 1.0
    TTS_VOICE_ID: Optional[str] = None
    STT_ENABLED: bool = True
    STT_ENERGY_THRESHOLD: int = 300
    STT_TIMEOUT_SECONDS: int = 5

    # File System & Security Sandboxing
    ALLOWED_DIRECTORIES: Union[List[str], str] = [
        str(Path.home()),
        str(Path.home() / "Downloads"),
        str(Path.home() / "Desktop"),
    ]

    # Database
    DATABASE_URL: str = "sqlite:///./jarvis.db"

    # Permission auto-confirmation flags
    AUTO_CONFIRM_LEVEL_0: bool = True  # Safe (read-only)
    AUTO_CONFIRM_LEVEL_1: bool = True  # Normal computer tasks (open app, create folder)
    AUTO_CONFIRM_LEVEL_2: bool = True  # Communication (send WhatsApp message, voice call)
    AUTO_CONFIRM_LEVEL_3: bool = False  # Destructive (delete, modify system)

    @field_validator("ALLOWED_DIRECTORIES", mode="before")
    @classmethod
    def parse_allowed_directories(cls, v: Union[str, List[str]]) -> List[str]:
        """Normalize comma-separated directory strings into a clean list of normalized paths."""
        if isinstance(v, str):
            paths = [p.strip() for p in v.split(",") if p.strip()]
            return [str(Path(p).resolve()) for p in paths]
        if isinstance(v, list):
            return [str(Path(p).resolve()) for p in v]
        return []

    def is_production(self) -> bool:
        """Return True if running in production mode."""
        return self.APP_ENV.lower() == "production"


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton instance of Settings."""
    return Settings()
