from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from jarvis.config import settings


class TTS:
    def __init__(self):
        self._lock = asyncio.Lock()

    async def speak(self, text: str) -> None:
        if not text:
            return
        async with self._lock:
            if settings.tts_provider == "edge":
                ok = await self._edge(text)
                if ok:
                    return
            await asyncio.to_thread(self._sapi, text)

    async def _edge(self, text: str) -> bool:
        try:
            import edge_tts
            import pygame
            fd, path = tempfile.mkstemp(prefix="jarvis_tts_", suffix=".mp3")
            os.close(fd)
            try:
                communicate = edge_tts.Communicate(text, settings.edge_voice, rate=settings.edge_rate, pitch=settings.edge_pitch)
                await communicate.save(path)
                await asyncio.to_thread(self._pygame_play, path, pygame)
                return True
            finally:
                try:
                    Path(path).unlink(missing_ok=True)
                except Exception:
                    pass
        except Exception:
            return False

    @staticmethod
    def _pygame_play(path: str, pygame) -> None:
        pygame.mixer.init()
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        clock = pygame.time.Clock()
        while pygame.mixer.music.get_busy():
            clock.tick(20)
        pygame.mixer.quit()

    @staticmethod
    def _sapi(text: str) -> None:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty("voices") or []
        # Prefer a male English/Indian voice when Windows exposes one.
        for v in voices:
            blob = f"{getattr(v, 'name', '')} {getattr(v, 'id', '')}".lower()
            if any(x in blob for x in ["david", "mark", "male", "guy"]):
                engine.setProperty("voice", v.id)
                break
        engine.setProperty("rate", 155)
        engine.setProperty("volume", 1.0)
        engine.say(text)
        engine.runAndWait()
