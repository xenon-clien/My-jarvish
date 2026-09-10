from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _csv(name: str, default: str = "") -> tuple[str, ...]:
    return tuple(x.strip().lower() for x in os.getenv(name, default).split(",") if x.strip())


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    data_dir: Path = ROOT / "data"
    logs_dir: Path = ROOT / "logs"

    enabled_apps: tuple[str, ...] = _csv("JARVIS_ENABLED_APPS", "youtube")

    explabs_api_key: str = os.getenv("EXPLABS_API_KEY", "").strip()
    explabs_base_url: str = os.getenv("EXPLABS_BASE_URL", "https://api.experimentallabs.ai/v1").rstrip("/")
    astra_model: str = os.getenv("ASTRA_MODEL", "gpt-6-astra").strip()

    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model: str = os.getenv("GEMINI_FALLBACK_MODEL", "").strip()

    cdp_url: str = os.getenv("CHROME_CDP_URL", "http://127.0.0.1:9222").strip()

    tts_provider: str = os.getenv("JARVIS_TTS_PROVIDER", "edge").strip().lower()
    edge_voice: str = os.getenv("JARVIS_EDGE_VOICE", "en-US-GuyNeural").strip()
    edge_rate: str = os.getenv("JARVIS_EDGE_RATE", "-8%").strip()
    edge_pitch: str = os.getenv("JARVIS_EDGE_PITCH", "-8Hz").strip()

    request_timeout_s: float = float(os.getenv("JARVIS_AI_TIMEOUT", "20"))


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.logs_dir.mkdir(parents=True, exist_ok=True)
