import sounddevice as sd
import numpy as np
import speech_recognition as sr
import time
import wave
import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

print("=" * 60)
print("LIVE MICROPHONE HARDWARE & STT FORENSIC DIAGNOSTIC")
print("=" * 60)

devices = sd.query_devices()
print("\n1. All Audio Devices:")
for i, d in enumerate(devices):
    if d['max_input_channels'] > 0:
        print(f"   [{i}] {d['name']} (Inputs: {d['max_input_channels']}, Default SR: {d['default_samplerate']})")

default_input = sd.query_devices(kind='input')
print(f"\n2. Selected Default Input: {default_input['name']} (Index: {default_input['index']})")

sample_rate = int(default_input.get('default_samplerate', 44100))
channels = int(default_input.get('max_input_channels', 2))

print(f"\n3. Testing 3 seconds of live audio capture at {sample_rate}Hz, {channels} channels...")
recorded_frames = []

def callback(indata, frames, time_info, status):
    if status:
        print(f"Status flag: {status}")
    recorded_frames.append(indata.copy())

with sd.InputStream(samplerate=sample_rate, channels=channels, dtype="int16", callback=callback):
    for i in range(15):
        time.sleep(0.2)
        if recorded_frames:
            latest = recorded_frames[-1]
            if channels > 1:
                mono = np.mean(latest, axis=1)
            else:
                mono = latest.flatten()
            rms = float(np.sqrt(np.mean(mono.astype(np.float64) ** 2)))
            bars = int(min(50, rms / 20))
            print(f"\rLive Volume RMS: {rms:6.1f} | {'#' * bars}{' ' * (50 - bars)}|", end="", flush=True)

print("\n\n4. Processing Recorded Audio...")
if recorded_frames:
    all_data = np.concatenate(recorded_frames, axis=0)
    print(f"Captured {len(all_data)} samples ({len(all_data) / sample_rate:.2f} seconds)")
    
    if channels > 1:
        mono_data = np.mean(all_data, axis=1).astype(np.float64) * 3.0
    else:
        mono_data = all_data.flatten().astype(np.float64) * 3.0
        
    mono_int16 = np.clip(mono_data, -32768, 32767).astype(np.int16)
    
    # Save to WAV
    wav_path = "scratch/test_mic_output.wav"
    os.makedirs("scratch", exist_ok=True)
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(mono_int16.tobytes())
    print(f"Saved audio to {wav_path} (Size: {os.path.getsize(wav_path)} bytes)")
    
    print("\n5. Testing Google Speech Recognition on captured audio...")
    recognizer = sr.Recognizer()
    audio_data = sr.AudioData(mono_int16.tobytes(), sample_rate, 2)
    
    try:
        t0 = time.time()
        text_en = recognizer.recognize_google(audio_data, language="en-IN")
        print(f"   [en-IN Result] ({time.time()-t0:.2f}s): '{text_en}'")
    except sr.UnknownValueError:
        print("   [en-IN Result]: <No speech detected / Silence>")
    except Exception as exc:
        print(f"   [en-IN Error]: {exc}")
        
    try:
        t0 = time.time()
        text_hi = recognizer.recognize_google(audio_data, language="hi-IN")
        print(f"   [hi-IN Result] ({time.time()-t0:.2f}s): '{text_hi}'")
    except sr.UnknownValueError:
        print("   [hi-IN Result]: <No speech detected / Silence>")
    except Exception as exc:
        print(f"   [hi-IN Error]: {exc}")

print("\n" + "=" * 60)
print("DIAGNOSTIC TEST COMPLETE")
print("=" * 60)
