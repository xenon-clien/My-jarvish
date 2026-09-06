"""High-Quality Natural Hindi Text-to-Speech (TTS) Manager for JARVIS AI.

Architecture:
- Modular TTSProvider interface (Microsoft Edge Neural Swara, Google TTS, ElevenLabs, Offline SAPI5).
- Automatic failsafe fallback chain (Edge -> Google -> Offline).
- Hardware-accelerated native Windows playback (winmm MCI).
- Asynchronous worker queue for smooth, non-blocking UI and voice flow.
"""
import ctypes
import os
import queue
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional

from backend.core.config import Settings, get_settings
from backend.core.logger import get_logger
from backend.voice.tts_providers import (
    EdgeTTSProvider,
    GoogleTTSProvider,
    ElevenLabsProvider,
    OfflineTTSProvider,
    TTSProvider,
    normalize_hindi_tts_text,
)

logger = get_logger("TTSManager")


class TTSManager:
    """Central Text-to-Speech manager orchestrating pluggable voice providers with automatic failsafe."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.enabled = self.settings.TTS_ENABLED
        self.rate = self.settings.TTS_RATE
        self.volume = self.settings.TTS_VOLUME

        # Instantiate providers with Captain America (Madhur Baritone -22Hz) as PRIMARY heavy voice
        self.edge_provider: TTSProvider = EdgeTTSProvider(voice_id="hi-IN-MadhurNeural", speed_rate="-4%", pitch="-22Hz")
        self.edge_madhur_safe: TTSProvider = EdgeTTSProvider(voice_id="hi-IN-MadhurNeural", speed_rate="-4%", pitch="+0Hz")
        self.edge_prabhat_provider: TTSProvider = EdgeTTSProvider(voice_id="en-IN-PrabhatNeural", speed_rate="-2%", pitch="-15Hz")
        self.edge_madhur_provider: TTSProvider = self.edge_provider
        self.edge_swara_provider: TTSProvider = EdgeTTSProvider(voice_id="hi-IN-SwaraNeural")
        self.offline_male_provider: TTSProvider = OfflineTTSProvider(rate=self.rate, volume=self.volume, gender="male")
        self.offline_provider: TTSProvider = self.offline_male_provider
        self.secondary_provider: TTSProvider = GoogleTTSProvider(lang="hi", tld="co.in")
        self.elevenlabs_provider: TTSProvider = ElevenLabsProvider()

        # Primary voice is Captain America (Deep Heavy Baritone Hindi Voice)
        self.primary_provider: TTSProvider = self.edge_provider if self.edge_provider.is_available() else self.offline_male_provider
        self._active_provider_name = "captain_america" if self.edge_provider.is_available() else "offline_sapi5"
        self._speech_queue: queue.Queue = queue.Queue()
        self._is_speaking = False
        self._playback_lock = threading.Lock()

        # Start background TTS synthesis worker thread
        self._worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self._worker_thread.start()

    def _play_audio_native(self, audio_path: str) -> bool:
        """Play generated MP3/WAV speech file using native Windows Multimedia API (winmm.dll) or winsound."""
        with self._playback_lock:
            try:
                with open(audio_path, "rb") as af:
                    header = af.read(4)
                if header == b"RIFF":
                    import winsound
                    winsound.PlaySound(audio_path, winsound.SND_FILENAME)
                    return True
            except Exception as e:
                logger.debug(f"WAV winsound check error: {e}")

            alias = f"jarvis_tts_{int(time.time() * 1000) % 100000}"
            mci = ctypes.windll.winmm.mciSendStringW
            try:
                mci("close all", None, 0, None)
                res = mci(f'open "{audio_path}" type mpegvideo alias {alias}', None, 0, None)
                if res != 0:
                    # Fallback type for wav/unknown
                    res = mci(f'open "{audio_path}" alias {alias}', None, 0, None)
                if res != 0:
                    logger.warning(f"MCI audio open returned code {res}")
                    return False

                mci(f"play {alias} wait", None, 0, None)
                mci(f"close {alias}", None, 0, None)
                return True
            except Exception as exc:
                logger.error(f"Native MCI playback error: {exc}")
                try:
                    mci(f"close {alias}", None, 0, None)
                except Exception:
                    pass
                return False

    def _synthesize_and_play(self, text: str) -> bool:
        """Synthesize text via the fallback provider chain and play it aloud."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            temp_path = f.name

        try:
            played = False

            # Provider priority list based on user selection and availability
            candidate_providers: List[TTSProvider] = []

            # 1. Add requested active provider first
            if self._active_provider_name in ("captain_america", "edge_madhur"):
                # STRICTLY MALE FALLBACK CHAIN - NEVER EVER FALL BACK TO FEMALE
                candidate_providers = [
                    self.edge_provider,          # 1. Captain America Deep Heavy Baritone (-22Hz)
                    self.edge_madhur_safe,      # 2. Hindi Male Madhur (Standard Pitch)
                    self.edge_prabhat_provider, # 3. Indian Male Prabhat
                    self.offline_male_provider,  # 4. Windows SAPI5 Male Baritone (David)
                ]
            elif self._active_provider_name == "edge_swara":
                candidate_providers = [self.edge_swara_provider, self.secondary_provider, self.offline_provider]
            elif self._active_provider_name == "google_hindi":
                candidate_providers = [self.secondary_provider, self.edge_provider, self.offline_provider]
            elif self._active_provider_name == "elevenlabs" and self.elevenlabs_provider.is_available():
                candidate_providers = [self.elevenlabs_provider, self.edge_provider, self.secondary_provider, self.offline_provider]
            elif self._active_provider_name == "neerja":
                neerja = EdgeTTSProvider(voice_id="en-IN-NeerjaNeural")
                candidate_providers = [neerja, self.edge_provider, self.secondary_provider, self.offline_provider]
            else:
                # Default: Captain America Baritone -> Hindi Male -> Offline Male
                candidate_providers = [
                    self.edge_provider,
                    self.edge_madhur_safe,
                    self.edge_prabhat_provider,
                    self.offline_male_provider,
                ]

            # Try candidate providers in order
            for provider in candidate_providers:
                if not provider.is_available():
                    continue

                try:
                    success = provider.synthesize(text, temp_path)
                    if success and os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                        played = self._play_audio_native(temp_path)
                        if played:
                            break
                except Exception as exc:
                    logger.warning(f"Provider {provider.get_metadata().provider_name} failed: {exc}")

            return played
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def _speech_worker(self) -> None:
        """Background daemon processing speech items from the queue with single-voice guarantee."""
        while True:
            try:
                item = self._speech_queue.get()
                if item is None:
                    break

                text, done_event = item
                if self.enabled and text.strip():
                    self._is_speaking = True
                    try:
                        self._synthesize_and_play(text)
                    except Exception as exc:
                        logger.error(f"TTS Worker execution error: {exc}")
                    finally:
                        self._is_speaking = False
                        self._last_spoken_time = time.time()

                if done_event:
                    done_event.set()
                self._speech_queue.task_done()
            except Exception as e:
                logger.error(f"TTS Worker fatal exception: {e}")

    def is_speaking(self) -> bool:
        """Return whether TTS audio is currently actively playing through speakers."""
        return bool(getattr(self, "_is_speaking", False))

    @property
    def last_spoken_time(self) -> float:
        """Return epoch timestamp of last speech finish."""
        return getattr(self, "_last_spoken_time", 0.0)

    def speak(self, text: str, block: bool = False) -> None:
        """Queue text to be spoken aloud by JARVIS in natural Hindi voice."""
        if not self.enabled or not text:
            return

        logger.info(f"Speaking (Hindi AI Voice): '{text[:60]}...'")
        done_event = threading.Event() if block else None
        self._speech_queue.put((text, done_event))

        if block and done_event:
            done_event.wait()

    def stop(self) -> None:
        """Instantly interrupt and stop any ongoing speech playback and clear pending queue."""
        # 1. Clear speech queue
        while not self._speech_queue.empty():
            try:
                item = self._speech_queue.get_nowait()
                if item and item[1]:
                    item[1].set()
                self._speech_queue.task_done()
            except Exception:
                break

        # 2. Stop native audio playback immediately
        try:
            mci = ctypes.windll.winmm.mciSendStringW
            mci("stop all", None, 0, None)
            mci("close all", None, 0, None)
        except Exception:
            pass
        self._is_speaking = False
        self._last_spoken_time = time.time()
        logger.info("Speech playback stopped immediately by user command.")

    def is_speaking(self) -> bool:
        """Return True if TTS engine is currently speaking."""
        return self._is_speaking

    def list_available_voices(self) -> List[Dict[str, Any]]:
        """List available Hindi natural voices and their metadata."""
        return [
            {
                "id": "captain_america",
                "name": "Captain America (Deep Heavy Baritone Hindi Voice)",
                "language": "hi-IN",
                "is_free": True,
                "recommended": True,
            },
            {
                "id": "edge_swara",
                "name": "Microsoft Swara (Natural Sweet Hindi Female)",
                "language": "hi-IN",
                "is_free": True,
                "recommended": False,
            },
            {
                "id": "google_hindi",
                "name": "Google Hindi AI Voice (Natural Assistant Female)",
                "language": "hi-IN",
                "is_free": True,
                "recommended": False,
            },
            {
                "id": "neerja",
                "name": "Microsoft Neerja (Expressive Indian English/Hinglish Female)",
                "language": "en-IN",
                "is_free": True,
                "recommended": False,
            },
            {
                "id": "offline_sapi5",
                "name": "Windows Offline SAPI5 (Zero Internet Fallback)",
                "language": "en-US",
                "is_free": True,
                "recommended": False,
            },
        ]

    def set_voice(self, voice_id: str) -> None:
        """Update the active voice provider ('edge_swara', 'google_hindi', 'neerja', 'offline_sapi5')."""
        self._active_provider_name = voice_id.lower().strip()
        logger.info(f"Active TTS voice set to: {self._active_provider_name}")

    def set_rate(self, rate: int) -> None:
        """Update speech rate in words per minute."""
        self.rate = rate

    def set_volume(self, volume: float) -> None:
        """Update volume level (0.0 to 1.0)."""
        self.volume = max(0.0, min(1.0, volume))


# Global TTS instance
tts_manager = TTSManager()
