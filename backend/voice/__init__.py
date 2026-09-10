"""Voice subsystem package for JARVIS AI (TTS, STT, Audio Manager)."""
def __getattr__(name: str):
    if name in ("AudioManager", "audio_manager"):
        from backend.voice.audio_manager import AudioManager, audio_manager
        return AudioManager if name == "AudioManager" else audio_manager
    if name in ("TTSManager", "tts_manager"):
        from backend.voice.text_to_speech import TTSManager, tts_manager
        return TTSManager if name == "TTSManager" else tts_manager
    if name in ("STTManager", "stt_manager"):
        from backend.voice.speech_to_text import STTManager, stt_manager
        return STTManager if name == "STTManager" else stt_manager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "AudioManager",
    "audio_manager",
    "TTSManager",
    "tts_manager",
    "STTManager",
    "stt_manager",
]
