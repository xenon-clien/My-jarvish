"""Acoustic Double-Clap Detection Engine for JARVIS AI.

Detects sharp impulsive acoustic transients (claps) and pattern-matches
double-clap sequences (2 claps within 0.12s - 0.85s window) to wake or start JARVIS.
"""
import os
import sys
import threading
import time
from typing import Callable, Optional
import numpy as np

try:
    import sounddevice as sd
    SD_AVAILABLE = True
except ImportError:
    SD_AVAILABLE = False

try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False

from backend.core.logger import get_logger

logger = get_logger("ClapDetector")


class ClapDetector:
    """Real-time, low-CPU double-clap detection engine."""

    def __init__(
        self,
        on_double_clap: Optional[Callable[[], None]] = None,
        energy_threshold: float = 0.14,
        min_clap_interval: float = 0.12,
        max_clap_interval: float = 0.85,
        sample_rate: int = 22050,
        chunk_size: int = 1024,
    ):
        self.on_double_clap = on_double_clap
        self.energy_threshold = energy_threshold  # Fallback minimum
        self.min_clap_interval = min_clap_interval
        self.max_clap_interval = max_clap_interval
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.digital_gain = 3.5  # Software AGC boost for laptop microphones

        self._running = False
        self._last_clap_time = 0.0
        self._clap_count = 0
        self._ambient_rms = 0.005
        self._lock = threading.Lock()
        self._stream = None

    def is_clap(self, audio_chunk: np.ndarray) -> bool:
        """Analyze an audio frame with software AGC & adaptive crest factor."""
        if audio_chunk is None or len(audio_chunk) == 0:
            return False

        # Apply digital gain boost
        boosted = np.clip(audio_chunk * self.digital_gain, -1.0, 1.0)

        # Compute peak amplitude and RMS energy
        peak = float(np.max(np.abs(boosted)))
        rms = float(np.sqrt(np.mean(boosted**2)))

        # Slowly update background ambient RMS tracker
        self._ambient_rms = 0.95 * self._ambient_rms + 0.05 * rms

        # Adaptive threshold: Trigger if peak exceeds dynamic ambient multiplier or base sensitivity
        adaptive_thresh = max(0.055, self._ambient_rms * 3.5)
        if peak < adaptive_thresh:
            return False

        # Hand claps have a sharp impulsive crest factor
        crest_factor = peak / (rms + 1e-6)
        return crest_factor >= 2.2

    def process_audio_frame(self, audio_data: np.ndarray) -> bool:
        """Process incoming audio block and check for double-clap pattern.
        
        Returns True if a double clap was just detected.
        """
        now = time.time()
        detected = False

        if self.is_clap(audio_data):
            with self._lock:
                time_since_last = now - self._last_clap_time

                if time_since_last < self.min_clap_interval:
                    # Ignore reverberation/echo of the first clap
                    pass
                elif self.min_clap_interval <= time_since_last <= self.max_clap_interval:
                    # Double clap detected!
                    logger.info(f"[DOUBLE CLAP DETECTED] Interval: {round(time_since_last, 2)}s")
                    detected = True
                    self._last_clap_time = 0.0  # Reset
                    self._play_wake_chime()
                    if self.on_double_clap:
                        try:
                            self.on_double_clap()
                        except Exception as e:
                            logger.error(f"Error in on_double_clap callback: {e}")
                else:
                    # First clap in a potential sequence
                    self._last_clap_time = now
                    logger.debug("[Single Clap Detected] Waiting for second clap...")

        # Reset if window expired
        with self._lock:
            if self._last_clap_time > 0 and (now - self._last_clap_time > self.max_clap_interval):
                self._last_clap_time = 0.0

        return detected

    def _play_wake_chime(self) -> None:
        """Play distinct double-beep confirmation chime."""
        if WINSOUND_AVAILABLE:
            def _beep():
                try:
                    winsound.Beep(988, 70)   # B5
                    winsound.Beep(1318, 120) # E6
                except Exception:
                    pass
            threading.Thread(target=_beep, daemon=True).start()

    def _audio_callback(self, indata, frames, time_info, status):
        """Streaming callback from sounddevice."""
        if status:
            logger.debug(f"Audio status: {status}")
        audio = indata[:, 0] if indata.ndim > 1 else indata
        self.process_audio_frame(audio)

    def start_listening(self) -> None:
        """Start non-blocking background microphone monitoring."""
        if not SD_AVAILABLE:
            logger.error("sounddevice is not available. Clap detection disabled.")
            return

        if self._running:
            return

        self._running = True
        logger.info("[Clap Listener] Background microphone monitoring started.")
        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                channels=1,
                dtype="float32",
                callback=self._audio_callback,
            )
            self._stream.start()
        except Exception as e:
            logger.error(f"Failed to open sounddevice input stream: {e}")
            self._running = False

    def stop_listening(self) -> None:
        """Stop background microphone monitoring."""
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        logger.info("Double-Clap Listener stopped.")


# Global default detector instance
clap_detector = ClapDetector()
