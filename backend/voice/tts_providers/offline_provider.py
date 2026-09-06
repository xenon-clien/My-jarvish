"""Windows SAPI5 Offline TTS Provider for JARVIS AI.

Guarantees 100% offline failsafe speech synthesis without any internet connection.
"""
import os
import pyttsx3
from backend.core.logger import get_logger
from backend.voice.tts_providers.base import TTSProvider, VoiceMetadata

logger = get_logger("OfflineTTSProvider")

try:
    import pythoncom
    PYTHONCOM_AVAILABLE = True
except ImportError:
    PYTHONCOM_AVAILABLE = False


def ensure_com():
    if PYTHONCOM_AVAILABLE:
        try:
            pythoncom.CoInitialize()
        except Exception:
            pass


class OfflineTTSProvider(TTSProvider):
    """Offline Windows SAPI5 engine provider."""

    def __init__(self, rate: int = 180, volume: float = 1.0, gender: str = "male"):
        self.rate = rate
        self.volume = volume
        self.gender = gender.lower()

    def get_metadata(self) -> VoiceMetadata:
        return VoiceMetadata(
            provider_name="Windows SAPI5 (Offline)",
            voice_id="offline_sapi5",
            display_name=f"Windows Offline Voice ({self.gender.title()})",
            language="en-US/hi",
            gender=self.gender,
            style="offline standard",
            is_free=True,
            is_offline=True,
            description="Offline local Windows speech synthesizer."
        )

    def is_available(self) -> bool:
        return True

    def synthesize(self, text: str, output_path: str, speed_multiplier: float = 1.0) -> bool:
        """Synthesize text to WAV/audio file using pyttsx3 offline."""
        if not text:
            return False

        ensure_com()
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", int(self.rate * speed_multiplier))
            engine.setProperty("volume", self.volume)

            voices = engine.getProperty("voices")
            if voices:
                selected_voice = None
                if self.gender == "male":
                    for v in voices:
                        if any(k in v.name.lower() for k in ["david", "mark", "george", "male", "ravi", "hemant"]):
                            selected_voice = v.id
                            break
                else:
                    for v in voices:
                        if any(k in v.name.lower() for k in ["zira", "eva", "kalpana", "female", "heera"]):
                            selected_voice = v.id
                            break

                if selected_voice:
                    engine.setProperty("voice", selected_voice)
                elif voices:
                    engine.setProperty("voice", voices[0].id)

            # Save to target file
            engine.save_to_file(text, output_path)
            engine.runAndWait()
            return os.path.exists(output_path) and os.path.getsize(output_path) > 0
        except Exception as exc:
            logger.warning(f"Offline SAPI5 synthesis failed: {exc}")
            return False
