"""Unit tests for configuration parsing and validation."""
from pathlib import Path
from backend.core.config import Settings


def test_default_settings():
    """Verify default settings initialization."""
    settings = Settings()
    assert settings.APP_NAME == "JARVIS"
    assert settings.AI_PROVIDER in ["astra", "mock", "openrouter", "gemini", "openai", "ollama"]
    assert isinstance(settings.ALLOWED_DIRECTORIES, list)


def test_allowed_directories_parsing():
    """Test parsing string list into normalized paths."""
    settings = Settings(
        ALLOWED_DIRECTORIES="C:/Users/test/Downloads, C:/Users/test/Desktop"
    )
    assert len(settings.ALLOWED_DIRECTORIES) == 2
    assert str(Path("C:/Users/test/Downloads").resolve()) in settings.ALLOWED_DIRECTORIES
