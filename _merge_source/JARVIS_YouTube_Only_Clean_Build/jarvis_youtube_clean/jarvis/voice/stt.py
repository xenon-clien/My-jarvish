from __future__ import annotations

import collections
import math
import time

import numpy as np
import sounddevice as sd
import speech_recognition as sr


class SoundDeviceSTT:
    def __init__(self, sample_rate: int = 16000, frame_ms: int = 30):
        self.sample_rate = sample_rate
        self.frame_ms = frame_ms
        self.frame_samples = int(sample_rate * frame_ms / 1000)
        self.recognizer = sr.Recognizer()

    @staticmethod
    def _rms(arr: np.ndarray) -> float:
        if arr.size == 0:
            return 0.0
        x = arr.astype(np.float64)
        return float(math.sqrt(np.mean(x * x)))

    def listen(self, start_timeout: float = 8.0, max_speech: float = 12.0) -> str | None:
        q = collections.deque()
        pre_roll = collections.deque(maxlen=max(1, int(300 / self.frame_ms)))
        ambient_rms = []

        def callback(indata, frames, time_info, status):
            q.append(indata.copy().reshape(-1))

        with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype="int16", blocksize=self.frame_samples, callback=callback):
            ambient_end = time.time() + 0.7
            while time.time() < ambient_end:
                if q:
                    ambient_rms.append(self._rms(q.popleft()))
                else:
                    time.sleep(0.01)

            if ambient_rms:
                median = float(np.median(ambient_rms))
                p90 = float(np.percentile(ambient_rms, 90))
            else:
                median, p90 = 80.0, 100.0
            threshold = max(180.0, median * 1.8, p90 * 1.35, p90 + 55.0)

            started = False
            started_at = None
            last_voice = None
            rolling = collections.deque(maxlen=5)
            audio_frames = []
            deadline = time.time() + start_timeout

            while True:
                if not q:
                    if not started and time.time() > deadline:
                        return None
                    if started and started_at and time.time() - started_at > max_speech:
                        break
                    time.sleep(0.005)
                    continue

                frame = q.popleft()
                rms = self._rms(frame)
                rolling.append(rms > threshold)
                confirmed = len(rolling) >= 5 and sum(rolling) >= 3

                if not started:
                    pre_roll.append(frame)
                    if confirmed:
                        started = True
                        started_at = time.time()
                        last_voice = time.time()
                        audio_frames.extend(list(pre_roll))
                else:
                    audio_frames.append(frame)
                    if rms > threshold:
                        last_voice = time.time()
                    if last_voice and time.time() - last_voice > 0.8:
                        break
                    if started_at and time.time() - started_at > max_speech:
                        break

        if not audio_frames or not started_at or time.time() - started_at < 0.35:
            return None
        raw = np.concatenate(audio_frames).astype(np.int16).tobytes()
        audio = sr.AudioData(raw, self.sample_rate, 2)
        # Try Hindi first, then Indian English. Do not invent a transcript on failure.
        for lang in ("hi-IN", "en-IN"):
            try:
                text = self.recognizer.recognize_google(audio, language=lang)
                if text and text.strip():
                    return text.strip()
            except sr.UnknownValueError:
                continue
            except sr.RequestError:
                return None
        return None
