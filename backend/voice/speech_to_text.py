"""High-sensitivity Speech-to-Text Manager with Software AGC, Diagnostic Instrumentation & Dual-Language Scoring."""
import concurrent.futures
import queue
import re
import time
from typing import List, Optional
import numpy as np
import speech_recognition as sr

try:
    import sounddevice as sd
    SD_AVAILABLE = True
except ImportError:
    SD_AVAILABLE = False

from backend.core.config import Settings, get_settings
from backend.core.logger import get_logger
from backend.diagnostics.engine import diagnostic_engine
from backend.diagnostics.models import DiagnosticEvent, ErrorCode

logger = get_logger("SpeechToText")

# Devanagari to Romanized Hinglish keyword transliterator
HINDI_PHONETIC_MAP = {
    "हर्ष": "harsh",
    "शिवम": "shivam",
    "मैसेज": "message",
    "कॉल": "call",
    "फोन": "phone",
    "लगाओ": "lagao",
    "करो": "karo",
    "खोलो": "kholo",
    "चलाओ": "chalao",
    "यूट्यूब": "youtube",
    "क्रोम": "chrome",
    "व्हाट्सएप": "whatsapp",
    "गाना": "gaana",
    "वीडियो": "video",
    "शॉर्ट": "short",
    "शॉर्ट्स": "shorts",
    "शॉट": "short",
    "शॉट्स": "shorts",
    "पहला": "first",
    "पहली": "first",
    "दूसरा": "second",
    "दूसरी": "second",
    "तीसरा": "third",
    "तीसरी": "third",
    "सर्च": "search",
    "रोको": "pause",
    "पॉज": "pause",
    "रिज्यूम": "resume",
    "चालू": "resume",
    "बंद": "close",
    "आवाज": "aawaz",
    "बढ़ाओ": "badhao",
    "कम": "kam",
    "अगला": "next",
    "पिछला": "prev",
    "लाइक": "like",
    "सब्सक्राइब": "subscribe",
    "शेयर": "share",
    "कमेंट्स": "comments",
}


def _clean_phonetic_variations(text: str) -> str:
    """Normalize common phonetic speech-to-text slips."""
    res = text
    for dev, rom in HINDI_PHONETIC_MAP.items():
        res = res.replace(dev, rom)

    slips = {
        r"\b(?:pouse|pows|pos|pass|paws|boss|post)\s+(?:karo|kar|do|video)\b": "pause video",
        r"\b(?:rijum|rijume|rigum|resum|resumed)\b": "resume",
        r"\b(?:fulskrin|fulscrin|full\s+skrin)\b": "fullscreen",
        r"\b(?:sabscraib|sabscribe|subscrive)\b": "subscribe",
        r"\b(?:kament|kaments|coment)\b": "comments",
        r"\b(?:shot|shots|shirt|shirts|shart|sort|sorts|chot|chote)\b": "short",
    }
    for pat, rep in slips.items():
        res = re.sub(pat, rep, res, flags=re.IGNORECASE)
    return res


class SpeechToTextManager:
    """Queue-buffered microphone recording engine with digital AGC and diagnostic instrumentation."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.enabled = getattr(settings, "STT_ENABLED", True)
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 100
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = 0.55

        # Native 16000Hz Mono capture per NVIDIA Nemotron recommendation
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_size = 1024
        self.gain_factor = 4.0
        self._last_transcript = None

    def is_microphone_available(self) -> bool:
        """Check if an active recording microphone device is accessible."""
        if not self.enabled or not SD_AVAILABLE:
            return False
        try:
            devices = sd.query_devices()
            inputs = [d for d in devices if d.get("max_input_channels", 0) > 0]
            return len(inputs) > 0
        except Exception:
            return False

    def listen_once(
        self,
        timeout: float = 6.0,
        phrase_time_limit: float = 12.0,
        silence_limit: float = 1.0,
        correlation_id: Optional[str] = None,
    ) -> Optional[str]:
        """Capture microphone speech natively in 16kHz Mono with real-time AGC and emit diagnostic events."""
        cid = correlation_id or "VOICE-LISTEN"
        # 1. Prevent audio feedback loop (gentle 0.10s cooldown so user speech is NEVER blocked)
        try:
            from backend.voice.text_to_speech import tts_manager
            if tts_manager.is_speaking() or (time.time() - tts_manager.last_spoken_time < 0.10):
                time.sleep(0.04)
                return None
        except Exception:
            pass

        if not self.enabled or not SD_AVAILABLE:
            diagnostic_engine.record_event(DiagnosticEvent(
                eventId="EVT-MIC-UNAVAIL",
                correlationId=cid,
                category="VOICE",
                operation="LISTEN_ONCE",
                stage="MIC",
                status="FAILED",
                errorCode=ErrorCode.VOICE_MIC_UNAVAILABLE,
                message="Sounddevice or microphone device not available.",
            ))
            return None

        q = queue.Queue()

        def audio_callback(indata, frames, time_info, status):
            if status:
                logger.debug(f"Audio stream status: {status}")
            q.put(indata.copy())

        chunk_samples = self.chunk_size
        pre_buffer = []
        max_pre_buffer_chunks = int((0.60 * self.sample_rate) / chunk_samples)

        recorded_chunks = []
        ambient_rms_samples = []
        speech_started = False
        speech_peak_rms = 50.0
        silence_start_time = None
        start_time = time.time()
        ambient_mean = 100.0

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                blocksize=chunk_samples,
                dtype="int16",
                channels=self.channels,
                callback=audio_callback,
            ):
                while True:
                    try:
                        chunk_arr = q.get(timeout=0.2)
                    except queue.Empty:
                        if time.time() - start_time > timeout:
                            break
                        continue

                    # Native mono int16 audio
                    raw_mono = chunk_arr.flatten().astype(np.float64)
                    rms = float(np.sqrt(np.mean(raw_mono ** 2)))
                    elapsed_total = time.time() - start_time

                    clipped_chunk = np.clip(raw_mono, -32768, 32767).astype(np.int16)
                    chunk_bytes = clipped_chunk.tobytes()

                    if not speech_started:
                        pre_buffer.append(chunk_bytes)
                        if len(pre_buffer) > max_pre_buffer_chunks:
                            pre_buffer.pop(0)

                        ambient_rms_samples.append(rms)
                        if len(ambient_rms_samples) > 10:
                            ambient_rms_samples.pop(0)

                        ambient_mean = float(np.mean(ambient_rms_samples)) if ambient_rms_samples else 100.0

                        # Ultra-sensitive whisper trigger (+12.0 delta above baseline, zero yelling required)
                        threshold = ambient_mean + 12.0

                        if elapsed_total > timeout:
                            return None

                        if rms > threshold:
                            speech_started = True
                            speech_peak_rms = rms
                            recorded_chunks.extend(pre_buffer)
                            silence_start_time = None
                    else:
                        recorded_chunks.append(chunk_bytes)
                        if rms > speech_peak_rms:
                            speech_peak_rms = rms

                        if elapsed_total > phrase_time_limit:
                            break

                        # Ultra-fast 0.32s silence cutoff for instant command execution
                        silence_cutoff = ambient_mean + 8.0
                        if rms < silence_cutoff:
                            if silence_start_time is None:
                                silence_start_time = time.time()
                            elif time.time() - silence_start_time >= 0.32:
                                break
                        else:
                            silence_start_time = None

            if not recorded_chunks or not speech_started or len(recorded_chunks) < 3:
                return None

            # 1. Combine recorded chunks (Natively 16kHz Mono)
            raw_16k = np.frombuffer(b"".join(recorded_chunks), dtype=np.int16).astype(np.float64)

            # 2. Studio AGC Normalization: Boost quiet natural speech up to 30x
            peak_val = np.max(np.abs(raw_16k)) if len(raw_16k) > 0 else 0
            if peak_val > 20:
                agc_gain = min(30.0, 28000.0 / peak_val)
                raw_16k = np.clip(raw_16k * agc_gain, -32768, 32767).astype(np.int16)
            else:
                raw_16k = raw_16k.astype(np.int16)

            raw_audio = raw_16k.tobytes()
            audio_data = sr.AudioData(raw_audio, 16000, 2)

            # Ultra-fast Parallel STT with instantaneous first-result return
            def _recognize(lang: str) -> Optional[str]:
                try:
                    res = self.recognizer.recognize_google(audio_data, language=lang)
                    if res:
                        return _clean_phonetic_variations(res.strip())
                except Exception:
                    pass
                return None

            stt_start_t = time.time()
            candidates = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = {
                    executor.submit(_recognize, "en-IN"): "en",
                    executor.submit(_recognize, "hi-IN"): "hi",
                }
                for f in concurrent.futures.as_completed(futures, timeout=3.0):
                    try:
                        r = f.result()
                        if r:
                            candidates.append(r)
                            break  # Return instantly on the fastest result!
                    except Exception:
                        pass

            stt_lat_ms = round((time.time() - stt_start_t) * 1000, 1)

            if not candidates:
                diagnostic_engine.record_event(DiagnosticEvent(
                    eventId="EVT-STT-EMPTY",
                    correlationId=cid,
                    category="VOICE",
                    operation="LISTEN_ONCE",
                    stage="STT",
                    status="FAILED",
                    durationMs=stt_lat_ms,
                    errorCode=ErrorCode.VOICE_EMPTY_TRANSCRIPT,
                    message="Speech recognition returned empty transcript.",
                ))
                return None

            # Prioritize genuine action tokens
            def score_candidate(cand: str) -> int:
                score = len(cand)
                c_low = cand.lower()
                action_kws = [
                    "short", "shorts", "video", "click", "scroll", "select", "pause", "rok", "roko",
                    "resume", "play", "chalao", "like", "subscribe", "forward", "aage", "rewind",
                    "peeche", "fullscreen", "theater", "comments", "mute", "unmute", "volume",
                    "speed", "pehla", "pehli", "dusra", "dusri", "teesra", "teesri", "harsh",
                    "call", "message", "whatsapp", "youtube", "chrome", "kholo", "down", "up"
                ]
                for kw in action_kws:
                    if kw in c_low:
                        score += 60
                return score

            best_text = max(candidates, key=score_candidate).strip()
            now = time.time()

            # Debounce rapid duplicate STT emissions within 1.2 seconds
            if self._last_transcript:
                last_text, last_time = self._last_transcript
                if best_text.lower() == last_text.lower() and (now - last_time) < 1.2:
                    diagnostic_engine.record_event(DiagnosticEvent(
                        eventId="EVT-STT-DEBOUNCE",
                        correlationId=cid,
                        category="VOICE",
                        operation="LISTEN_ONCE",
                        stage="STT",
                        status="SKIPPED",
                        errorCode=ErrorCode.VOICE_DUPLICATE_SUPPRESSED,
                        message=f"Suppressed duplicate transcript: '{best_text}'",
                    ))
                    return None

            self._last_transcript = (best_text, now)
            diagnostic_engine.record_event(DiagnosticEvent(
                eventId="EVT-STT-OK",
                correlationId=cid,
                category="VOICE",
                operation="LISTEN_ONCE",
                stage="STT",
                status="SUCCESS",
                durationMs=stt_lat_ms,
                message=f"Recognized: '{best_text}'",
                metadata={"en_candidate": res_en, "hi_candidate": res_hi},
            ))
            logger.info(f"STT_RECOGNIZED: '{best_text}' [en='{res_en}', hi='{res_hi}'] ({stt_lat_ms}ms)")
            return best_text

        except Exception as exc:
            logger.debug(f"Recording error: {exc}")
            diagnostic_engine.record_event(DiagnosticEvent(
                eventId="EVT-MIC-ERR",
                correlationId=cid,
                category="VOICE",
                operation="LISTEN_ONCE",
                stage="MIC",
                status="FAILED",
                errorCode=ErrorCode.VOICE_STT_ERROR,
                message=str(exc),
            ))
            return None


# Global singleton instance
stt_manager = SpeechToTextManager(get_settings())
STTManager = SpeechToTextManager
