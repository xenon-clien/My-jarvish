import sounddevice as sd
import numpy as np
import speech_recognition as sr
import io
import wave

sample_rate = 16000
duration = 3.5

print(f"Recording {duration}s using sounddevice...")
rec = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
sd.wait()
print("Recorded!")

# Build valid WAV in memory
wav_io = io.BytesIO()
with wave.open(wav_io, 'wb') as wav_file:
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)
    wav_file.setframerate(sample_rate)
    wav_file.writeframes(rec.tobytes())
wav_bytes = wav_io.getvalue()

recognizer = sr.Recognizer()
with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
    audio = recognizer.record(source)

print("Recognizing en-IN...")
try:
    res = recognizer.recognize_google(audio, language="en-IN")
    print(f"RESULT en-IN: '{res}'")
except Exception as e:
    print("en-IN error:", e)

print("Recognizing hi-IN...")
try:
    res_hi = recognizer.recognize_google(audio, language="hi-IN")
    print(f"RESULT hi-IN: '{res_hi}'")
except Exception as e:
    print("hi-IN error:", e)
