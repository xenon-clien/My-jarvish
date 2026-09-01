"""Unit & Integration tests for Developer Commands & Slash Commands."""
import pytest
from nlu.deterministic_router import DeterministicRouter
from engine.jarvis_engine import JarvisEngine


def test_slash_commands_routing():
    test_cases = [
        ("/health", "diagnostics.health_check"),
        ("/apps", "desktop.list_apps"),
        ("/capabilities youtube", "desktop.app_capabilities"),
        ("/diagnose", "diagnostics.bugs"),
        ("/stop", "system.stop"),
    ]
    for cmd, expected_tool in test_cases:
        res = DeterministicRouter.route_command(cmd)
        assert res is not None, f"Failed to route '{cmd}'"
        assert res.tool_name == expected_tool, f"Expected {expected_tool} for '{cmd}', got {res.tool_name}"


@pytest.mark.asyncio
async def test_apps_listing_pipeline():
    engine = JarvisEngine()
    resp = await engine.process_user_input("Kaun kaun se apps installed hain?", speak_output=False)
    assert resp.success is True
    assert "APPLICATION REGISTRY" in resp.message or "apps" in resp.message.lower()


@pytest.mark.asyncio
async def test_hidden_files_pipeline():
    engine = JarvisEngine()
    resp = await engine.process_user_input("Hidden files dikhao", speak_output=False)
    assert resp.success is True
    assert "hidden" in resp.message.lower()


@pytest.mark.asyncio
async def test_chrome_tab_pipeline():
    engine = JarvisEngine()
    resp = await engine.process_user_input("Chrome mein new tab kholo", speak_output=False)
    assert resp.success is True
    assert "tab" in resp.message.lower()
