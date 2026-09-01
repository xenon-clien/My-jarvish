"""Test VAD Sensitivity and Speech Recognition Live."""
import time
import numpy as np
import sounddevice as sd
import speech_recognition as sr

def test_live_vad():
    print("==================================================")
    print("Testing Ultra-Sensitive VAD & Speech Recognition...")
    print("Speak naturally or softly for 3 seconds...")
    print("==================================================")
    
    q = []
    def cb(indata, frames, t, s):
        mono = np.mean(indata, axis=1).astype(np.float64) if indata.ndim > 1 else indata.flatten().astype(np.float64)
        q.append(mono)
    
    stream = sd.InputStream(samplerate=44100, channels=2, dtype='int16', blocksize=2048, callback=cb)
    stream.start()
    time.sleep(3.0)
    stream.stop()
    
    all_audio = np.concatenate(q)
    peak = np.max(np.abs(all_audio))
    rms = np.sqrt(np.mean(all_audio ** 2))
    print(f"Recorded 3.0s: Peak={peak:.1f}, RMS={rms:.1f}, Chunks={len(q)}")
    
    # Peak normalize
    if peak > 50:
        gain = min(20.0, 26000.0 / peak)
        boosted = np.clip(all_audio * gain, -32768, 32767).astype(np.int16)
    else:
        boosted = all_audio.astype(np.int16)
        
    # Resample to 16000Hz for Google STT
    duration = len(boosted) / 44100
    num_16k = int(duration * 16000)
    orig_t = np.linspace(0, duration, len(boosted), endpoint=False)
    target_t = np.linspace(0, duration, num_16k, endpoint=False)
    raw_16k = np.interp(target_t, orig_t, boosted).astype(np.int16)
    
    recognizer = sr.Recognizer()
    audio_data = sr.AudioData(raw_16k.tobytes(), 16000, 2)
    
    try:
        text_en = recognizer.recognize_google(audio_data, language="en-IN")
        print(f"✅ Google en-IN Recognized: '{text_en}'")
    except Exception as e:
        print(f"en-IN: {e}")
        
    try:
        text_hi = recognizer.recognize_google(audio_data, language="hi-IN")
        print(f"✅ Google hi-IN Recognized: '{text_hi}'")
    except Exception as e:
        print(f"hi-IN: {e}")

if __name__ == "__main__":
    test_live_vad()
