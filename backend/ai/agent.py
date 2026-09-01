"""JarvisAgent - Core orchestrator for conversation turns, permissions, and tool execution."""
from enum import Enum
import json
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.ai.action_planner import action_planner
from backend.ai.context_memory import context_memory
from backend.ai.intent_engine import fast_intent_engine
from backend.ai.prompts import get_system_prompt
from backend.ai.providers import AIProvider, BaseAIResponse, ToolCall, get_ai_provider
from backend.ai.state_observer import state_observer
from backend.ai.verification_engine import verification_engine
from backend.core.config import Settings, get_settings
from backend.core.logger import get_logger
from backend.core.observability import observability, ObservabilityTrace
from backend.core.permissions import PermissionLevel, ToolPermissionPolicy
from backend.database.repositories import TaskHistoryRepository, task_history_repo
from backend.tools.registry import ToolRegistry, ToolResult, default_registry

logger = get_logger("JarvisAgent")


class AgentState(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    EXECUTING = "EXECUTING"
    SPEAKING = "SPEAKING"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    ERROR = "ERROR"


class PendingAction(BaseModel):
    """Holds a tool call that is paused waiting for user confirmation."""
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    permission_level: PermissionLevel
    confirmation_prompt: str
    original_command: str = ""


class AgentResponse(BaseModel):
    """Structured response from a single turn with JARVIS."""
    message: str
    state: AgentState
    tool_results: List[ToolResult] = Field(default_factory=list)
    pending_action: Optional[PendingAction] = None


class JarvisAgent:
    """The central intelligence coordinator for JARVIS."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        provider: Optional[AIProvider] = None,
        registry: Optional[ToolRegistry] = None,
        permission_policy: Optional[ToolPermissionPolicy] = None,
        history_repo: Optional[TaskHistoryRepository] = None,
    ):
        self.settings = settings or get_settings()
        self.provider = provider or get_ai_provider()
        self.registry = registry or default_registry
        self.permission_policy = permission_policy or ToolPermissionPolicy(self.settings)
        self.history_repo = history_repo or task_history_repo
        self.history: List[Dict[str, str]] = []
        self.pending_action: Optional[PendingAction] = None
        self.state: AgentState = AgentState.IDLE

    def reset_conversation(self) -> None:
        """Clear conversation history and reset state."""
        self.history.clear()
        self.pending_action = None
        self.state = AgentState.IDLE

    async def process_user_input(
        self,
        user_text: str,
        confirmation_decision: Optional[bool] = None,
    ) -> AgentResponse:
        """Process a single turn of user input with complete diagnostic transaction tracing."""
        start_turn_time = time.time()
        from backend.diagnostics.engine import diagnostic_engine
        from backend.diagnostics.models import DiagnosticEvent, ErrorCode

        cid = diagnostic_engine.start_transaction(user_text)

        # Check if we were waiting for user confirmation on a pending action
        if self.pending_action is not None:
            resp = await self._handle_confirmation(user_text, confirmation_decision)
            diagnostic_engine.end_transaction(cid, success=(resp.state != AgentState.ERROR), final_response=resp.message)
            return resp

        # -------------------------------------------------------------
        # 1. UNIVERSAL HUMAN-LANGUAGE UNDERSTANDING ENGINE (NLU - PRIMARY BRAIN)
        # -------------------------------------------------------------
        from backend.nlu import SemanticIntentEngine, UniversalIntentRouter, NluDebugLogger, NluDebugTrace, UniversalIntent
        nlu_result = SemanticIntentEngine.parse(user_text)

        diagnostic_engine.record_event(DiagnosticEvent(
            eventId=f"EVT-{time.time():.3f}-NLU",
            correlationId=cid,
            category="NLU",
            operation=nlu_result.primary_intent.value,
            stage="INTENT",
            status="SUCCESS" if nlu_result.confidence >= 0.70 else "UNVERIFIED",
            confidence=nlu_result.confidence,
            message=f"Detected intent '{nlu_result.primary_intent.value}' (Lang: {nlu_result.detected_language})",
            metadata={"entities": nlu_result.entities.model_dump(exclude_none=True)},
        ))

        if nlu_result.requires_clarification and nlu_result.clarification_prompt:
            logger.info(f"NLU Intent requested clarification: '{nlu_result.clarification_prompt}'")
            NluDebugLogger.log_trace(NluDebugTrace(
                raw_transcript=user_text,
                normalized_transcript=nlu_result.normalized_transcript,
                detected_language=nlu_result.detected_language,
                intent=nlu_result.primary_intent.value,
                confidence=nlu_result.confidence,
                entities=nlu_result.entities.model_dump(exclude_none=True),
                target_application=nlu_result.target_application,
                selected_tool=None,
                tool_arguments={},
                error_or_clarification=nlu_result.clarification_prompt,
            ))
            self.history.append({"role": "user", "content": user_text})
            self.history.append({"role": "assistant", "content": nlu_result.clarification_prompt})
            self.state = AgentState.SPEAKING
            diagnostic_engine.end_transaction(cid, success=True, final_response=nlu_result.clarification_prompt)
            return AgentResponse(message=nlu_result.clarification_prompt, state=AgentState.SPEAKING)

        routed_calls = UniversalIntentRouter.route(nlu_result)
        if routed_calls and nlu_result.confidence >= 0.70:
            logger.info(f"NLU Universal Intent routed: {nlu_result.primary_intent.value} -> {[c.tool_name for c in routed_calls]}")
            self.history.append({"role": "user", "content": user_text})

            tool_calls = [
                ToolCall(name=c.tool_name, arguments=c.arguments)
                for c in routed_calls
            ]
            primary_response = routed_calls[0].immediate_response

            diagnostic_engine.record_event(DiagnosticEvent(
                eventId=f"EVT-{time.time():.3f}-ROUTER",
                correlationId=cid,
                category=nlu_result.target_application.upper() if nlu_result.target_application else "ROUTING",
                operation=routed_calls[0].tool_name,
                stage="ROUTING",
                status="SUCCESS",
                message=f"Routed to tool '{routed_calls[0].tool_name}' with args {routed_calls[0].arguments}",
            ))

            resp = await self._process_tool_calls(
                tool_calls,
                user_text,
                primary_response,
                correlation_id=cid,
                target_subsystem=nlu_result.target_application,
            )
            diagnostic_engine.end_transaction(
                cid,
                success=(resp.state != AgentState.ERROR),
                final_response=resp.message,
                target_subsystem=nlu_result.target_application,
            )
            return resp

        # -------------------------------------------------------------
        # 2. COGNITIVE ACTION PLANNER (Multi-step Fallback)
        # -------------------------------------------------------------
        plan = action_planner.create_plan(user_text)
        if plan:
            logger.info(f"Action plan resolved: intent='{plan.intent.value}', target='{plan.target_entity}'")
            self.history.append({"role": "user", "content": user_text})

            if plan.is_direct_chat and plan.direct_chat_response:
                bot_text = plan.direct_chat_response
                self.history.append({"role": "assistant", "content": bot_text})
                self.state = AgentState.SPEAKING
                self.history_repo.add_record(
                    command=user_text,
                    action=plan.intent.value,
                    status="SUCCESS",
                    result=bot_text,
                    execution_time_ms=round((time.time() - start_turn_time) * 1000, 2),
                )
                return AgentResponse(
                    message=bot_text,
                    state=AgentState.SPEAKING,
                )

            if plan.steps:
                tool_calls = [step.tool_call for step in plan.steps]
                return await self._process_tool_calls(
                    tool_calls,
                    user_text,
                    plan.immediate_response,
                )

        # -------------------------------------------------------------
        # 3. FAST LOCAL INTENT ENGINE (Zero Latency Execution)
        # -------------------------------------------------------------
        fast_match = fast_intent_engine.match(user_text)
        if fast_match:
            logger.info(f"Fast local intent matched: '{fast_match.intent_name}'")
            self.history.append({"role": "user", "content": user_text})

            if fast_match.is_direct_chat and fast_match.direct_chat_response:
                bot_text = fast_match.direct_chat_response
                self.history.append({"role": "assistant", "content": bot_text})
                self.state = AgentState.SPEAKING
                self.history_repo.add_record(
                    command=user_text,
                    action=fast_match.intent_name,
                    status="SUCCESS",
                    result=bot_text,
                    execution_time_ms=round((time.time() - start_turn_time) * 1000, 2),
                )
                return AgentResponse(
                    message=bot_text,
                    state=AgentState.SPEAKING,
                )

            if fast_match.tool_calls:
                return await self._process_tool_calls(
                    fast_match.tool_calls,
                    user_text,
                    fast_match.immediate_response,
                )

        # Update state to THINKING
        self.state = AgentState.THINKING
        logger.info(f"Processing command with AI Brain: '{user_text}'")

        # Build message history for the AI provider
        messages = [
            {"role": "system", "content": get_system_prompt(self.settings.USER_NAME)},
            *self.history,
            {"role": "user", "content": user_text},
        ]

        # Call AI provider with scoped tools
        from backend.core.command_processor import command_processor
        domain, app = command_processor.resolve_application_context(user_text, user_text)
        scoped_tool_names = command_processor.get_scoped_tools(domain, app)
        tools_schemas = self.registry.get_openai_tool_schemas(scoped_tool_names)
        logger.info(f"Scoped Gemini tool schemas provided: {len(tools_schemas)} tools for app '{app}'")

        try:
            ai_response: BaseAIResponse = await self.provider.generate_response(
                messages=messages,
                tools_schema=tools_schemas,
            )
        except Exception as exc:
            logger.warning(f"AI Provider error ({exc}). Falling back to local offline provider.")
            try:
                from backend.ai.providers import MockProvider
                mock_p = MockProvider(self.settings)
                ai_response = await mock_p.generate_response(messages, tools_schemas)
            except Exception:
                self.state = AgentState.ERROR
                error_msg = "Boss, cloud AI service temporarily unavailable hai. Lekin local automation tools chal rahe hain."
                self.history_repo.add_record(
                    command=user_text,
                    action=None,
                    status="FAILED",
                    result=error_msg,
                    execution_time_ms=round((time.time() - start_turn_time) * 1000, 2),
                )
                return AgentResponse(message=error_msg, state=AgentState.ERROR)

        # Append user message to history
        self.history.append({"role": "user", "content": user_text})

        # If no tool calls requested, return direct conversational response
        if not ai_response.tool_calls:
            bot_text = ai_response.content or "Ji Boss! Main aapki madad ke liye tayar hu."
            self.history.append({"role": "assistant", "content": bot_text})
            self.state = AgentState.SPEAKING
            self.history_repo.add_record(
                command=user_text,
                action=None,
                status="SUCCESS",
                result=bot_text,
                execution_time_ms=round((time.time() - start_turn_time) * 1000, 2),
            )
            return AgentResponse(
                message=bot_text,
                state=AgentState.SPEAKING,
            )

        # Process tool calls
        return await self._process_tool_calls(ai_response.tool_calls, user_text, ai_response.content)

    async def _process_tool_calls(
        self,
        tool_calls: List[ToolCall],
        original_command: str = "",
        intro_content: Optional[str] = None,
        correlation_id: Optional[str] = None,
        target_subsystem: Optional[str] = None,
    ) -> AgentResponse:
        """Execute validated tool calls, perform closed-loop verification, and emit diagnostic telemetry."""
        from backend.diagnostics.engine import diagnostic_engine
        from backend.diagnostics.models import DiagnosticEvent, ErrorCode

        cid = correlation_id or diagnostic_engine.create_correlation_id()

        # Check permissions for each tool call
        from backend.core.permissions import PermissionLevel
        for tool_call in tool_calls:
            tool_obj = self.registry.get(tool_call.name)
            perm_level = tool_obj.permission_level if tool_obj else PermissionLevel.LEVEL_1_NORMAL
            perm_check = self.permission_policy.evaluate(
                tool_name=tool_call.name,
                level=perm_level,
                arguments_summary=str(tool_call.arguments),
            )

            if not perm_check.allowed:
                msg = f"Action denied by security policy: {perm_check.reason}"
                self.state = AgentState.ERROR
                return AgentResponse(message=msg, state=AgentState.ERROR)

            if perm_check.requires_confirmation:
                logger.info(f"Tool '{tool_call.name}' requires user confirmation")
                self.pending_action = PendingAction(
                    tool_name=tool_call.name,
                    arguments=tool_call.arguments,
                    permission_level=perm_level,
                    confirmation_prompt=perm_check.confirmation_message or f"Confirm '{tool_call.name}'?",
                    original_command=original_command,
                )
                self.state = AgentState.AWAITING_CONFIRMATION
                self.history.append({"role": "user", "content": original_command})
                self.history.append({
                    "role": "assistant",
                    "content": self.pending_action.confirmation_prompt,
                })
                self.history_repo.add_record(
                    command=original_command,
                    action=tool_call.name,
                    status="AWAITING_CONFIRMATION",
                    result=self.pending_action.confirmation_prompt,
                )
                return AgentResponse(
                    message=self.pending_action.confirmation_prompt,
                    state=AgentState.AWAITING_CONFIRMATION,
                    pending_action=self.pending_action,
                )

        # All tools are approved: execute them
        self.state = AgentState.EXECUTING
        results: List[ToolResult] = []
        executed_names = []
        pre_state = state_observer.capture_current_state()

        for tool_call in tool_calls:
            logger.info(f"Executing tool '{tool_call.name}' with args {tool_call.arguments}")
            t_res = await self.registry.execute(tool_call.name, **tool_call.arguments)
            results.append(t_res)
            executed_names.append(tool_call.name)

            # 1. Closed-Loop Action Verification
            target_str = str(
                tool_call.arguments.get("target")
                or tool_call.arguments.get("target_app")
                or tool_call.arguments.get("query")
                or tool_call.arguments.get("direction")
                or ""
            )
            ver_res = verification_engine.verify_action(
                action_name=tool_call.name,
                target=target_str,
                pre_state=pre_state,
                tool_result_data=t_res.data if isinstance(t_res.data, dict) else None,
            )

            # 2. Emit Diagnostic Engine Event
            cat_name = (target_subsystem or "SYSTEM").upper()
            diagnostic_engine.record_event(DiagnosticEvent(
                eventId=f"EVT-{time.time():.3f}-EXEC",
                correlationId=cid,
                category=cat_name,
                operation=tool_call.name,
                stage="EXECUTE",
                status="SUCCESS" if t_res.success else "FAILED",
                durationMs=t_res.execution_time_ms,
                errorCode=None if t_res.success else ErrorCode.EXEC_RUNTIME_ERROR,
                message=f"Executed tool '{tool_call.name}'",
                metadata={"arguments": tool_call.arguments, "error": t_res.error},
            ))

            diagnostic_engine.record_event(DiagnosticEvent(
                eventId=f"EVT-{time.time():.3f}-VERIF",
                correlationId=cid,
                category=cat_name,
                operation=tool_call.name,
                stage="VERIFY",
                status="SUCCESS" if ver_res.is_verified else "FAILED",
                errorCode=None if ver_res.is_verified else ErrorCode.EXECUTION_VERIFICATION_MISMATCH,
                expected="Target state verified active",
                actual=ver_res.message,
                message=ver_res.message,
            ))

            # 2. Developer Observability Lifecycle Trace
            trace = ObservabilityTrace(
                command=original_command,
                understood_intent=tool_call.name.upper(),
                current_app=pre_state.active_process_name or "Windows Desktop",
                plan_steps=[tool_call.name],
                selected_tool=tool_call.name,
                target=target_str,
                verification_status="VERIFIED" if ver_res.is_verified else "RECOVERED",
                result="SUCCESS" if t_res.success else "FAILED",
                execution_time_ms=t_res.execution_time_ms,
            )
            observability.record_trace(trace)

            self.history_repo.add_record(
                command=original_command,
                action=tool_call.name,
                status="SUCCESS" if t_res.success else "FAILED",
                result=str(t_res.data) if t_res.success else t_res.error,
                execution_time_ms=t_res.execution_time_ms,
            )

        # Synthesize final response
        return self._format_tool_results_response(results, executed_names, intro_content)

    def _format_tool_results_response(
        self,
        results: List[ToolResult],
        tool_names: List[str],
        intro_content: Optional[str] = None,
    ) -> AgentResponse:
        """Format friendly combined response message from multiple tool execution results in Hindi."""
        self.state = AgentState.SPEAKING
        messages = []

        for name, res in zip(tool_names, results):
            if not res.success:
                messages.append(f"Boss, '{name}' execute karne mein error aaya: {res.error}")
                continue

            data = res.data
            if name == "get_current_time" and isinstance(data, dict):
                messages.append(f"Boss, abhi samay ho raha hai {data.get('time')} ({data.get('date')}).")
            elif name == "get_system_status" and isinstance(data, dict):
                messages.append(
                    f"Boss, System Status: CPU {data.get('cpu_usage_percent')}%, RAM {data.get('ram_percent')}% "
                    f"({data.get('ram_used_gb')}/{data.get('ram_total_gb')} GB), OS: {data.get('os')}."
                )
            elif name == "get_system_health" and isinstance(data, dict):
                messages.append(
                    f"Boss, System Health: CPU {data.get('cpu_usage_percent')}%, RAM {data.get('ram_usage_percent')}%."
                )
            elif name == "get_battery_status" and isinstance(data, dict):
                if not data.get("has_battery"):
                    messages.append("Boss, computer direct AC power par chal raha hai.")
                else:
                    messages.append(f"Boss, battery {data.get('percent')}% par hai ({data.get('charging_status')}).")
            elif name == "get_storage_status" and isinstance(data, dict):
                drives = data.get("drives", [])
                d_str = ", ".join([f"{d['device']} ({d['free_gb']} GB free)" for d in drives])
                messages.append(f"Boss, Storage status: {d_str}.")
            elif name == "get_network_status" and isinstance(data, dict):
                messages.append(f"Boss, Network: {data.get('status')} (IP: {data.get('local_ip')}).")
            elif name == "find_files" and isinstance(data, dict):
                matches = data.get("files", [])
                if not matches:
                    messages.append(f"Boss, '{data.get('query')}' naam ki koi file nahi mili.")
                else:
                    file_list = ", ".join([f"{f['name']}" for f in matches[:5]])
                    more = f" (+{len(matches)-5} more)" if len(matches) > 5 else ""
                    messages.append(f"Boss, {len(matches)} files mili hain: {file_list}{more}.")
            elif name == "list_directory" and isinstance(data, dict):
                items = data.get("items", [])
                item_names = ", ".join([f"📁 {it['name']}" if it['type'] == 'folder' else f"📄 {it['name']}" for it in items[:8]])
                more = f" (+{len(items)-8} more)" if len(items) > 8 else ""
                messages.append(f"Boss, directory mein {data.get('total_items')} items hain: {item_names}{more}.")
            elif name == "read_file_content" and isinstance(data, dict):
                preview = data.get("content", "")
                if len(preview) > 300:
                    preview = preview[:300] + "... [truncated]"
                messages.append(f"Content of '{Path(data.get('file_path')).name}':\n{preview}")
            elif isinstance(data, dict) and "message" in data:
                messages.append(data["message"])
            elif name == "get_quick_answer" and isinstance(data, dict):
                if data.get("status") == "success":
                    messages.append(f"{data.get('title')}: {data.get('summary')}")
                else:
                    messages.append(data.get("message", "Boss, koi direct jankari nahi mili."))
            elif name == "list_running_applications" and isinstance(data, dict):
                apps = data.get("applications", [])
                app_list = ", ".join([f"{a['name']} ({a['memory_percent']}% RAM)" for a in apps[:8]])
                more = f" (+{len(apps)-8} more)" if len(apps) > 8 else ""
                messages.append(f"Boss, active apps ({data.get('total_active')} total): {app_list}{more}.")
            elif name == "echo_message" and isinstance(data, dict):
                messages.append(f"{data.get('echo')}")
            elif isinstance(data, str):
                messages.append(data)
            elif isinstance(data, dict) and "summary" in data:
                messages.append(data["summary"])
            else:
                messages.append("Ji Boss, action successfully complete ho gaya.")

        final_msg = " ".join(messages)
        self.history.append({"role": "assistant", "content": final_msg})
        return AgentResponse(
            message=final_msg,
            state=AgentState.SPEAKING,
            tool_results=results,
        )

    async def _handle_confirmation(
        self,
        user_text: str,
        confirmation_decision: Optional[bool] = None,
    ) -> AgentResponse:
        """Handle user response when an action is awaiting confirmation."""
        pending = self.pending_action
        self.pending_action = None

        approved = False
        if confirmation_decision is not None:
            approved = confirmation_decision
        else:
            text_clean = user_text.lower().strip()
            if text_clean in ["yes", "y", "confirm", "proceed", "allow", "sure", "ok", "okay"]:
                approved = True

        if not approved:
            logger.info(f"User rejected pending action '{pending.tool_name}'")
            self.state = AgentState.IDLE
            msg = f"Understood. I have canceled '{pending.tool_name}'."
            self.history_repo.add_record(
                command=pending.original_command,
                action=pending.tool_name,
                status="CANCELLED",
                result=msg,
            )
            return AgentResponse(message=msg, state=AgentState.IDLE)

        # User approved: execute the single pending tool
        self.state = AgentState.EXECUTING
        t_res = await self.registry.execute(pending.tool_name, **pending.arguments)
        self.history_repo.add_record(
            command=pending.original_command,
            action=pending.tool_name,
            status="SUCCESS" if t_res.success else "FAILED",
            result=str(t_res.data) if t_res.success else t_res.error,
            execution_time_ms=t_res.execution_time_ms,
        )
        return self._format_tool_results_response([t_res], [pending.tool_name])


# Global Singleton Jarvis Agent
jarvis_agent = JarvisAgent()

