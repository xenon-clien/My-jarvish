"""JARVIS 3.0 - Dedicated Voice Adapter (STT & TTS).

Handles microphone audio streaming, Software AGC amplification,
dual-language speech recognition (en-IN + hi-IN), and natural Hindi/English TTS speech.
"""
import concurrent.futures
import queue
import re
import threading
import time
from typing import Any, Callable, Dict, Optional
import numpy as np
import pyttsx3
import speech_recognition as sr

from adapters.base_adapter import BaseAdapter
from core.config import get_settings
from core.events import EventType, JarvisEvent, event_bus
from core.logger import get_logger
from core.models import PermissionLevel, PermissionType, ToolCategory, ToolExecutionResult
from core.tool_contract import FunctionalTool
from core.tool_registry import ToolRegistry, default_registry
from nlu.language_normalizer import LanguageNormalizer

logger = get_logger("VoiceAdapter")

try:
    import sounddevice as sd
    SD_AVAILABLE = True
except ImportError:
    SD_AVAILABLE = False


class VoiceAdapter(BaseAdapter):
    """Encapsulates speech-to-text recording and text-to-speech feedback."""

    def __init__(self):
        super().__init__(name="voice", category=ToolCategory.VOICE)
        self.settings = get_settings()
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = self.settings.VOICE_ENERGY_THRESHOLD
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = self.settings.VOICE_PAUSE_THRESHOLD

        self._tts_engine = None
        self._tts_lock = threading.Lock()
        self._is_speaking = False
        self._init_tts()

    def _init_tts(self) -> None:
        try:
            self._tts_engine = pyttsx3.init()
            self._tts_engine.setProperty("rate", self.settings.VOICE_RATE)
            self._tts_engine.setProperty("volume", self.settings.VOICE_VOLUME)
        except Exception as e:
            logger.warning(f"Failed to initialize pyttsx3 TTS engine: {e}")

    def register_tools(self, registry: Optional[ToolRegistry] = None) -> None:
        reg = registry or default_registry

        # 1. voice.speak
        reg.register(FunctionalTool(
            name="voice.speak",
            description="Speak a message aloud to the user using text-to-speech.",
            category=ToolCategory.VOICE,
            func=self.speak,
            permission_level=PermissionLevel.LEVEL_0_SAFE,
        ))

        # 2. voice.stop_speaking
        reg.register(FunctionalTool(
            name="voice.stop_speaking",
            description="Stop any ongoing speech audio playback immediately.",
            category=ToolCategory.VOICE,
            func=self.stop_speaking,
            permission_level=PermissionLevel.LEVEL_0_SAFE,
        ))

        self.is_initialized = True
        logger.info("Registered VoiceAdapter tools: voice.speak, voice.stop_speaking")

    def get_application_state(self) -> Dict[str, Any]:
        return {
            "mic_available": self.is_microphone_available(),
            "is_speaking": self._is_speaking,
        }

    def is_microphone_available(self) -> bool:
        if not SD_AVAILABLE:
            return False
        try:
            devices = sd.query_devices()
            return any(d.get("max_input_channels", 0) > 0 for d in devices)
        except Exception:
            return False

    def is_speaking(self) -> bool:
        return self._is_speaking

    def speak(self, text: str, block: bool = False) -> ToolExecutionResult:
        """Speak message aloud asynchronously or blocking."""
        if not text or not text.strip() or not self._tts_engine:
            return ToolExecutionResult(success=True, message="Nothing to speak.")

        def _worker():
            with self._tts_lock:
                self._is_speaking = True
                event_bus.publish(JarvisEvent(
                    event_type=EventType.TTS_SPEAK_STARTED,
                    data={"text": text},
                ))
                try:
                    self._tts_engine.say(text)
                    self._tts_engine.runAndWait()
                except Exception as exc:
                    logger.debug(f"TTS error: {exc}")
                finally:
                    self._is_speaking = False
                    event_bus.publish(JarvisEvent(
                        event_type=EventType.TTS_SPEAK_COMPLETED,
                        data={"text": text},
                    ))

        if block:
            _worker()
        else:
            threading.Thread(target=_worker, daemon=True).start()

        return ToolExecutionResult(success=True, message=f"Speaking: '{text[:40]}...'")

    def stop_speaking(self) -> ToolExecutionResult:
        """Interrupt active TTS speech."""
        if self._tts_engine:
            try:
                self._tts_engine.stop()
                self._is_speaking = False
            except Exception:
                pass
        return ToolExecutionResult(success=True, message="Stopped speech.")

    def listen_phrase(self, timeout: float = 3.5, phrase_time_limit: float = 8.0) -> Optional[str]:
        """Capture microphone phrase with AGC and dual-language Google STT."""
        if not SD_AVAILABLE or not self.is_microphone_available():
            return None

        sample_rate = 44100
        channels = 2
        try:
            dev = sd.query_devices(kind="input")
            sample_rate = int(dev.get("default_samplerate", 44100))
            channels = int(dev.get("max_input_channels", 2))
        except Exception:
            pass

        q = queue.Queue()
        def _cb(indata, frames, time_info, status):
            q.put(indata.copy())

        chunk_samples = 2048
        recorded_chunks = []
        speech_started = False
        silence_start = None
        start_t = time.time()

        try:
            with sd.InputStream(samplerate=sample_rate, blocksize=chunk_samples, dtype="int16", channels=channels, callback=_cb):
                while True:
                    try:
                        chunk = q.get(timeout=0.2)
                    except queue.Empty:
                        if time.time() - start_t > timeout:
                            break
                        continue

                    raw_mono = np.mean(chunk, axis=1).astype(np.float64) if chunk.ndim > 1 else chunk.flatten().astype(np.float64)
                    rms = float(np.sqrt(np.mean(raw_mono ** 2)))
                    elapsed = time.time() - start_t

                    if not speech_started:
                        if elapsed > timeout:
                            return None
                        if rms > 220.0:
                            speech_started = True
                            recorded_chunks.append(raw_mono)
                    else:
                        recorded_chunks.append(raw_mono)
                        if elapsed > phrase_time_limit:
                            break
                        if rms < 150.0:
                            if silence_start is None:
                                silence_start = time.time()
                            elif time.time() - silence_start >= 0.9:
                                break
                        else:
                            silence_start = None

            if not recorded_chunks or len(recorded_chunks) < 3:
                return None

            full_audio_mono = np.concatenate(recorded_chunks)

            # Resample to 16000Hz standard for Google STT
            if sample_rate != 16000:
                dur = len(full_audio_mono) / sample_rate
                target_samples = int(dur * 16000)
                orig_t = np.linspace(0, dur, len(full_audio_mono), endpoint=False)
                tgt_t = np.linspace(0, dur, target_samples, endpoint=False)
                resampled = np.interp(tgt_t, orig_t, full_audio_mono).astype(np.float64)
            else:
                resampled = full_audio_mono

            # Peak AGC Amplification
            peak = np.max(np.abs(resampled)) if len(resampled) > 0 else 0
            if peak > 40:
                gain = min(12.0, 26000.0 / peak)
                resampled = np.clip(resampled * gain, -32768, 32767).astype(np.int16)
            else:
                resampled = resampled.astype(np.int16)

            audio_data = sr.AudioData(resampled.tobytes(), 16000, 2)

            # Parallel recognition for en-IN and hi-IN
            def _recog(lang: str) -> Optional[str]:
                try:
                    res = self.recognizer.recognize_google(audio_data, language=lang)
                    return LanguageNormalizer.normalize_text(res) if res else None
                except Exception:
                    return None

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
                f_en = ex.submit(_recog, "en-IN")
                f_hi = ex.submit(_recog, "hi-IN")
                cand_en = f_en.result(timeout=4.0)
                cand_hi = f_hi.result(timeout=4.0)

            cands = [c for c in [cand_en, cand_hi] if c]
            if not cands:
                return None

            # Pick best candidate based on length / action keyword presence
            best = max(cands, key=len).strip()
            logger.info(f"STT Recognized: '{best}'")
            return best

        except Exception as exc:
            logger.debug(f"Voice recording error: {exc}")
            return None


voice_adapter = VoiceAdapter()
