import sys

for mod in ["sounddevice", "pyaudio", "speech_recognition", "soundfile", "wave"]:
    try:
        __import__(mod)
        print(f"✅ {mod} is installed!")
    except ImportError:
        print(f"❌ {mod} NOT installed!")
