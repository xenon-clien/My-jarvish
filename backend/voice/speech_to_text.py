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


from dataclasses import dataclass, field


@dataclass
class NoiseProfile:
    """Statistical noise profile for dynamic VAD envelope calculation."""
    median_rms: float = 150.0
    mean_rms: float = 150.0
    p75_rms: float = 175.0
    p90_rms: float = 200.0
    p95_rms: float = 220.0
    typical_peak: float = 600.0
    timestamp: float = field(default_factory=time.time)
    sample_count: int = 0


class SpeechToTextManager:
    """Queue-buffered microphone recording engine with Multi-Stage VAD, digital AGC, and diagnostic instrumentation."""

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
        self.noise_profile = NoiseProfile()
        self._idle_noise_history = []

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

    def update_noise_profile(self, rms_samples: List[float], peak_samples: List[int]) -> None:
        """Update statistical noise profile using robust percentile metrics."""
        if len(rms_samples) < 5:
            return
        self.noise_profile.median_rms = float(np.median(rms_samples))
        self.noise_profile.mean_rms = float(np.mean(rms_samples))
        self.noise_profile.p75_rms = float(np.percentile(rms_samples, 75))
        self.noise_profile.p90_rms = float(np.percentile(rms_samples, 90))
        self.noise_profile.p95_rms = float(np.percentile(rms_samples, 95))
        self.noise_profile.typical_peak = float(np.percentile(peak_samples, 75))
        self.noise_profile.timestamp = time.time()
        self.noise_profile.sample_count = len(rms_samples)

    def listen_once(
        self,
        timeout: float = 6.0,
        phrase_time_limit: float = 5.5,
        silence_limit: float = 0.55,
        correlation_id: Optional[str] = None,
        debug: Optional[bool] = None,
    ) -> Optional[str]:
        """Capture microphone speech natively in 16kHz Mono with Multi-Stage VAD and real-time AGC."""
        cid = correlation_id or "VOICE-LISTEN"
        is_debug = debug if debug is not None else bool(os.environ.get("JARVIS_VOICE_DEBUG", "0") in ["1", "true", "True"])

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
        max_pre_buffer_chunks = int((0.30 * self.sample_rate) / chunk_samples)  # ~300ms pre-roll

        recorded_chunks = []
        ambient_rms_samples = []
        ambient_peak_samples = []
        candidate_window = []  # rolling 5 frames for consecutive-frame confirmation
        speech_started = False
        speech_peak_rms = 50.0
        speech_peak_amp = 100
        silence_start_time = None
        speech_start_time = None
        start_time = time.time()
        last_debug_log_time = 0.0

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
                    peak = int(np.max(np.abs(raw_mono)))
                    elapsed_total = time.time() - start_time

                    clipped_chunk = np.clip(raw_mono, -32768, 32767).astype(np.int16)
                    chunk_bytes = clipped_chunk.tobytes()

                    # Dynamic Multi-Stage Threshold Calculation
                    noise_ceiling = max(self.noise_profile.p90_rms, self.noise_profile.mean_rms + 20.0, 80.0)
                    adaptive_margin = max(35.0, self.noise_profile.p90_rms * 0.25)
                    speech_start_threshold = noise_ceiling + adaptive_margin
                    silence_cutoff = max(self.noise_profile.p75_rms, self.noise_profile.median_rms * 1.15 + 15.0)

                    # Frame-level speech candidate evidence (energy above noise + separation)
                    is_speech_frame = (rms > speech_start_threshold * 0.88) and (rms - noise_ceiling > 18.0)

                    if is_debug and time.time() - last_debug_log_time >= 0.40:
                        last_debug_log_time = time.time()
                        print(
                            f"  [VOICE_DEBUG] rms={rms:5.1f} | peak={peak:4d} | noise_ceiling={noise_ceiling:5.1f} | "
                            f"start_thresh={speech_start_threshold:5.1f} | candidate_frames={sum(candidate_window)}/5 | "
                            f"speech_started={speech_started}",
                            flush=True
                        )

                    if not speech_started:
                        pre_buffer.append(chunk_bytes)
                        if len(pre_buffer) > max_pre_buffer_chunks:
                            pre_buffer.pop(0)

                        candidate_window.append(is_speech_frame)
                        if len(candidate_window) > 5:
                            candidate_window.pop(0)

                        ambient_rms_samples.append(rms)
                        ambient_peak_samples.append(peak)
                        if len(ambient_rms_samples) > 25:
                            ambient_rms_samples.pop(0)
                            ambient_peak_samples.pop(0)

                        # Update background noise profile when no speech candidate is active
                        if not any(candidate_window):
                            self._idle_noise_history.append((rms, peak))
                            if len(self._idle_noise_history) > 35:
                                self._idle_noise_history.pop(0)
                            if len(self._idle_noise_history) >= 8:
                                r_l = [x[0] for x in self._idle_noise_history]
                                p_l = [x[1] for x in self._idle_noise_history]
                                self.update_noise_profile(r_l, p_l)

                        if elapsed_total > timeout:
                            return None

                        # Multi-Stage Gate: Require at least 3 of last 5 frames AND current frame above start threshold
                        if sum(candidate_window) >= 3 and rms > speech_start_threshold:
                            speech_started = True
                            speech_start_time = time.time()
                            speech_peak_rms = rms
                            speech_peak_amp = peak
                            recorded_chunks.extend(pre_buffer)
                            silence_start_time = None
                            if is_debug:
                                print(f"\n  [VAD_SPEECH_START] rms={rms:.1f} > thresh={speech_start_threshold:.1f} (pre-buffer: {len(pre_buffer)} chunks)", flush=True)
                    else:
                        recorded_chunks.append(chunk_bytes)
                        if rms > speech_peak_rms:
                            speech_peak_rms = rms
                        if peak > speech_peak_amp:
                            speech_peak_amp = peak

                        speech_duration = time.time() - speech_start_time

                        # False-start protection: If within first 0.35s the signal collapses back to ambient noise, abort candidate
                        if speech_duration >= 0.30 and len(recorded_chunks) <= (max_pre_buffer_chunks + 5):
                            recent_rms = rms
                            if recent_rms < noise_ceiling:
                                if is_debug:
                                    print(f"  [VAD_FALSE_START] Transient noise spike aborted (duration: {speech_duration:.2f}s).", flush=True)
                                # Reset state back to listening
                                speech_started = False
                                recorded_chunks.clear()
                                candidate_window.clear()
                                continue

                        if elapsed_total > phrase_time_limit:
                            break

                        # Dynamic silence cutoff hysteresis
                        if rms < silence_cutoff:
                            if silence_start_time is None:
                                silence_start_time = time.time()
                            elif time.time() - silence_start_time >= silence_limit:
                                if is_debug:
                                    print(f"  [VAD_SPEECH_END] Silence duration: {time.time() - silence_start_time:.2f}s, Total: {speech_duration:.2f}s", flush=True)
                                break
                        else:
                            silence_start_time = None

            if not recorded_chunks or not speech_started or len(recorded_chunks) < 4:
                return None

            # 1. Combine recorded chunks (Natively 16kHz Mono)
            raw_16k = np.frombuffer(b"".join(recorded_chunks), dtype=np.int16).astype(np.float64)

            # 2. Post-Capture Validity Check (Do NOT send noise to Google STT)
            phrase_peak = float(np.max(np.abs(raw_16k))) if len(raw_16k) > 0 else 0
            phrase_mean_rms = float(np.sqrt(np.mean(raw_16k ** 2))) if len(raw_16k) > 0 else 0
            if phrase_mean_rms < self.noise_profile.p90_rms + 25.0 or phrase_peak < self.noise_profile.typical_peak * 1.25:
                if is_debug:
                    print(f"  [STT_SKIPPED] Captured audio has no SNR separation from ambient noise (Peak: {phrase_peak:.0f}, RMS: {phrase_mean_rms:.1f}).", flush=True)
                return None

            # 3. Studio AGC Normalization: Boost quiet natural speech up to 30x
            if phrase_peak > 20:
                agc_gain = min(30.0, 28000.0 / phrase_peak)
                raw_16k = np.clip(raw_16k * agc_gain, -32768, 32767).astype(np.int16)
            else:
                raw_16k = raw_16k.astype(np.int16)

            raw_audio = raw_16k.tobytes()
            audio_data = sr.AudioData(raw_audio, 16000, 2)

            # Ultra-fast Parallel STT with instantaneous first-result return
            res_en = None
            res_hi = None

            def _recognize_en() -> Optional[str]:
                nonlocal res_en
                try:
                    res = self.recognizer.recognize_google(audio_data, language="en-IN")
                    if res:
                        res_en = _clean_phonetic_variations(res.strip())
                        return res_en
                except Exception:
                    pass
                return None

            def _recognize_hi() -> Optional[str]:
                nonlocal res_hi
                try:
                    res = self.recognizer.recognize_google(audio_data, language="hi-IN")
                    if res:
                        res_hi = _clean_phonetic_variations(res.strip())
                        return res_hi
                except Exception:
                    pass
                return None

            stt_start_t = time.time()
            candidates = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = {
                    executor.submit(_recognize_en): "en",
                    executor.submit(_recognize_hi): "hi",
                }
                for f in concurrent.futures.as_completed(futures, timeout=3.5):
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

