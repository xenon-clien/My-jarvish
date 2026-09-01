"""Abstract Base Class and data models for modular Text-to-Speech (TTS) providers."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class VoiceMetadata(BaseModel):
    """Metadata describing a specific TTS voice."""
    provider_name: str
    voice_id: str
    display_name: str
    language: str
    gender: str = "female"
    style: str = "natural"
    is_free: bool = True
    is_offline: bool = False
    description: str = ""


class TTSProvider(ABC):
    """Abstract interface for all pluggable TTS engines."""

    @abstractmethod
    def synthesize(self, text: str, output_path: str, speed_multiplier: float = 1.0) -> bool:
        """Synthesize text to an audio file (e.g. MP3/WAV).
        
        Args:
            text: The text string to speak.
            output_path: Target absolute path to save the generated audio.
            speed_multiplier: Speech rate multiplier (1.0 = normal).
            
        Returns:
            True if synthesis succeeded and output file exists, False otherwise.
        """
        pass

    @abstractmethod
    def get_metadata(self) -> VoiceMetadata:
        """Return structured metadata about this voice provider."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if required libraries and connectivity are available."""
        pass
