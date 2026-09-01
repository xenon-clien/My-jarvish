import sounddevice as sd
import numpy as np
import speech_recognition as sr
import time

print("Testing microphone live...")
devices = sd.query_devices()
print("Default input device:", sd.query_devices(kind='input'))

sample_rate = 16000
duration = 4.0
print(f"\nRecording {duration} seconds... Please say 'Video pause karo' now!")

recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
sd.wait()
print("Recording complete!")

data = recording.flatten().astype(np.float64)
rms = float(np.sqrt(np.mean(data ** 2)))
peak = float(np.max(np.abs(data)))
print(f"Recorded Audio Stats -> RMS: {rms:.2f}, Peak: {peak:.2f}")

recognizer = sr.Recognizer()
raw_bytes = (recording * 1.8).clip(-32768, 32767).astype(np.int16).tobytes()
audio_data = sr.AudioData(raw_bytes, sample_rate, 2)

try:
    res_en = recognizer.recognize_google(audio_data, language="en-IN")
    print(f"Google STT (en-IN): '{res_en}'")
except Exception as e:
    print(f"Google STT (en-IN) Error: {e}")

try:
    res_hi = recognizer.recognize_google(audio_data, language="hi-IN")
    print(f"Google STT (hi-IN): '{res_hi}'")
except Exception as e:
    print(f"Google STT (hi-IN) Error: {e}")
