"""JARVIS 3.0 - Gemini Structured Planner.

Coordinates AI reasoning and converts user requests into verified TaskItem plans.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from ai.context_manager import ContextManager
from ai.provider import AIStructuredResponse, GeminiProvider, MockProvider
from core.logger import get_logger
from core.task_state import TaskItem, TaskPriority
from core.tool_registry import default_registry

logger = get_logger("GeminiPlanner")


class PlannerOutput(BaseModel):
    is_direct_chat: bool
    chat_message: str = ""
    tasks: List[Dict[str, Any]] = []


class GeminiPlanner:
    """Uses Gemini API as reasoning engine to plan tasks and tool parameters."""

    def __init__(self):
        self.provider = GeminiProvider()
        self.mock = MockProvider()

    async def plan(
        self,
        user_prompt: str,
        conversation_history: List[Dict[str, str]],
        active_app: Optional[str] = None,
    ) -> PlannerOutput:
        """Generate structured task plan from natural language prompt."""
        messages, tools_schema = ContextManager.prepare_llm_context(
            user_prompt=user_prompt,
            conversation_history=conversation_history,
            active_app=active_app,
        )

        try:
            ai_resp: AIStructuredResponse = await self.provider.plan_or_chat(messages, tools_schema)
        except Exception as exc:
            logger.warning(f"Gemini planner failed: {exc}. Using fallback provider.")
            ai_resp = await self.mock.plan_or_chat(messages, tools_schema)

        # 1. Conversational Reply
        if ai_resp.response_type == "conversation":
            return PlannerOutput(
                is_direct_chat=True,
                chat_message=ai_resp.message or "Ji Boss! Main aapki madad ke liye tayar hoon.",
            )

        # 2. Multi-Step Plan
        if ai_resp.response_type == "plan" and ai_resp.plan_steps:
            validated_steps = []
            for step in ai_resp.plan_steps:
                tool_name = step.get("tool")
                if tool_name and default_registry.has_tool(tool_name):
                    validated_steps.append({
                        "tool_name": tool_name,
                        "arguments": step.get("arguments", {}),
                    })
            if validated_steps:
                return PlannerOutput(
                    is_direct_chat=False,
                    tasks=validated_steps,
                )

        # 3. Single Tool Call
        if ai_resp.response_type == "tool_call" and ai_resp.tool_name:
            tool_name = ai_resp.tool_name
            # Strict Tool Validation: check if tool exists
            if not default_registry.has_tool(tool_name):
                logger.warning(f"AI requested non-existent tool: '{tool_name}'")
                return PlannerOutput(
                    is_direct_chat=True,
                    chat_message=f"Boss, capability '{tool_name}' currently installed nahi hai.",
                )

            return PlannerOutput(
                is_direct_chat=False,
                tasks=[{
                    "tool_name": tool_name,
                    "arguments": ai_resp.arguments,
                }],
            )

        return PlannerOutput(
            is_direct_chat=True,
            chat_message=ai_resp.message or "Ji Boss!",
        )


gemini_planner = GeminiPlanner()
