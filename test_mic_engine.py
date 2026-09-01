import sys
import speech_recognition as sr

print("SpeechRecognition version:", sr.__version__)
try:
    with sr.Microphone() as source:
        print("Microphone initialized successfully via speech_recognition!")
except Exception as e:
    print("Microphone initialization error:", e)
