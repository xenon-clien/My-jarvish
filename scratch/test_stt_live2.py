from backend.voice.speech_to_text import stt_manager
import time

print("Listening for 5 seconds using stt_manager.listen_once()...")
print("Please say: 'video pause karo'")

text = stt_manager.listen_once(timeout=5.0, phrase_time_limit=8.0, silence_limit=0.95)
print(f"\nFinal Transcribed Output: '{text}'")
