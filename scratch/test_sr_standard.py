import speech_recognition as sr
import time

print("Testing standard speech_recognition.Microphone() capture...")
recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.energy_threshold = 300

try:
    with sr.Microphone() as source:
        print(f"Adjusting for ambient noise for 0.5s... (current energy: {recognizer.energy_threshold})")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        print(f"Calibrated energy threshold: {recognizer.energy_threshold}")
        print("Listening for 3 seconds...")
        audio = recognizer.listen(source, timeout=3.0, phrase_time_limit=4.0)
        print(f"Captured audio data: {len(audio.frame_data)} bytes at {audio.sample_rate}Hz")
        
        try:
            text = recognizer.recognize_google(audio, language="en-IN")
            print(f"Recognized (en-IN): '{text}'")
        except Exception as e:
            print(f"Recognition result: {e}")
except Exception as exc:
    print(f"SR Microphone Error: {exc}")
