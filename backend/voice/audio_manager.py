"""System sound and audio cue manager for JARVIS AI.

Plays non-blocking audio chimes for wake detection, tool completion,
and error alerts using Windows system audio services.
"""
import os
import threading
from typing import Optional

from backend.core.logger import get_logger

logger = get_logger("AudioManager")

# Check if winsound is available on Windows
try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False


class AudioManager:
    """Provides non-blocking audio feedback chimes."""

    def __init__(self, sound_enabled: bool = True):
        self.sound_enabled = sound_enabled

    def _play_async(self, func, *args):
        """Execute audio function in a daemon thread so it never blocks the main loop."""
        if not self.sound_enabled or not WINSOUND_AVAILABLE:
            return
        thread = threading.Thread(target=func, args=args, daemon=True)
        thread.start()

    def play_wake_chime(self) -> None:
        """Subtle dual-tone chime when wake word or voice listening starts."""
        def _chime():
            try:
                winsound.Beep(880, 80)   # A5
                winsound.Beep(1320, 120) # E6
            except Exception:
                pass
        self._play_async(_chime)

    def play_complete_chime(self) -> None:
        """Ascending chime on successful tool execution or response generation."""
        def _chime():
            try:
                winsound.Beep(1046, 70) # C6
                winsound.Beep(1318, 90) # E6
            except Exception:
                pass
        self._play_async(_chime)

    def play_error_chime(self) -> None:
        """Low double-beep on error or permission denial."""
        def _chime():
            try:
                winsound.Beep(440, 150) # A4
                winsound.Beep(330, 200) # E4
            except Exception:
                pass
        self._play_async(_chime)

    def play_beep(self, frequency: int = 1000, duration_ms: int = 100) -> None:
        """Play a custom frequency beep."""
        def _beep():
            try:
                winsound.Beep(frequency, duration_ms)
            except Exception:
                pass
        self._play_async(_beep)


# Global audio manager instance
audio_manager = AudioManager()
