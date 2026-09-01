"""Pluggable TTS Providers package for JARVIS AI."""
from backend.voice.tts_providers.base import TTSProvider, VoiceMetadata
from backend.voice.tts_providers.edge_provider import EdgeTTSProvider
from backend.voice.tts_providers.gtts_provider import GoogleTTSProvider
from backend.voice.tts_providers.elevenlabs_provider import ElevenLabsProvider
from backend.voice.tts_providers.offline_provider import OfflineTTSProvider
from backend.voice.tts_providers.normalizer import normalize_hindi_tts_text

__all__ = [
    "TTSProvider",
    "VoiceMetadata",
    "EdgeTTSProvider",
    "GoogleTTSProvider",
    "ElevenLabsProvider",
    "OfflineTTSProvider",
    "normalize_hindi_tts_text",
]
