"""Unit tests for the Voice subsystem (TTS, STT, and AudioManager)."""
import pytest
from backend.core.config import Settings
from backend.voice.audio_manager import AudioManager
from backend.voice.speech_to_text import STTManager
from backend.voice.text_to_speech import TTSManager


def test_audio_manager_chimes():
    """Test audio cue player methods without crashing."""
    mgr = AudioManager(sound_enabled=True)
    mgr.play_wake_chime()
    mgr.play_complete_chime()
    mgr.play_error_chime()
    mgr.play_beep(800, 50)


def test_tts_manager_properties():
    """Test setting voice rate, volume, and listing available system voices."""
    settings = Settings(TTS_ENABLED=False)  # Disable audio hardware playback during unit test
    tts = TTSManager(settings=settings)

    tts.set_rate(190)
    assert tts.rate == 190

    tts.set_volume(0.8)
    assert tts.volume == 0.8

    # Ensure volume is clamped between 0.0 and 1.0
    tts.set_volume(1.5)
    assert tts.volume == 1.0

    voices = tts.list_available_voices()
    assert isinstance(voices, list)


def test_stt_manager_initialization():
    """Test Speech-to-Text manager initialization and safe mic checks."""
    stt = STTManager(settings=Settings(STT_ENABLED=True))
    assert stt.recognizer is not None
    # Checking mic availability should return boolean without throwing unhandled exceptions
    is_available = stt.is_microphone_available()
    assert isinstance(is_available, bool)
