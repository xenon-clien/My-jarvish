"""JARVIS 3.0 - Master Engine Orchestrator.

The central brain and deterministic execution coordinator.
Implements the complete pipeline:
User -> Input -> Normalizer -> Router -> Planner -> TaskManager -> Permissions ->
Resource Locks -> TaskQueue -> Adapter -> Execution -> Verification -> Recovery -> Health -> Output
"""
import asyncio
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from adapters import initialize_all_adapters, voice_adapter
from ai.gemini_planner import gemini_planner
from core.diagnostics_engine import diagnostics_engine
from core.events import EventType, JarvisEvent, event_bus
from core.health_manager import health_manager
from core.logger import get_logger
from core.models import ToolExecutionResult
from core.permissions import permission_manager
from core.task_manager import task_manager
from core.task_queue import task_queue
from core.task_state import TaskItem, TaskPriority, TaskState
from core.tool_registry import default_registry
from nlu.canonical_intents import CanonicalIntent
from nlu.deterministic_router import DeterministicRouter, RouteDecision

logger = get_logger("JarvisEngine")


class EngineResponse(BaseModel):
    """Structured response returned for every interaction turn."""
    message: str
    success: bool
    correlation_id: str
    tasks_executed: List[Dict[str, Any]] = Field(default_factory=list)
    state: str = "IDLE"
    execution_time_ms: float = 0.0


class JarvisEngine:
    """Master operating system coordinator for JARVIS 3.0."""

    def __init__(self):
        self._is_initialized = False
        self.conversation_history: List[Dict[str, str]] = []
        self._initialize()

    def _initialize(self) -> None:
        if not self._is_initialized:
            logger.info("Initializing JARVIS 3.0 Engine and Application Adapters...")
            initialize_all_adapters()
            self._is_initialized = True
            logger.info(f"JARVIS 3.0 initialized with {len(default_registry.list_tools())} registered tools.")

    def reset_conversation(self) -> None:
        self.conversation_history.clear()
        task_queue.cancel_all(reason="Reset conversation")

    async def process_user_input(self, user_text: str, speak_output: bool = True) -> EngineResponse:
        """Process a single turn of user command/chat through the complete resilient pipeline."""
        start_turn_time = time.time()
        raw = (user_text or "").strip()
        if not raw:
            return EngineResponse(
                message="Boliye Boss, main sun raha hoon.",
                success=True,
                correlation_id="EMPTY",
            )

        # 1. Start Diagnostic Transaction Trace with unique Correlation ID
        cid = diagnostics_engine.start_trace(raw)
        logger.info(f"[{cid}] Processing command: '{raw}'")

        tasks_summary = []
        final_message = ""
        overall_success = True

        # 2. Stage 1: Deterministic Semantic Router (Zero-Latency Local Execution)
        route_decision = DeterministicRouter.route_command(raw)

        if route_decision:
            logger.info(f"[{cid}] Deterministic Route matched: '{route_decision.tool_name}' (Confidence: {route_decision.confidence})")

            # 2a. Multi-step command chain
            if route_decision.is_multi_step and route_decision.plan_steps:
                created_tasks = []
                prev_task_id = None
                for step in route_decision.plan_steps:
                    deps = [prev_task_id] if prev_task_id else []
                    t = task_manager.create_task(
                        tool_name=step["tool"],
                        arguments=step.get("arguments", {}),
                        priority=TaskPriority.HIGH,
                        dependencies=deps,
                    )
                    created_tasks.append(t)
                    prev_task_id = t.id

                # Execute sequential plan
                executed_tasks = await task_manager.execute_plan(created_tasks)
                for t in executed_tasks:
                    tasks_summary.append({
                        "task_id": t.id,
                        "tool": t.tool_name,
                        "status": t.state.value,
                        "duration_ms": t.execution_duration_ms(),
                    })
                    # Update health score for tool subsystem
                    health_manager.record_call(t.tool_name, t.is_successful(), t.error)

                succ_count = sum(1 for t in executed_tasks if t.is_successful())
                if succ_count == len(executed_tasks):
                    final_message = "Ji Boss, saare steps successfully complete ho gaye."
                    overall_success = True
                else:
                    failed_step = next(t for t in executed_tasks if not t.is_successful())
                    final_message = f"Boss, {succ_count}/{len(executed_tasks)} steps ho gaye. '{failed_step.tool_name}' par issue aaya: {failed_step.error}"
                    overall_success = False

            # 2b. Single atomic tool execution
            else:
                task = task_manager.create_task(
                    tool_name=route_decision.tool_name,
                    arguments=route_decision.arguments,
                    priority=TaskPriority.HIGH,
                )
                executed_task = await task_manager.execute_task(task.id)
                tasks_summary.append({
                    "task_id": executed_task.id,
                    "tool": executed_task.tool_name,
                    "status": executed_task.state.value,
                    "duration_ms": executed_task.execution_duration_ms(),
                })
                health_manager.record_call(executed_task.tool_name, executed_task.is_successful(), executed_task.error)

                overall_success = executed_task.is_successful()
                if overall_success:
                    final_message = executed_task.message or route_decision.immediate_response or "Ji Boss, complete kar diya."
                else:
                    final_message = f"Boss, '{route_decision.tool_name}' execute nahi ho paya: {executed_task.error}"

        # 3. Stage 2: Complex / Conversational Reasoning via Gemini Planner
        else:
            logger.info(f"[{cid}] Delegating complex turn to Gemini Planner...")
            planner_output = await gemini_planner.plan(
                user_prompt=raw,
                conversation_history=self.conversation_history,
            )

            # Direct conversation
            if planner_output.is_direct_chat:
                final_message = planner_output.chat_message
                overall_success = True
            # AI Planned Tasks
            else:
                created_tasks = []
                prev_id = None
                for step in planner_output.tasks:
                    deps = [prev_id] if prev_id else []
                    t = task_manager.create_task(
                        tool_name=step["tool_name"],
                        arguments=step.get("arguments", {}),
                        priority=TaskPriority.HIGH,
                        dependencies=deps,
                    )
                    created_tasks.append(t)
                    prev_id = t.id

                executed_tasks = await task_manager.execute_plan(created_tasks)
                for t in executed_tasks:
                    tasks_summary.append({
                        "task_id": t.id,
                        "tool": t.tool_name,
                        "status": t.state.value,
                        "duration_ms": t.execution_duration_ms(),
                    })
                    health_manager.record_call(t.tool_name, t.is_successful(), t.error)

                overall_success = all(t.is_successful() for t in executed_tasks)
                final_message = "Ji Boss, task successfully complete ho gaya." if overall_success else "Boss, task execution mein error aaya."

        # 4. Record history & Complete Diagnostic Trace
        self.conversation_history.append({"role": "user", "content": raw})
        self.conversation_history.append({"role": "assistant", "content": final_message})

        from memory.memory_manager import memory_manager
        memory_manager.short_term.add_turn("user", raw)
        memory_manager.short_term.add_turn("assistant", final_message)
        if tasks_summary:
            memory_manager.short_term.last_tool_executed = tasks_summary[-1]["tool"]

        diagnostics_engine.end_trace(cid, success=overall_success, final_response=final_message)
        total_time_ms = round((time.time() - start_turn_time) * 1000, 2)

        # 5. Voice Audio Output
        if speak_output and final_message:
            voice_adapter.speak(final_message, block=False)

        return EngineResponse(
            message=final_message,
            success=overall_success,
            correlation_id=cid,
            tasks_executed=tasks_summary,
            state="IDLE",
            execution_time_ms=total_time_ms,
        )


# Global Master Engine singleton
jarvis_engine = JarvisEngine()
