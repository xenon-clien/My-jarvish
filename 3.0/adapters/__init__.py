"""JARVIS 3.0 - Application Adapters Package."""
from adapters.base_adapter import BaseAdapter
from adapters.browser_adapter import BrowserAdapter, browser_adapter
from adapters.chrome_adapter import ChromeAdapter, chrome_adapter
from adapters.download_manager import DownloadManager, download_manager
from adapters.youtube_adapter import YouTubeAdapter, youtube_adapter
from adapters.whatsapp_adapter import WhatsAppAdapter, whatsapp_adapter
from adapters.system_adapter import SystemAdapter, system_adapter
from adapters.file_manager_adapter import FileManagerAdapter, file_manager_adapter
from adapters.filesystem_adapter import FilesystemAdapter, filesystem_adapter
from adapters.generic_desktop_adapter import GenericDesktopAdapter, generic_desktop_adapter
from adapters.voice_adapter import VoiceAdapter, voice_adapter


def initialize_all_adapters():
    """Register all tools across all application adapters into the default ToolRegistry."""
    browser_adapter.register_tools()
    chrome_adapter.register_tools()
    youtube_adapter.register_tools()
    whatsapp_adapter.register_tools()
    system_adapter.register_tools()
    file_manager_adapter.register_tools()
    filesystem_adapter.register_tools()
    generic_desktop_adapter.register_tools()
    voice_adapter.register_tools()


__all__ = [
    "BaseAdapter",
    "BrowserAdapter",
    "browser_adapter",
    "ChromeAdapter",
    "chrome_adapter",
    "DownloadManager",
    "download_manager",
    "YouTubeAdapter",
    "youtube_adapter",
    "WhatsAppAdapter",
    "whatsapp_adapter",
    "SystemAdapter",
    "system_adapter",
    "FileManagerAdapter",
    "file_manager_adapter",
    "FilesystemAdapter",
    "filesystem_adapter",
    "GenericDesktopAdapter",
    "generic_desktop_adapter",
    "VoiceAdapter",
    "voice_adapter",
    "initialize_all_adapters",
]
