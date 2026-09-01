"""ElevenLabs AI Voice Provider for JARVIS AI (Optional Plugin).

Supports studio-grade ultra-realistic voices when an API key is provided.
Disabled by default to ensure 100% free and cost-safe operation.
"""
import os
import requests
from backend.core.logger import get_logger
from backend.voice.tts_providers.base import TTSProvider, VoiceMetadata

logger = get_logger("ElevenLabsProvider")


class ElevenLabsProvider(TTSProvider):
    """ElevenLabs Multilingual TTS Provider."""

    def __init__(self, api_key: str = "", voice_id: str = "21m00Tcm4TlvDq8ikWAM"):  # Rachel / Default
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY", "")
        self.voice_id = voice_id

    def get_metadata(self) -> VoiceMetadata:
        return VoiceMetadata(
            provider_name="ElevenLabs",
            voice_id=self.voice_id,
            display_name="ElevenLabs Multilingual AI Voice",
            language="hi-IN/en-US",
            gender="female",
            style="studio realistic",
            is_free=False,
            is_offline=False,
            description="Ultra-realistic studio AI voice (requires personal API key)."
        )

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def synthesize(self, text: str, output_path: str, speed_multiplier: float = 1.0) -> bool:
        """Synthesize text using ElevenLabs REST API."""
        if not self.is_available() or not text:
            return False

        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
            }
            payload = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.8,
                }
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=10.0)
            if resp.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                return True
            else:
                logger.warning(f"ElevenLabs API returned {resp.status_code}: {resp.text}")
                return False
        except Exception as exc:
            logger.warning(f"ElevenLabs synthesis error: {exc}")
            return False
