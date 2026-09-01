"""API routes for JARVIS chat, tools, history, and status."""
from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.ai.agent import AgentResponse, JarvisAgent
from backend.database.models import TaskHistoryRecord
from backend.database.repositories import task_history_repo
from backend.tools.registry import default_registry

router = APIRouter(prefix="/api", tags=["JARVIS"])

# Central agent singleton for the API process
agent_instance = JarvisAgent()


class ChatRequest(BaseModel):
    """Payload for user interaction with JARVIS."""
    message: str = Field(..., description="The user's natural language input.")
    confirmation: Optional[bool] = Field(
        None,
        description="Explicit user approval (True/False) if confirming a pending action.",
    )


@router.post("/chat", response_model=AgentResponse)
async def chat(request: ChatRequest):
    """Send a command or conversational turn to JARVIS."""
    response = await agent_instance.process_user_input(
        user_text=request.message,
        confirmation_decision=request.confirmation,
    )
    return response


@router.post("/reset")
async def reset_chat():
    """Reset agent conversation history and pending states."""
    agent_instance.reset_conversation()
    return {"status": "success", "message": "Conversation history reset."}


@router.get("/tools")
async def list_tools():
    """Return all registered tools and their function-calling schemas."""
    return {
        "count": len(default_registry.list_tools()),
        "tools": default_registry.get_schemas(),
    }


@router.get("/history", response_model=List[TaskHistoryRecord])
async def get_history(limit: int = 50):
    """Fetch recent task execution audit history."""
    return task_history_repo.get_recent(limit=limit)


@router.delete("/history")
async def clear_history():
    """Clear all task execution audit history."""
    deleted = task_history_repo.clear_history()
    return {"status": "success", "deleted_count": deleted}


@router.get("/stats")
async def get_stats():
    """Get system command execution statistics."""
    return task_history_repo.get_stats()


@router.get("/status")
async def get_agent_status():
    """Get current agent operational state."""
    from backend.plugins.gesture import gesture_engine
    return {
        "state": agent_instance.state,
        "has_pending_action": agent_instance.pending_action is not None,
        "pending_action": agent_instance.pending_action,
        "history_turns": len(agent_instance.history) // 2,
        "camera_enabled": gesture_engine.camera_enabled,
        "gesture_mode": gesture_engine.last_detection.status_text,
    }


class CameraToggleRequest(BaseModel):
    enabled: bool = Field(..., description="Enable or disable gesture camera detection mode.")


@router.post("/gesture/toggle")
async def toggle_gesture_camera(request: CameraToggleRequest):
    """Toggle gesture control camera ON or OFF."""
    from backend.plugins.gesture import gesture_engine
    res = gesture_engine.enable_camera(request.enabled)
    return {"status": "success", "data": res}


@router.get("/gesture/status")
async def get_gesture_status():
    """Get current gesture detection status."""
    from backend.plugins.gesture import gesture_engine
    return {
        "status": "success",
        "detection": gesture_engine.last_detection.model_dump(),
        "camera_enabled": gesture_engine.camera_enabled,
        "camera_active": gesture_engine.camera_active,
    }


@router.get("/permissions")
async def list_permissions():
    """Get permission center statuses."""
    from backend.core.permissions import permission_center
    return {"permissions": permission_center.get_all_permissions()}


class SetPermissionRequest(BaseModel):
    key: str
    enabled: bool


@router.post("/permissions")
async def update_permission(request: SetPermissionRequest):
    """Update a specific permission status."""
    from backend.core.permissions import permission_center
    ok = permission_center.set_permission(request.key, request.enabled)
    return {"status": "success" if ok else "error", "key": request.key, "enabled": request.enabled}


@router.get("/plugins")
async def list_plugins():
    """List registered plugins."""
    from backend.plugins import plugin_manager
    return {"plugins": plugin_manager.list_plugins()}


@router.post("/emergency-stop")
async def trigger_emergency_stop(reason: Optional[str] = "UI Emergency Stop"):
    """Trigger global emergency stop."""
    from backend.core.emergency_stop import emergency_stop_manager
    res = emergency_stop_manager.trigger_stop(reason)
    agent_instance.reset_conversation()
    return res


@router.get("/memory")
async def get_memory():
    """Get stored user memory."""
    from backend.ai.context_memory import user_memory
    return {"memory": user_memory.get_stored_preferences()}


@router.delete("/memory")
async def clear_user_memory():
    """Clear stored user memory."""
    from backend.ai.context_memory import user_memory
    msg = user_memory.clear_memory()
    return {"status": "success", "message": msg}


class ProblemSolveRequest(BaseModel):
    problem_text: str = Field(..., description="Problem description or copied error text.")
    auto_repair: bool = Field(True, description="Whether to execute low-risk repairs automatically.")
    user_confirmed: bool = Field(False, description="User confirmation for medium/high risk repair.")


@router.post("/diagnostics/health")
async def get_system_health():
    """Run full-system hardware and Windows OS health inspection."""
    from backend.problem_solver.system_health import SystemHealthEngine
    return SystemHealthEngine.get_full_health_report()


@router.post("/diagnostics/solve")
async def solve_pc_problem(request: ProblemSolveRequest):
    """Execute diagnosis, RCA, safe self-repair, and strict verification."""
    from backend.problem_solver.problem_solver_engine import problem_solver_engine
    return problem_solver_engine.solve_problem(
        problem_text=request.problem_text,
        auto_repair=request.auto_repair,
        user_confirmed=request.user_confirmed,
    )


@router.get("/diagnostics/history")
async def get_diagnostic_history(limit: int = 10):
    """Retrieve persistent troubleshooting and repair audit history."""
    from backend.problem_solver.history import RepairHistory
    entries = RepairHistory.get_recent_entries(limit=limit)
    return {"history": [e.model_dump() for e in entries]}


@router.get("/diagnostics/timeline")
async def get_system_timeline(hours: int = 48):
    """Get recent system changes, updates, and crash events timeline."""
    from backend.problem_solver.timeline_engine import SystemTimelineEngine
    return SystemTimelineEngine.get_recent_timeline(hours_back=hours)


# ── JARVIS Self-Diagnostic Bug Finder & Root-Cause Engine Endpoints ──────────
@router.get("/diagnostics/engine/health")
async def get_engine_feature_health():
    """Return live telemetry, health scores (0-100%), and status for every subsystem."""
    from backend.diagnostics.engine import diagnostic_engine
    return {k: v.model_dump() for k, v in diagnostic_engine.get_feature_health().items()}


@router.get("/diagnostics/engine/traces")
async def get_engine_traces(limit: int = 50):
    """Return recent transaction traces with stage timestamps and Correlation IDs."""
    from backend.diagnostics.engine import diagnostic_engine
    return [t.model_dump() for t in diagnostic_engine.get_recent_traces(limit=limit)]


@router.get("/diagnostics/engine/bugs")
async def get_engine_open_bugs():
    """Return open bug records automatically detected across subsystems."""
    from backend.diagnostics.engine import diagnostic_engine
    return [b.model_dump() for b in diagnostic_engine.get_open_bugs()]


@router.get("/diagnostics/engine/why/{correlation_id}")
async def explain_transaction_failure(correlation_id: str):
    """Explain root-cause and evidence for a given failed transaction."""
    from backend.diagnostics.engine import diagnostic_engine
    return {"correlation_id": correlation_id, "explanation": diagnostic_engine.why_did_this_fail(correlation_id)}


@router.get("/diagnostics/engine/export")
async def export_sanitized_diagnostic_report():
    """Export sanitized diagnostic report without secrets or private data."""
    from backend.diagnostics.engine import diagnostic_engine
    return diagnostic_engine.export_diagnostic_report()


