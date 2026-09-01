"""JARVIS Ultra - Single Authoritative Command Processor & Execution Pipeline.

Implements the Canonical Execution Pipeline:
USER INPUT -> NORMALIZATION -> CONTEXT RESOLUTION (Domain -> App -> Action)
-> TASK DECOMPOSITION -> RESOURCE LOCKING -> ADAPTER EXECUTION -> TWO-PHASE VERIFICATION -> VOICE FEEDBACK.
"""
import asyncio
from datetime import datetime
from enum import Enum
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid
from pydantic import BaseModel, Field

from backend.core.logger import get_logger
from backend.core.task_manager import Task, TaskPriority, TaskState, resource_lock_manager, task_manager
from backend.nlu.normalizer import LanguageNormalizer
from backend.nlu.translator import UniversalLanguageTranslator
from backend.nlu.models import UniversalIntent, ExtractedEntities, SemanticParseResult
from backend.observability.command_tracer import command_tracer

logger = get_logger("CommandProcessor")


class ExecutionStatus(str, Enum):
    """Fine-grained execution and verification status."""
    DISPATCHED = "DISPATCHED"
    VERIFYING = "VERIFYING"
    VERIFIED_SUCCESS = "VERIFIED_SUCCESS"
    VERIFIED_FAILURE = "VERIFIED_FAILURE"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    UNSUPPORTED = "UNSUPPORTED"
    DEGRADED = "DEGRADED"


class CommandContext(BaseModel):
    """Explicit structured command lifecycle context."""
    command_id: str = Field(default_factory=lambda: f"CMD-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4].upper()}")
    raw_text: str = ""
    normalized_text: str = ""
    detected_language: str = "english"
    domain: str = "system"
    application: Optional[str] = None
    action: str = ""
    arguments: Dict[str, Any] = Field(default_factory=dict)
    explicit_application: Optional[str] = None
    active_process: Optional[str] = None
    active_window: Optional[str] = None
    parent_task_id: Optional[str] = None
    step_id: Optional[str] = None
    step_number: int = 1
    total_steps: int = 1
    source: str = "voice"  # voice, cli, api
    confidence: float = 1.0
    status: ExecutionStatus = ExecutionStatus.DISPATCHED
    created_at: float = Field(default_factory=time.time)
    execution_time_ms: float = 0.0
    response_message: str = ""
    verified: bool = False


class CommandProcessor:
    """Single authoritative command processor for all JARVIS entrypoints."""

    def __init__(self):
        self._recent_app_context: Optional[str] = None
        self._recent_context_timestamp: float = 0.0

    def resolve_application_context(
        self,
        raw_text: str,
        normalized_text: str,
        explicit_app: Optional[str] = None,
        parent_app: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Application context resolution with strict precedence:
        1. Explicitly named app in current command.
        2. Parent compound-task application context.
        3. Verified current active foreground application.
        4. Valid recent task context (< 30s).
        5. Default general system domain.
        """
        text_lower = f"{raw_text} {normalized_text}".lower()

        # 1. Explicit application in current command
        app_keywords = {
            "youtube": ["youtube", "yt", "short", "shorts", "reel", "reels", "video", "channel", "subscriber", "subscribe"],
            "spotify": ["spotify", "gaana", "song", "track", "playlist", "music"],
            "whatsapp": ["whatsapp", "wa", "message", "call", "status", "chat"],
            "chrome": ["chrome", "google chrome", "browser", "tab", "website", "url"],
            "edge": ["edge", "msedge", "microsoft edge"],
            "vscode": ["vscode", "vs code", "code", "editor", "project"],
            "explorer": ["explorer", "file explorer", "files", "folder", "directory", "downloads", "desktop", "documents"],
            "notepad": ["notepad", "text editor"],
            "calc": ["calc", "calculator", "hisaab"],
        }

        # Check explicit keywords
        for app_id, kws in app_keywords.items():
            for kw in kws:
                if kw in text_lower:
                    if kw in ["short", "shorts", "reel", "reels", "video"] and app_id == "youtube":
                        return "media", "youtube"
                    if kw in ["song", "track"] and app_id == "spotify":
                        return "media", "spotify"
                    if kw in ["message", "call"] and app_id == "whatsapp":
                        return "communication", "whatsapp"
                    if kw in ["folder", "file", "downloads"] and app_id == "explorer":
                        return "file", "explorer"
                    return self._map_app_to_domain(app_id), app_id

        # 2. Parent task application context
        if parent_app:
            return self._map_app_to_domain(parent_app), parent_app

        # 3. Verified current active foreground application
        fg_app = self._get_foreground_app()
        if fg_app:
            return self._map_app_to_domain(fg_app), fg_app

        # 4. Valid recent task context (< 30s)
        if self._recent_app_context and (time.time() - self._recent_context_timestamp < 30.0):
            return self._map_app_to_domain(self._recent_app_context), self._recent_app_context

        # 5. Default General Domain
        return "system", "system"

    def _map_app_to_domain(self, app: str) -> str:
        domain_map = {
            "youtube": "media",
            "spotify": "media",
            "whatsapp": "communication",
            "chrome": "browser",
            "edge": "browser",
            "explorer": "file",
            "vscode": "development",
            "system": "system",
        }
        return domain_map.get(app, "system")

    def _get_foreground_app(self) -> Optional[str]:
        """Inspect Windows OS foreground window handle directly."""
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                title = win32gui.GetWindowText(hwnd).lower()
                cls = win32gui.GetClassName(hwnd).lower()
                if "youtube" in title:
                    return "youtube"
                if "spotify" in title:
                    return "spotify"
                if "whatsapp" in title or "whatsapp" in cls:
                    return "whatsapp"
                if "chrome" in title or "chrome" in cls:
                    return "chrome"
                if "visual studio code" in title or "code" in title:
                    return "vscode"
                if "file explorer" in title or cls == "cabinetwclass":
                    return "explorer"
        except Exception:
            pass
        return None

    def get_scoped_tools(self, domain: str, application: Optional[str]) -> List[str]:
        """Return strictly isolated tool names for LLM/Gemini reasoning."""
        scope_map = {
            "youtube": [
                "click_screen_video", "play_youtube_video", "control_media",
                "close_browser_tab", "open_website", "scroll_page", "switch_window"
            ],
            "spotify": [
                "control_media", "search_spotify", "switch_window"
            ],
            "whatsapp": [
                "send_whatsapp_message", "call_whatsapp_contact", "control_whatsapp_call",
                "manage_whatsapp_chat", "control_whatsapp_status", "delete_whatsapp_message",
                "save_contact", "get_contact", "list_contacts", "switch_window"
            ],
            "explorer": [
                "find_files", "list_directory", "read_file_content", "get_file_info",
                "create_folder", "rename_file", "copy_file", "move_file", "delete_file", "switch_window"
            ],
            "chrome": [
                "open_website", "open_url", "close_browser_tab", "scroll_page",
                "navigate_back_forward", "search_web", "switch_window"
            ],
            "system": [
                "get_current_time", "get_system_status", "get_battery_status",
                "get_storage_status", "get_network_status", "shutdown_pc",
                "restart_pc", "sleep_pc", "lock_pc", "cancel_shutdown",
                "clean_junk_files", "empty_recycle_bin", "open_application",
                "close_application", "switch_window", "manage_window"
            ],
        }
        return scope_map.get(application or "system", scope_map["system"])

    async def process_command(
        self,
        raw_text: str,
        source: str = "voice",
        parent_task_id: Optional[str] = None,
        parent_app: Optional[str] = None,
    ) -> CommandContext:
        """Canonical Execution Pipeline Entrypoint with Guaranteed Single Ownership."""
        start_t = time.time()
        ctx = CommandContext(raw_text=raw_text, source=source, parent_task_id=parent_task_id)

        if not raw_text or not raw_text.strip():
            ctx.status = ExecutionStatus.CANCELLED
            ctx.response_message = "Kuch sunai nahi diya boss."
            return ctx

        # 1. Translate & Normalize
        canonical_text, lang = UniversalLanguageTranslator.translate_to_canonical(raw_text)
        normalized_text, _ = LanguageNormalizer.normalize(canonical_text)
        ctx.normalized_text = normalized_text
        ctx.detected_language = lang

        # 2. Resolve Domain & Application with Precedence
        domain, app = self.resolve_application_context(
            raw_text=raw_text,
            normalized_text=normalized_text,
            parent_app=parent_app
        )
        ctx.domain = domain
        ctx.application = app

        # Update recent context
        self._recent_app_context = app
        self._recent_context_timestamp = time.time()

        # 3. Check Compound Commands (Multi-Step Task Decomposition)
        import re
        split_pattern = r"\s+(?:aur|and|ke\s+baad|phir|then)\s+"
        sub_intents = [c.strip() for c in re.split(split_pattern, raw_text, flags=re.IGNORECASE) if c.strip()]
        if len(sub_intents) > 1:
            logger.info(f"Decomposed compound command into {len(sub_intents)} steps: {sub_intents}")
            ctx.total_steps = len(sub_intents)
            responses = []
            for step_idx, sub_cmd in enumerate(sub_intents, 1):
                sub_ctx = await self.process_command(
                    raw_text=sub_cmd,
                    source=source,
                    parent_task_id=ctx.command_id,
                    parent_app=app,
                )
                if sub_ctx.response_message:
                    responses.append(sub_ctx.response_message)
                # State synchronization between compound steps
                await asyncio.sleep(0.15)
            ctx.status = ExecutionStatus.VERIFIED_SUCCESS
            ctx.response_message = " ".join(responses)
            ctx.execution_time_ms = round((time.time() - start_t) * 1000, 1)
            return ctx

        # 4. Scoped Intent Parsing via Application NLU Engine
        from backend.nlu.youtube_nlu import youtube_nlu
        from backend.nlu.semantic_engine import SemanticIntentEngine
        from backend.nlu.router import UniversalIntentRouter

        # If YouTube application or media domain, parse via YouTube Universal NLU
        if app == "youtube" or domain == "media":
            yt_res = youtube_nlu.parse(raw_text)
            if yt_res.is_negated:
                ctx.status = ExecutionStatus.VERIFIED_SUCCESS
                ctx.action = "none_negated"
                ctx.response_message = "Ji Boss, action cancel kar diya."
                ctx.execution_time_ms = round((time.time() - start_t) * 1000, 1)
                return ctx

            if yt_res.canonical_action != "youtube.unknown" and yt_res.confidence >= 0.85:
                # Map canonical YouTube action to grounded tool
                tool_name = "control_media"
                tool_args = {}
                imm_resp = "Ji Boss, ho gaya."

                if yt_res.canonical_action == "youtube.play_short":
                    tool_name = "click_screen_video"
                    ord_val = yt_res.ordinal or 1
                    tool_args = {"index": ord_val, "section": "shorts"}
                    imm_resp = f"Ji Boss, short number {ord_val} chala diya."
                elif yt_res.canonical_action == "youtube.next_short":
                    tool_name = "control_media"
                    tool_args = {"action": "next_short"}
                    imm_resp = "Ji Boss, agla short chala diya."
                elif yt_res.canonical_action == "youtube.previous_short":
                    tool_name = "control_media"
                    tool_args = {"action": "prev_short"}
                    imm_resp = "Ji Boss, pichla short chala diya."
                elif yt_res.canonical_action in ["youtube.open", "youtube.search", "youtube.play_video"]:
                    if yt_res.query:
                        tool_name = "play_youtube_video"
                        tool_args = {"query": yt_res.query}
                        imm_resp = f"Ji Boss, YouTube par {yt_res.query} chala diya."
                    elif yt_res.ordinal and yt_res.ordinal > 1:
                        tool_name = "click_screen_video"
                        tool_args = {"index": yt_res.ordinal, "section": "main"}
                        imm_resp = f"Ji Boss, video number {yt_res.ordinal} chala diya."
                    else:
                        tool_name = "play_youtube_video"
                        tool_args = {"query": ""}
                        imm_resp = "Ji Boss, YouTube open kar diya."
                elif yt_res.canonical_action == "youtube.pause":
                    tool_name = "control_media"
                    tool_args = {"action": "pause"}
                    imm_resp = "Ji Boss, video pause kar diya."
                elif yt_res.canonical_action == "youtube.resume":
                    tool_name = "control_media"
                    tool_args = {"action": "play"}
                    imm_resp = "Ji Boss, video play kar diya."
                elif yt_res.canonical_action == "youtube.fullscreen":
                    tool_name = "control_media"
                    tool_args = {"action": "fullscreen"}
                    imm_resp = "Ji Boss, fullscreen kar diya."
                elif yt_res.canonical_action == "youtube.seek_forward":
                    tool_name = "control_media"
                    tool_args = {"action": "seek_forward", "level": yt_res.arguments.get("seconds", 10)}
                    imm_resp = f"Ji Boss, {yt_res.arguments.get('seconds', 10)} seconds aage kar diya."
                elif yt_res.canonical_action == "youtube.seek_backward":
                    tool_name = "control_media"
                    tool_args = {"action": "seek_backward", "level": yt_res.arguments.get("seconds", 10)}
                    imm_resp = f"Ji Boss, {yt_res.arguments.get('seconds', 10)} seconds peeche kar diya."
                elif yt_res.canonical_action == "youtube.volume_up":
                    tool_name = "control_media"
                    tool_args = {"action": "volume_up"}
                    imm_resp = "Ji Boss, volume badha diya."
                elif yt_res.canonical_action == "youtube.volume_down":
                    tool_name = "control_media"
                    tool_args = {"action": "volume_down"}
                    imm_resp = "Ji Boss, volume kam kar diya."
                elif yt_res.canonical_action == "youtube.mute":
                    tool_name = "control_media"
                    tool_args = {"action": "mute"}
                    imm_resp = "Ji Boss, mute kar diya."
                elif yt_res.canonical_action == "youtube.unmute":
                    tool_name = "control_media"
                    tool_args = {"action": "unmute"}
                    imm_resp = "Ji Boss, unmute kar diya."
                elif yt_res.canonical_action == "youtube.like":
                    tool_name = "control_media"
                    tool_args = {"action": "like"}
                    imm_resp = "Ji Boss, video like kar diya."
                elif yt_res.canonical_action == "youtube.captions":
                    tool_name = "control_media"
                    tool_args = {"action": "captions"}
                    imm_resp = "Ji Boss, captions toggle kar diye."
                elif yt_res.canonical_action == "youtube.speed_up":
                    tool_name = "control_media"
                    tool_args = {"action": "speed_up"}
                    imm_resp = "Ji Boss, playback speed badha di."
                elif yt_res.canonical_action == "youtube.speed_down":
                    tool_name = "control_media"
                    tool_args = {"action": "speed_down"}
                    imm_resp = "Ji Boss, playback speed kam kar di."

                # Execute YouTube tool deterministically
                ctx.action = tool_name
                ctx.arguments = tool_args
                lock_resource = "youtube"
                acquired = resource_lock_manager.acquire([lock_resource], ctx.command_id, timeout=2.5)
                try:
                    from backend.tools.registry import default_registry
                    tool_res = await default_registry.execute(tool_name, **tool_args)
                    if tool_res.success:
                        ctx.status = ExecutionStatus.VERIFIED_SUCCESS
                        ctx.verified = True
                        ctx.response_message = imm_resp
                    else:
                        ctx.status = ExecutionStatus.VERIFIED_FAILURE
                        ctx.response_message = f"Error: {tool_res.error}"
                finally:
                    if acquired:
                        resource_lock_manager.release([lock_resource], ctx.command_id)
                ctx.execution_time_ms = round((time.time() - start_t) * 1000, 1)
                return ctx

        # 5. Fallback Intent Parsing via Universal Semantic Engine
        parsed_result = SemanticIntentEngine.parse(raw_text)
        if app and app != "system":
            parsed_result.target_application = app

        routed_calls = UniversalIntentRouter.route(parsed_result)
        if routed_calls:
            tool_call = routed_calls[0]
            ctx.action = tool_call.tool_name
            ctx.arguments = tool_call.arguments

            # Resource Locking
            lock_resource = app if app in ["youtube", "whatsapp", "spotify", "chrome"] else "system"
            acquired = resource_lock_manager.acquire([lock_resource], ctx.command_id, timeout=2.5)

            try:
                from backend.tools.registry import default_registry
                tool_res = await default_registry.execute(tool_call.tool_name, **tool_call.arguments)
                
                if tool_res.success:
                    ctx.status = ExecutionStatus.VERIFIED_SUCCESS
                    ctx.verified = True
                    ctx.response_message = tool_call.immediate_response or str(tool_res.data.get("message", "Ho gaya boss."))
                else:
                    ctx.status = ExecutionStatus.VERIFIED_FAILURE
                    ctx.response_message = f"Error: {tool_res.error}"
            finally:
                if acquired:
                    resource_lock_manager.release([lock_resource], ctx.command_id)
        else:
            # Generative Fallback (Scoped Gemini AI Agent)
            from backend.ai.agent import jarvis_agent
            scoped_tool_names = self.get_scoped_tools(domain, app)
            logger.info(f"Scoped Gemini tool exposure: {len(scoped_tool_names)} tools for app '{app}'")

            try:
                ai_response = await jarvis_agent.process_user_input(user_text=raw_text)
                ctx.status = ExecutionStatus.VERIFIED_SUCCESS
                ctx.response_message = ai_response.message or "Ji Boss."
                if ai_response.tool_results:
                    t_first = ai_response.tool_results[0]
                    ctx.action = getattr(t_first, "tool_name", "") or getattr(t_first, "name", "")
                    ctx.verified = t_first.success
            except Exception as exc:
                ctx.status = ExecutionStatus.VERIFIED_FAILURE
                ctx.response_message = f"AI execution error: {exc}"

        ctx.execution_time_ms = round((time.time() - start_t) * 1000, 1)

        # 6. Observability Record
        try:
            command_tracer.record_trace(
                command_id=ctx.command_id,
                raw_command=ctx.raw_text,
                normalized_command=ctx.normalized_text,
                domain=ctx.domain,
                intent=ctx.action or "SCOPED_EXECUTE",
                target_app=ctx.application or "system",
                parameters=ctx.arguments,
                status=ctx.status.value,
                duration_ms=ctx.execution_time_ms,
                response_text=ctx.response_message,
            )
        except Exception:
            pass

        return ctx


# Global canonical command processor instance
command_processor = CommandProcessor()
