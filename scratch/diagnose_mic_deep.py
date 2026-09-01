import sounddevice as sd
import numpy as np
import speech_recognition as sr
import wave
import io
import time
import os

print("=" * 60)
print("[DIAGNOSTIC] DEEP MICROPHONE & AUDIO PIPELINE DIAGNOSIS")
print("=" * 60)

# 1. Device enumeration
print("\n--- 1. AUDIO INPUT DEVICES ---")
devices = sd.query_devices()
for idx, d in enumerate(devices):
    if d.get("max_input_channels", 0) > 0:
        is_def = " (DEFAULT)" if idx == sd.default.device[0] else ""
        print(f"[{idx}] {d.get('name')} | Channels: {d.get('max_input_channels')} | Sample Rate: {d.get('default_samplerate')}{is_def}")

# 2. Test Recording for 5 seconds
sample_rate = 16000
duration = 5.0
print(f"\n--- 2. RECORDING FOR {duration} SECONDS ---")
print(">>> PLEASE SPEAK LOUDLY INTO YOUR MICROPHONE NOW: 'VIDEO PAUSE KARO' <<<")

start_t = time.time()
rec = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype="int16")
sd.wait()
print(f"Recording finished in {time.time() - start_t:.2f}s.")

# 3. Waveform analysis
data = rec.flatten()
rms = float(np.sqrt(np.mean(data.astype(np.float64) ** 2)))
peak = int(np.max(np.abs(data)))
non_zero = int(np.count_nonzero(data))
total = len(data)

print(f"\n--- 3. RAW WAVEFORM ANALYSIS ---")
print(f"Total Samples: {total}")
print(f"Non-Zero Samples: {non_zero} ({non_zero/total*100:.1f}%)")
print(f"Signal RMS: {rms:.2f}")
print(f"Peak Amplitude: {peak} / 32767")

if rms < 5.0 and peak < 20:
    print("\n🚨 CRITICAL WARNING: Audio is almost COMPLETELY SILENT (RMS < 5.0)!")
    print("Possibilities:")
    print("1. Laptop microphone hardware is muted in Windows / Function key (F8/F9/F4).")
    print("2. Windows Microphone Privacy Setting is blocking Python / Desktop apps.")
    print("3. Wrong input device selected.")

# 4. Save to WAV for testing
wav_path = os.path.abspath("scratch/test_mic_output.wav")
with wave.open(wav_path, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sample_rate)
    wf.writeframes(rec.tobytes())
print(f"\nSaved raw audio to: {wav_path} ({os.path.getsize(wav_path)} bytes)")

# 5. Test SpeechRecognition on saved WAV
print(f"\n--- 4. SPEECH RECOGNITION ATTEMPT ---")
recognizer = sr.Recognizer()
with sr.AudioFile(wav_path) as src:
    audio = recognizer.record(src)

try:
    res_en = recognizer.recognize_google(audio, language="en-IN")
    print(f"✅ Google STT (en-IN): '{res_en}'")
except sr.UnknownValueError:
    print("❌ Google STT (en-IN): UnknownValueError (No speech detected in audio)")
except Exception as e:
    print(f"❌ Google STT (en-IN) Error: {e}")

try:
    res_hi = recognizer.recognize_google(audio, language="hi-IN")
    print(f"✅ Google STT (hi-IN): '{res_hi}'")
except sr.UnknownValueError:
    print("❌ Google STT (hi-IN): UnknownValueError (No speech detected in audio)")
except Exception as e:
    print(f"❌ Google STT (hi-IN) Error: {e}")

print("=" * 60)
