"""Unit tests for File Manager Adapter."""
import pytest
from adapters.file_manager_adapter import FileManagerAdapter
from core.tool_registry import ToolRegistry


def test_file_manager_registration():
    reg = ToolRegistry()
    fm = FileManagerAdapter()
    fm.register_tools(reg)

    assert reg.has_tool("files.open")
    assert reg.has_tool("files.search")
    assert reg.has_tool("files.find_by_extension")
    assert reg.has_tool("files.find_large")
    assert reg.has_tool("files.find_recent")
    assert reg.has_tool("files.show_hidden")
    assert reg.has_tool("files.hide_hidden")
    assert reg.has_tool("files.create_folder")
    assert reg.has_tool("files.properties")


@pytest.mark.asyncio
async def test_find_recent_files():
    fm = FileManagerAdapter()
    res = await fm.find_recent_files()
    assert res.success is True
    assert "file" in res.message.lower() or "recent" in res.message.lower() or "modify" in res.message.lower()
