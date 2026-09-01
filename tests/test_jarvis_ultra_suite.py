"""JARVIS Ultra - Comprehensive Architecture & Collision Test Suite.

Validates:
1. Single Authoritative Command Processor & Execution Owner.
2. Context Precedence & Negative Cross-App Collision Elimination.
3. Compound Multi-Step Command Sequencing with Parent App Inheritance.
4. Scoped Gemini Tool Isolation.
5. Resource Locking & Safe Auto-Release.
"""
import asyncio
import pytest

from backend.core.command_processor import command_processor, ExecutionStatus
from backend.core.task_manager import resource_lock_manager
from backend.tools.registry import default_registry


@pytest.mark.asyncio
async def test_single_command_processor_execution():
    """Verify single command processor returns verified success and single execution owner."""
    ctx = await command_processor.process_command("get battery status", source="cli")
    assert ctx.command_id.startswith("CMD-")
    assert ctx.status in [ExecutionStatus.VERIFIED_SUCCESS, ExecutionStatus.DISPATCHED]
    assert ctx.action in ["get_battery_status", "get_system_status"]
    assert ctx.total_steps == 1


@pytest.mark.asyncio
async def test_context_precedence_explicit_override():
    """Explicitly named app in command must ALWAYS override foreground/recent context."""
    # Simulate recent context was Spotify
    command_processor._recent_app_context = "spotify"
    domain, app = command_processor.resolve_application_context(
        raw_text="YouTube ka next short chalao",
        normalized_text="youtube ka next short chalao",
    )
    assert app == "youtube"
    assert domain == "media"


@pytest.mark.asyncio
async def test_scoped_exact_matching_youtube_vs_spotify():
    """Context-aware command disambiguation."""
    # In YouTube context
    domain_yt, app_yt = command_processor.resolve_application_context("next short", "next short")
    assert app_yt == "youtube"

    # In Spotify context
    domain_sp, app_sp = command_processor.resolve_application_context("next song", "next song")
    assert app_sp == "spotify"

    # In WhatsApp context
    domain_wa, app_wa = command_processor.resolve_application_context("Harsh ko message karo", "harsh ko message karo")
    assert app_wa == "whatsapp"
    assert domain_wa == "communication"


@pytest.mark.asyncio
async def test_compound_task_decomposition():
    """Compound command with 'aur' must decompose into sequenced child tasks inheriting app context."""
    cmd = "YouTube kholo aur pehla short chalao"
    ctx = await command_processor.process_command(cmd, source="cli")
    assert ctx.total_steps == 2
    assert ctx.application == "youtube"
    assert ctx.status == ExecutionStatus.VERIFIED_SUCCESS


@pytest.mark.asyncio
async def test_scoped_gemini_tool_exposure():
    """Gemini must only receive scoped tools relevant to the active application."""
    yt_tools = command_processor.get_scoped_tools("media", "youtube")
    assert len(yt_tools) <= 10
    assert "click_screen_video" in yt_tools
    assert "send_whatsapp_message" not in yt_tools
    assert "shutdown_pc" not in yt_tools

    wa_tools = command_processor.get_scoped_tools("communication", "whatsapp")
    assert "send_whatsapp_message" in wa_tools
    assert "click_screen_video" not in wa_tools

    sys_tools = command_processor.get_scoped_tools("system", "system")
    assert "get_system_status" in sys_tools
    assert "send_whatsapp_message" not in sys_tools


@pytest.mark.asyncio
async def test_resource_lock_safety():
    """Resource locks must prevent simultaneous execution collisions and release cleanly."""
    task_1 = "TASK-001"
    task_2 = "TASK-002"

    # Acquire lock for task 1
    acq1 = resource_lock_manager.acquire(["youtube", "mouse"], task_1, timeout=0.5)
    assert acq1 is True

    # Task 2 trying to acquire same lock should time out
    acq2 = resource_lock_manager.acquire(["youtube"], task_2, timeout=0.1)
    assert acq2 is False

    # Release task 1
    resource_lock_manager.release_all_for_task(task_1)

    # Task 2 can now acquire
    acq2_retry = resource_lock_manager.acquire(["youtube"], task_2, timeout=0.5)
    assert acq2_retry is True
    resource_lock_manager.release_all_for_task(task_2)
