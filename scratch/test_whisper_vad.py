import sounddevice as sd
import numpy as np
import time

print("=" * 60)
print("TESTING SENSITIVITY VAD WITH UNAMPLIFIED ADAPTIVE BASELINE")
print("=" * 60)

sample_rate = 44100
chunk_size = 2048
duration = 4.0

ambient_samples = []
speech_triggered = False

def callback(indata, frames, time_info, status):
    global speech_triggered
    mono = np.mean(indata, axis=1) if indata.ndim > 1 else indata.flatten()
    raw_rms = float(np.sqrt(np.mean(mono.astype(np.float64) ** 2)))
    
    if len(ambient_samples) < 20:
        ambient_samples.append(raw_rms)
        return
    
    ambient_mean = float(np.mean(ambient_samples[-20:]))
    ambient_std = float(np.std(ambient_samples[-20:]))
    # Whisper-level sensitive trigger: just 1.5 standard deviations above noise floor
    threshold = ambient_mean + max(12.0, ambient_std * 2.0 + 15.0)
    
    if raw_rms > threshold:
        speech_triggered = True
        print(f"-> SPEECH DETECTED! Raw RMS: {raw_rms:.1f} (Threshold: {threshold:.1f}, Noise Floor: {ambient_mean:.1f})")
    else:
        ambient_samples.append(raw_rms)
        if len(ambient_samples) > 50:
            ambient_samples.pop(0)

with sd.InputStream(samplerate=sample_rate, blocksize=chunk_size, dtype="int16", channels=1, callback=callback):
    print("Listening for 3 seconds... Please speak normally or whisper:")
    time.sleep(3.0)

print(f"Test Finished. Speech Triggered: {speech_triggered}")
