"""JARVIS 3.0 - API Endpoints.

REST API routes for interacting with JARVIS 3.0 engine, querying tools,
inspecting health, viewing task traces, listing discovered applications, and triggering emergency stop.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from adapters.download_manager import download_manager
from apps.application_registry import application_registry
from apps.capability_discovery import capability_discovery_engine
from core.bug_finder import bug_finder
from core.health_manager import health_manager
from core.permissions import permission_manager
from core.task_manager import task_manager
from core.task_queue import task_queue
from core.tool_registry import default_registry
from engine.jarvis_engine import EngineResponse, jarvis_engine
from memory.memory_manager import memory_manager

router = APIRouter(prefix="/api", tags=["JARVIS 3.0"])


class ChatRequest(BaseModel):
    message: str = Field(..., description="User voice transcript or typed text command.")
    speak_output: bool = Field(default=False, description="Whether to speak the response aloud.")


class PermissionUpdateRequest(BaseModel):
    key: str
    enabled: bool


@router.post("/chat", response_model=EngineResponse)
async def process_chat(request: ChatRequest):
    """Process user command or query through the full JARVIS 3.0 pipeline."""
    return await jarvis_engine.process_user_input(
        user_text=request.message,
        speak_output=request.speak_output,
    )


@router.post("/voice/listen")
async def listen_from_microphone():
    """Capture speech directly from computer's physical microphone and execute."""
    import asyncio
    from adapters.voice_adapter import voice_adapter

    loop = asyncio.get_event_loop()
    phrase = await loop.run_in_executor(None, lambda: voice_adapter.listen_phrase(timeout=4.5, phrase_time_limit=8.0))

    if not phrase:
        return {
            "success": False,
            "transcript": "",
            "message": "Kuch sunayi nahi diya. Kripya dobara boliye.",
        }

    response = await jarvis_engine.process_user_input(
        user_text=phrase,
        speak_output=True,
    )
    return {
        "success": True,
        "transcript": phrase,
        "response": response.model_dump(),
    }


@router.get("/health")
async def get_system_health():
    """Return real-time health scorecard across all subsystems."""
    return {
        "status": "online",
        "subsystems": {k: v.model_dump() for k, v in health_manager.get_health().items()},
        "formatted_report": health_manager.get_formatted_health_report(),
    }


@router.get("/apps")
async def list_applications(category: Optional[str] = None):
    """List all installed applications discovered on the computer (~93+ apps)."""
    apps = application_registry.list_apps()
    if category:
        apps = [a for a in apps if a.category.value.lower() == category.lower()]
    return {
        "total_apps": len(apps),
        "breakdown": application_registry.get_category_breakdown(),
        "apps": [a.model_dump() for a in apps],
    }


@router.get("/apps/{app_id}/capabilities")
async def get_app_capabilities(app_id: str):
    """Inspect capability manifest and supported tools for an application."""
    manifest = capability_discovery_engine.get_manifest_by_id_or_name(app_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Application '{app_id}' not found.")
    return manifest.model_dump()


@router.post("/apps/rescan")
async def rescan_applications():
    """Re-scan Windows registry and shortcuts for newly installed applications."""
    application_registry.rescan()
    return {
        "status": "success",
        "total_apps": len(application_registry.list_apps()),
        "breakdown": application_registry.get_category_breakdown(),
    }


@router.get("/downloads")
async def get_downloads():
    """Inspect recent and active browser downloads."""
    active = download_manager.get_active_downloads()
    recent = download_manager.list_recent_downloads(limit=15)
    return {
        "active_downloads": [d.model_dump() for d in active],
        "recent_downloads": [d.model_dump() for d in recent],
    }


@router.get("/memory")
async def inspect_memory():
    """Inspect ShortTermMemory, TaskMemory, and Preferences."""
    return {
        "recent_history": memory_manager.short_term.get_recent_history(),
        "last_tool": memory_manager.short_term.last_tool_executed,
        "completed_tasks": memory_manager.task_memory.completed_tasks[-10:],
        "preferences": memory_manager.preferences.preferences,
    }


@router.get("/tools")
async def list_registered_tools():
    """Return all registered tools and their schemas."""
    return {
        "total_tools": len(default_registry.list_tools(only_enabled=False)),
        "categories": default_registry.get_summary_by_category(),
        "schemas": default_registry.get_schemas(),
    }


@router.get("/tasks")
async def list_recent_tasks(limit: int = 20):
    """Return recently created and executed tasks."""
    return [t.model_dump() for t in task_manager.list_tasks(limit=limit)]


@router.post("/stop")
async def emergency_stop():
    """Trigger immediate cancellation of active tasks and release resource locks."""
    return task_queue.cancel_all(reason="API Emergency Stop")


@router.get("/permissions")
async def list_permissions():
    """List all system permission settings."""
    return {"permissions": permission_manager.list_permissions()}


@router.post("/permissions")
async def update_permission(request: PermissionUpdateRequest):
    """Update a specific subsystem permission toggle."""
    ok = permission_manager.set_permission_toggle(request.key, request.enabled)
    return {"status": "success" if ok else "error", "key": request.key, "enabled": request.enabled}


@router.get("/diagnostics/bugs")
async def scan_for_bugs():
    """Run integrity scan to detect broken imports, invalid schemas, and registration bugs."""
    bugs = bug_finder.scan_system_integrity()
    return {"bugs": [b.model_dump() for b in bugs]}


@router.post("/reset")
async def reset_session():
    """Clear conversation history and reset state."""
    jarvis_engine.reset_conversation()
    memory_manager.reset()
    return {"status": "success", "message": "Conversation history and memory reset."}
