"""Microsoft Edge Neural TTS Provider for JARVIS AI.

Provides studio-quality, 100% free neural speech synthesis using Microsoft Azure
speech models (Swara, Neerja, Madhur) without requiring API keys or payment.
"""
import asyncio
import os
from typing import Optional
from backend.core.logger import get_logger
from backend.voice.tts_providers.base import TTSProvider, VoiceMetadata
from backend.voice.tts_providers.normalizer import normalize_hindi_tts_text

logger = get_logger("EdgeTTSProvider")

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False


class EdgeTTSProvider(TTSProvider):
    """Microsoft Neural TTS Provider using edge-tts."""

    def __init__(self, voice_id: str = "hi-IN-SwaraNeural", speed_rate: str = "+0%"):
        self.voice_id = voice_id
        self.speed_rate = speed_rate  # e.g. "+0%", "+5%", "-5%"

    def get_metadata(self) -> VoiceMetadata:
        return VoiceMetadata(
            provider_name="Microsoft Edge Neural TTS",
            voice_id=self.voice_id,
            display_name="Microsoft Swara (Natural Hindi Female)",
            language="hi-IN",
            gender="female",
            style="calm, warm, pleasant, respectful, natural conversational",
            is_free=True,
            is_offline=False,
            description="Deep learning neural voice with authentic Indian Hindi pronunciation and zero foreign accent."
        )

    def is_available(self) -> bool:
        return EDGE_TTS_AVAILABLE

    def synthesize(self, text: str, output_path: str, speed_multiplier: float = 1.0) -> bool:
        """Synthesize text to MP3 audio file using Microsoft Edge Neural voice."""
        if not self.is_available() or not text:
            return False

        try:
            # Normalize text for natural Indian pronunciation
            phonetic_text = normalize_hindi_tts_text(text)

            # Calculate rate string
            if speed_multiplier != 1.0:
                pct = int((speed_multiplier - 1.0) * 100)
                rate_str = f"{'+' if pct >= 0 else ''}{pct}%"
            else:
                rate_str = self.speed_rate

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                communicate = edge_tts.Communicate(
                    text=phonetic_text,
                    voice=self.voice_id,
                    rate=rate_str,
                )
                loop.run_until_complete(communicate.save(output_path))
            finally:
                loop.close()

            return os.path.exists(output_path) and os.path.getsize(output_path) > 0
        except Exception as exc:
            logger.warning(f"Edge TTS synthesis failed: {exc}")
            return False
