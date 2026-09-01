"""Unit tests for Generic Desktop Adapter."""
import pytest
from adapters.generic_desktop_adapter import GenericDesktopAdapter
from core.tool_registry import ToolRegistry


def test_generic_desktop_registration():
    reg = ToolRegistry()
    gd = GenericDesktopAdapter()
    gd.register_tools(reg)

    assert reg.has_tool("desktop.open_app")
    assert reg.has_tool("desktop.close_app")
    assert reg.has_tool("desktop.focus_app")
    assert reg.has_tool("desktop.minimize_app")
    assert reg.has_tool("desktop.maximize_app")
    assert reg.has_tool("desktop.app_status")
    assert reg.has_tool("desktop.list_apps")
    assert reg.has_tool("desktop.app_capabilities")


@pytest.mark.asyncio
async def test_list_discovered_apps_tool():
    gd = GenericDesktopAdapter()
    res = await gd.list_discovered_apps()
    assert res.success is True
    assert "APPLICATION REGISTRY" in res.message or "apps" in res.message.lower()


@pytest.mark.asyncio
async def test_get_app_capabilities_tool():
    gd = GenericDesktopAdapter()
    res = await gd.get_app_capabilities("youtube")
    assert res.success is True
    assert "YouTube" in res.message
    assert "Capabilities" in res.message
