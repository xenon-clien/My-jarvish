"""Unit tests for YouTube Adapter and 'youtube.play_first_short'."""
import pytest
from adapters.youtube_adapter import YouTubeAdapter, PlayFirstShortTool
from core.tool_registry import ToolRegistry


def test_youtube_adapter_registration():
    reg = ToolRegistry()
    yt = YouTubeAdapter()
    yt.register_tools(reg)

    assert reg.has_tool("youtube.play_first_short")
    assert reg.has_tool("youtube.open")
    assert reg.has_tool("youtube.search")
    assert reg.has_tool("youtube.pause")
    assert reg.has_tool("youtube.resume")
    assert reg.has_tool("youtube.next_video")
    assert reg.has_tool("youtube.next_short")
    assert reg.has_tool("youtube.prev_short")


@pytest.mark.asyncio
async def test_play_first_short_tool_definition():
    yt = YouTubeAdapter()
    tool = PlayFirstShortTool(adapter=yt)

    assert tool.name == "youtube.play_first_short"
    assert tool.dependencies == ["browser"]
    assert tool.retry_policy.max_retries >= 2

    # Check that schema exposes proper contract
    schema = tool.get_schema()
    assert schema["name"] == "youtube.play_first_short"
    assert schema["category"] == "MEDIA"
