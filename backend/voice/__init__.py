"""Voice subsystem package for JARVIS AI (TTS, STT, Audio Manager)."""
from backend.voice.audio_manager import AudioManager, audio_manager
from backend.voice.text_to_speech import TTSManager, tts_manager
from backend.voice.speech_to_text import STTManager, stt_manager

__all__ = [
    "AudioManager",
    "audio_manager",
    "TTSManager",
    "tts_manager",
    "STTManager",
    "stt_manager",
]
