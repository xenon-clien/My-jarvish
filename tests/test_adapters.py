"""Tests for Application Adapters (YouTubeAdapter, WhatsAppAdapter, SystemAdapter)."""
import pytest
from backend.adapters.youtube_adapter import youtube_adapter
from backend.adapters.whatsapp_adapter import whatsapp_adapter
from backend.adapters.system_adapter import system_adapter
from backend.tools.registry import default_registry


@pytest.mark.asyncio
async def test_tool_registry_adapter_dispatch():
    # Test registry dispatch through adapter namespaces
    res_vol = await default_registry.execute("system.volume_up", step=5)
    assert res_vol.success is True
    
    res_yt = await default_registry.execute("youtube.play")
    assert res_yt.success is True
    
    res_stop = await default_registry.execute("system.emergency_stop")
    assert res_stop.success is True


def test_youtube_adapter_methods():
    # Test play, pause, seek, short methods
    assert hasattr(youtube_adapter, "open")
    assert hasattr(youtube_adapter, "play")
    assert hasattr(youtube_adapter, "pause")
    assert hasattr(youtube_adapter, "play_first_short")
    assert hasattr(youtube_adapter, "next_short")
    assert hasattr(youtube_adapter, "prev_short")
    assert hasattr(youtube_adapter, "seek_forward")
    assert hasattr(youtube_adapter, "seek_backward")


def test_whatsapp_adapter_methods():
    assert hasattr(whatsapp_adapter, "send_message")
    assert hasattr(whatsapp_adapter, "voice_call")
    assert hasattr(whatsapp_adapter, "video_call")
    assert hasattr(whatsapp_adapter, "end_call")


def test_system_adapter_methods():
    assert hasattr(system_adapter, "volume_up")
    assert hasattr(system_adapter, "volume_down")
    assert hasattr(system_adapter, "mute_toggle")
    assert hasattr(system_adapter, "clean_junk")
    assert hasattr(system_adapter, "lock_pc")
    assert hasattr(system_adapter, "emergency_stop")
