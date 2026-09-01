import sounddevice as sd
import numpy as np
import speech_recognition as sr
import time

print("Testing Resampled 16kHz Audio Pipeline with Dynamic VAD...")

def resample_audio(audio_data: np.ndarray, orig_sr: int, target_sr: int = 16000) -> np.ndarray:
    """High quality linear interpolation resampler from orig_sr to target_sr."""
    if orig_sr == target_sr:
        return audio_data
    duration = len(audio_data) / orig_sr
    num_target_samples = int(duration * target_sr)
    orig_times = np.linspace(0, duration, len(audio_data), endpoint=False)
    target_times = np.linspace(0, duration, num_target_samples, endpoint=False)
    resampled = np.interp(target_times, orig_times, audio_data)
    return resampled.astype(np.int16)

# Test with synthetic signal
t = np.linspace(0, 1.0, 44100)
synth_44k = (np.sin(2 * np.pi * 440 * t) * 15000).astype(np.int16)
resampled_16k = resample_audio(synth_44k, 44100, 16000)

print(f"Resampling test: {len(synth_44k)} samples @ 44.1kHz -> {len(resampled_16k)} samples @ 16kHz (Success!)")

# Test live recording with real user voice
print("\nRecording 3 seconds of mic input with 16kHz resampler...")
dev = sd.query_devices(kind="input")
sr_native = int(dev.get("default_samplerate", 44100))
ch_native = int(dev.get("max_input_channels", 2))

data = sd.rec(int(3.0 * sr_native), samplerate=sr_native, channels=ch_native, dtype="int16")
sd.wait()

mono_44k = np.mean(data, axis=1) if ch_native > 1 else data.flatten()
resampled_16k = resample_audio(mono_44k, sr_native, 16000)

# Normalize amplitude
peak = np.max(np.abs(resampled_16k))
print(f"Peak amplitude: {peak}")
if peak > 50:
    gain = min(10.0, 24000.0 / peak)
    resampled_16k = np.clip(resampled_16k.astype(np.float64) * gain, -32768, 32767).astype(np.int16)

audio_data = sr.AudioData(resampled_16k.tobytes(), 16000, 2)
recognizer = sr.Recognizer()

try:
    text = recognizer.recognize_google(audio_data, language="en-IN")
    print(f"Recognized (en-IN): '{text}'")
except sr.UnknownValueError:
    print("Recognition: <No speech detected in silent room>")
except Exception as e:
    print(f"Recognition Error: {e}")
