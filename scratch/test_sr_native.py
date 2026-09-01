import speech_recognition as sr
import time

print("Testing SpeechRecognition standard Microphone...")
recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.pause_threshold = 0.8

try:
    with sr.Microphone() as source:
        print("Calibrating ambient noise for 0.5s...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        print(f"Energy threshold set to: {recognizer.energy_threshold}")
        print("\nSay 'video pause karo' now (listening for 4 seconds)...")
        audio = recognizer.listen(source, timeout=4.0, phrase_time_limit=4.0)
        print("Audio captured! Sending to Google STT...")
        
        try:
            res_en = recognizer.recognize_google(audio, language="en-IN")
            print(f"Google STT (en-IN): '{res_en}'")
        except Exception as e:
            print(f"Google STT (en-IN) Error: {e}")
            
        try:
            res_hi = recognizer.recognize_google(audio, language="hi-IN")
            print(f"Google STT (hi-IN): '{res_hi}'")
        except Exception as e:
            print(f"Google STT (hi-IN) Error: {e}")
            
except Exception as exc:
    print(f"sr.Microphone Error: {exc}")
