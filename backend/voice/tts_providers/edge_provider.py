"""Microsoft Edge Neural TTS Provider for JARVIS AI.

Provides studio-quality, 100% free neural speech synthesis using Microsoft Azure
speech models (Swara, Neerja, Madhur) without requiring API keys or payment.
"""
import asyncio
import os
import time
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

    def __init__(self, voice_id: str = "hi-IN-MadhurNeural", speed_rate: str = "-4%", pitch: str = "-22Hz"):
        self.voice_id = voice_id
        self.speed_rate = speed_rate  # e.g. "+0%", "-4%"
        self.pitch = pitch  # e.g. "-22Hz" for deep heavy superhero baritone

    def get_metadata(self) -> VoiceMetadata:
        is_madhur = "madhur" in self.voice_id.lower()
        return VoiceMetadata(
            provider_name="Microsoft Edge Neural TTS",
            voice_id=self.voice_id,
            display_name="Captain America (Deep Heavy Baritone Hindi Voice)" if (is_madhur and self.pitch) else ("Microsoft Madhur (Male)" if is_madhur else "Microsoft Swara (Female)"),
            language="hi-IN",
            gender="male" if is_madhur else "female",
            style="commanding, deep, heavy, heroic, loyal baritone" if (is_madhur and self.pitch) else "natural conversational",
            is_free=True,
            is_offline=False,
            description="Deep resonant baritone superhero voice in Hindi with zero robotic accent."
        )

    def is_available(self) -> bool:
        return EDGE_TTS_AVAILABLE

    def synthesize(self, text: str, output_path: str, speed_multiplier: float = 1.0) -> bool:
        """Synthesize text to MP3 audio file using Microsoft Edge Neural voice with automatic retry."""
        if not self.is_available() or not text:
            return False

        # Normalize text for natural Indian pronunciation
        phonetic_text = normalize_hindi_tts_text(text)

        # Calculate rate string
        if speed_multiplier != 1.0:
            pct = int((speed_multiplier - 1.0) * 100)
            rate_str = f"{'+' if pct >= 0 else ''}{pct}%"
        else:
            rate_str = self.speed_rate

        import concurrent.futures

        attempts = [
            {"pitch": self.pitch, "rate": rate_str},
            {"pitch": self.pitch, "rate": rate_str},  # Retry 1: Transient network reset
            {"pitch": "+0Hz", "rate": rate_str},     # Retry 2: Standard pitch fallback
        ]

        for attempt_idx, params in enumerate(attempts):
            try:
                def _run_save():
                    worker_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(worker_loop)
                    try:
                        communicate = edge_tts.Communicate(
                            text=phonetic_text,
                            voice=self.voice_id,
                            rate=params["rate"],
                            pitch=params["pitch"],
                        )
                        worker_loop.run_until_complete(communicate.save(output_path))
                    finally:
                        worker_loop.close()

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_run_save)
                    future.result(timeout=15.0)

                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    return True
            except Exception as exc:
                logger.warning(f"Edge TTS attempt {attempt_idx + 1} failed ({exc}), retrying...")
                time.sleep(0.20)

        logger.error(f"All Edge TTS attempts failed for voice '{self.voice_id}'")
        return False
