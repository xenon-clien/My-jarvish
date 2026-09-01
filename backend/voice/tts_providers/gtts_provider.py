"""Google Cloud / gTTS Hindi Provider for JARVIS AI.

Provides sweet, pleasant, and natural Indian Hindi female voice synthesis
using Google's official text-to-speech engine.
"""
import os
from backend.core.logger import get_logger
from backend.voice.tts_providers.base import TTSProvider, VoiceMetadata
from backend.voice.tts_providers.normalizer import normalize_hindi_tts_text

logger = get_logger("GoogleTTSProvider")

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False


class GoogleTTSProvider(TTSProvider):
    """Google Cloud Hindi TTS Provider using gTTS."""

    def __init__(self, lang: str = "hi", tld: str = "co.in"):
        self.lang = lang
        self.tld = tld

    def get_metadata(self) -> VoiceMetadata:
        return VoiceMetadata(
            provider_name="Google Cloud TTS (gTTS)",
            voice_id="google_hindi",
            display_name="Google Hindi Voice (Natural Sweet Female)",
            language="hi-IN",
            gender="female",
            style="sweet, clear, natural, helpful",
            is_free=True,
            is_offline=False,
            description="Google Assistant Indian Hindi female voice with fluent pronunciation."
        )

    def is_available(self) -> bool:
        return GTTS_AVAILABLE

    def synthesize(self, text: str, output_path: str, speed_multiplier: float = 1.0) -> bool:
        """Synthesize text to MP3 audio file using Google TTS."""
        if not self.is_available() or not text:
            return False

        try:
            phonetic_text = normalize_hindi_tts_text(text)
            tts = gTTS(text=phonetic_text, lang=self.lang, tld=self.tld, slow=(speed_multiplier < 0.85))
            tts.save(output_path)
            return os.path.exists(output_path) and os.path.getsize(output_path) > 0
        except Exception as exc:
            logger.warning(f"Google TTS synthesis failed: {exc}")
            return False
