import speech_recognition as sr
import numpy as np
import wave
import io

print("Testing Automatic Gain Control (AGC) & Normalization on recorded audio...")

with wave.open("scratch/test_mic_output.wav", "rb") as wf:
    params = wf.getparams()
    frames = wf.readframes(params.nframes)

audio_arr = np.frombuffer(frames, dtype=np.int16).astype(np.float64)
peak = np.max(np.abs(audio_arr))
rms = np.sqrt(np.mean(audio_arr ** 2))
print(f"Original Audio -> Peak: {peak:.1f}, RMS: {rms:.1f}")

# Test multiple gain multipliers: 3x, 6x, 10x, 15x, and Peak-Normalized (to 24000)
recognizer = sr.Recognizer()

for gain in [3.0, 6.0, 10.0, 15.0, 24000.0 / max(peak, 1.0)]:
    norm_arr = np.clip(audio_arr * gain, -32768, 32767).astype(np.int16)
    audio_data = sr.AudioData(norm_arr.tobytes(), 16000, 2)
    print(f"\n--- Testing Gain {gain:.2f}x (New Peak: {np.max(np.abs(norm_arr))}) ---")
    
    try:
        res_en = recognizer.recognize_google(audio_data, language="en-IN")
        print(f"  [en-IN Result]: '{res_en}'")
    except Exception as e:
        print(f"  [en-IN Failed]: {type(e).__name__}")
        
    try:
        res_hi = recognizer.recognize_google(audio_data, language="hi-IN")
        print(f"  [hi-IN Result]: '{res_hi}'")
    except Exception as e:
        print(f"  [hi-IN Failed]: {type(e).__name__}")
