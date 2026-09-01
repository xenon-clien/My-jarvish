"""Integration tests for Master JARVIS Engine end-to-end processing."""
import pytest
from engine.jarvis_engine import JarvisEngine


@pytest.mark.asyncio
async def test_engine_single_command_execution():
    engine = JarvisEngine()

    # Time command
    resp = await engine.process_user_input("time kya hai", speak_output=False)
    assert resp.success is True
    assert "samay" in resp.message.lower() or "am" in resp.message.lower() or "pm" in resp.message.lower()
    assert len(resp.tasks_executed) == 1
    assert resp.tasks_executed[0]["tool"] == "system.time"


@pytest.mark.asyncio
async def test_engine_volume_command():
    engine = JarvisEngine()
    resp = await engine.process_user_input("volume badhao", speak_output=False)
    assert resp.success is True
    assert "volume" in resp.message.lower()
    assert resp.tasks_executed[0]["tool"] == "system.volume_up"


@pytest.mark.asyncio
async def test_engine_hindi_shorts_mapping():
    engine = JarvisEngine()
    resp = await engine.process_user_input("पहला शॉर्ट चलाओ", speak_output=False)
    assert resp.tasks_executed[0]["tool"] == "youtube.play_first_short"


@pytest.mark.asyncio
async def test_engine_emergency_stop():
    engine = JarvisEngine()
    resp = await engine.process_user_input("ruk jao", speak_output=False)
    assert resp.success is True
    assert resp.tasks_executed[0]["tool"] == "system.stop"


@pytest.mark.asyncio
async def test_engine_health_check_command():
    engine = JarvisEngine()
    resp = await engine.process_user_input("health check", speak_output=False)
    assert resp.success is True
    assert "HEALTH CHECK" in resp.message
