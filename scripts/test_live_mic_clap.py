"""Interactive Live Microphone Clap Calibrator.

Shows live audio energy levels, crest factors, and triggers instant sound beeps
when you clap in front of your microphone.
"""
import os
import sys
import time
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

try:
    import sounddevice as sd
except ImportError:
    print("sounddevice not installed!")
    sys.exit(1)

try:
    import winsound
    def beep_clap():
        winsound.Beep(1200, 80)
    def beep_double():
        winsound.Beep(1500, 150)
        winsound.Beep(2000, 200)
except Exception:
    def beep_clap(): pass
    def beep_double(): pass

print("==================================================")
print("🎙️ LIVE MICROPHONE CLAP MONITOR & TESTER 🎙️")
print("Taali bajayein (Clap)! Aapko screen par live peak aur beeps sunai denge.")
print("Press Ctrl+C to stop.")
print("==================================================")

last_clap_time = 0.0
ambient_rms = 0.005
digital_gain = 4.0

def audio_callback(indata, frames, time_info, status):
    global last_clap_time, ambient_rms
    now = time.time()
    audio = indata[:, 0] if indata.ndim > 1 else indata
    boosted = np.clip(audio * digital_gain, -1.0, 1.0)
    
    peak = float(np.max(np.abs(boosted)))
    rms = float(np.sqrt(np.mean(boosted**2)))
    ambient_rms = 0.95 * ambient_rms + 0.05 * rms
    
    crest = peak / (rms + 1e-6)
    
    # Check if frame is a clap
    # A clap has high peak relative to ambient, and high crest factor
    if peak > 0.035 and crest >= 1.8:
        time_since_last = now - last_clap_time
        if time_since_last < 0.08:
            # Echo / reverb
            pass
        elif 0.08 <= time_since_last <= 1.0:
            print(f"\n👏👏 >>> DOUBLE CLAP DETECTED! (Interval: {time_since_last:.2f}s) <<<")
            print("🚀 Starting JARVIS now...")
            last_clap_time = 0.0
            beep_double()
            try:
                import subprocess
                subprocess.Popen(["cmd.exe", "/c", "start \"\" \"run_jarvis.bat\""], cwd=BASE_DIR, shell=True)
            except Exception as e:
                print(f"Error launching: {e}")
        else:
            print(f"\n👏 Single Clap Detected! (Peak: {peak:.3f}, Crest: {crest:.1f}) -> Bajayein Dusri Taali...")
            last_clap_time = now
            beep_clap()

try:
    with sd.InputStream(samplerate=22050, blocksize=1024, channels=1, dtype="float32", callback=audio_callback):
        while True:
            time.sleep(0.1)
except KeyboardInterrupt:
    print("\nLive monitor stopped.")
