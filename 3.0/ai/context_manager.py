"""JARVIS 3.0 - Context & Token Optimization Manager.

Prunes conversation context and filters tool schemas to only provide
what Gemini needs for the current turn, minimizing latency and token costs.
"""
from typing import Any, Dict, List, Optional
from core.config import get_settings
from core.models import ToolCategory
from core.tool_registry import default_registry


class ContextManager:
    """Provides focused, minimal context to the AI Planner."""

    @staticmethod
    def get_system_prompt(user_name: str = "Shivam") -> str:
        """Return standardized JARVIS persona and reasoning prompt."""
        return (
            f"You are JARVIS, a highly reliable, intelligent desktop AI assistant created to assist {user_name}.\n"
            "CRITICAL OPERATING RULES:\n"
            "1. You are the Brain and Planner. You do NOT directly execute actions yourself.\n"
            "2. When the user asks you to perform an action, select the exact registered tool.\n"
            "3. If the user asks a multi-step request, select the primary starting tool.\n"
            "4. NEVER output arbitrary shell or bash commands.\n"
            "5. Understand Hindi, Hinglish, and English naturally.\n"
            "6. Keep conversational replies crisp, polite, and respectful in Hindi/Hinglish (address the user as 'Boss' or 'Shivam')."
        )

    @classmethod
    def prepare_llm_context(
        cls,
        user_prompt: str,
        conversation_history: List[Dict[str, str]],
        active_app: Optional[str] = None,
        max_history_turns: int = 4,
    ) -> tuple[List[Dict[str, str]], List[Dict[str, Any]]]:
        """Build compact message history and filter relevant tool schemas."""
        settings = get_settings()

        # 1. System instruction
        messages = [
            {"role": "system", "content": cls.get_system_prompt(settings.USER_NAME)}
        ]

        # 2. Add recent conversational turns only
        recent_turns = conversation_history[-(max_history_turns * 2):]
        messages.extend(recent_turns)

        # 3. Add current turn
        messages.append({"role": "user", "content": user_prompt})

        # 4. Contextual Tool Filtering
        q = user_prompt.lower()
        if any(w in q for w in ["youtube", "video", "short", "gaana", "song", "play", "pause"]):
            relevant_categories = [ToolCategory.MEDIA, ToolCategory.BROWSER]
        elif any(w in q for w in ["whatsapp", "message", "call", "phone"]):
            relevant_categories = [ToolCategory.COMMUNICATION]
        elif any(w in q for w in ["volume", "battery", "storage", "time", "status", "health"]):
            relevant_categories = [ToolCategory.SYSTEM, ToolCategory.DIAGNOSTICS]
        else:
            relevant_categories = None  # all tools

        if relevant_categories:
            schemas = []
            for cat in relevant_categories:
                for t in default_registry.list_tools(category=cat):
                    schemas.append(t.get_openai_tool_schema())
        else:
            schemas = default_registry.get_openai_tool_schemas()

        return messages, schemas
