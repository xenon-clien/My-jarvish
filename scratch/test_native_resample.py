import sounddevice as sd
import numpy as np
import speech_recognition as sr
import io
import wave

print("Testing Native 44100Hz Stereo Recording -> Mono 16000Hz Resampling...")

sample_rate_native = 44100
target_sample_rate = 16000
duration = 4.0

print(f"Recording {duration}s at native 44100Hz...")
rec_native = sd.rec(int(duration * sample_rate_native), samplerate=sample_rate_native, channels=2, dtype='int16')
sd.wait()
print("Done recording!")

# Convert Stereo to Mono (average channels)
mono_44k = rec_native.astype(np.float64).mean(axis=1)

# Resample from 44100Hz to 16000Hz
num_target_samples = int(len(mono_44k) * target_sample_rate / sample_rate_native)
indices = np.linspace(0, len(mono_44k) - 1, num_target_samples)
mono_16k = np.interp(indices, np.arange(len(mono_44k)), mono_44k)

# Normalize / AGC
peak = np.max(np.abs(mono_16k))
gain = min(10.0, 20000.0 / max(peak, 1.0))
amplified = np.clip(mono_16k * gain, -32768, 32767).astype(np.int16)

print(f"Native Peak: {peak:.1f} -> Amplified Peak: {np.max(np.abs(amplified))} (Gain: {gain:.2f}x)")

# Build WAV
wav_io = io.BytesIO()
with wave.open(wav_io, 'wb') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(target_sample_rate)
    wf.writeframes(amplified.tobytes())

recognizer = sr.Recognizer()
with sr.AudioFile(io.BytesIO(wav_io.getvalue())) as src:
    audio = recognizer.record(src)

try:
    res = recognizer.recognize_google(audio, language="en-IN")
    print(f"✅ Google STT (en-IN): '{res}'")
except Exception as e:
    print(f"en-IN: {type(e).__name__}")

try:
    res_hi = recognizer.recognize_google(audio, language="hi-IN")
    print(f"✅ Google STT (hi-IN): '{res_hi}'")
except Exception as e:
    print(f"hi-IN: {type(e).__name__}")
