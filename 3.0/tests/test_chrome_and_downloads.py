"""Unit tests for Chrome Adapter and Download Manager."""
import pytest
from adapters.chrome_adapter import ChromeAdapter
from adapters.download_manager import DownloadManager
from core.tool_registry import ToolRegistry


def test_chrome_adapter_registration():
    reg = ToolRegistry()
    chrome = ChromeAdapter()
    chrome.register_tools(reg)

    assert reg.has_tool("chrome.open")
    assert reg.has_tool("chrome.new_tab")
    assert reg.has_tool("chrome.close_tab")
    assert reg.has_tool("chrome.next_tab")
    assert reg.has_tool("chrome.previous_tab")
    assert reg.has_tool("chrome.zoom_in")
    assert reg.has_tool("chrome.zoom_out")
    assert reg.has_tool("chrome.reset_zoom")
    assert reg.has_tool("chrome.open_incognito")
    assert reg.has_tool("chrome.open_downloads")
    assert reg.has_tool("downloads.status")
    assert reg.has_tool("downloads.last_downloaded")


def test_download_manager_scan():
    dm = DownloadManager()
    downloads_dir = dm.get_downloads_directory()
    assert downloads_dir.exists()

    recent = dm.list_recent_downloads(limit=5)
    assert isinstance(recent, list)


@pytest.mark.asyncio
async def test_downloads_status_tool():
    chrome = ChromeAdapter()
    res = await chrome.check_downloads_status()
    assert res.success is True
    assert "download" in res.message.lower() or "file" in res.message.lower()
