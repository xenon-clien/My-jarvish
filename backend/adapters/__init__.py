"""JARVIS Application Adapters Package.

Encapsulates application-specific logic behind clean, typed, verifiable interfaces:
- YouTubeAdapter: Wraps browser_tools & media_tools YouTube features.
- WhatsAppAdapter: Wraps whatsapp_tools automation features.
- SystemAdapter: Wraps system_tools, power_tools, cleaner_tools, and media_tools.
"""
from backend.adapters.youtube_adapter import youtube_adapter
from backend.adapters.whatsapp_adapter import whatsapp_adapter
from backend.adapters.system_adapter import system_adapter

__all__ = ["youtube_adapter", "whatsapp_adapter", "system_adapter"]
