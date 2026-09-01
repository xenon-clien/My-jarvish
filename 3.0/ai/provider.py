"""JARVIS 3.0 - AI Provider Abstraction Layer.

Decouples JARVIS core from specific LLM providers:
- Google Gemini 2.5 / Flash (Official Google AI Studio REST API)
- OpenRouter (Unified multi-model API)
- Deterministic Mock Provider (Zero-token offline fallback)
"""
from abc import ABC, abstractmethod
import json
import time
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field

from core.config import get_settings
from core.logger import get_logger

logger = get_logger("AIProvider")


class AIStructuredResponse(BaseModel):
    """Structured decision output from LLM planner."""
    response_type: str = "conversation"  # tool_call, plan, conversation
    tool_name: Optional[str] = None
    arguments: Dict[str, Any] = Field(default_factory=dict)
    plan_steps: List[Dict[str, Any]] = Field(default_factory=list)
    message: Optional[str] = None
    confidence: float = 1.0
    raw_response: Optional[Any] = None


class BaseAIProvider(ABC):
    """Abstract interface for all AI Brain providers."""

    @abstractmethod
    async def plan_or_chat(
        self,
        messages: List[Dict[str, str]],
        tools_schema: Optional[List[Dict[str, Any]]] = None,
    ) -> AIStructuredResponse:
        """Process messages and return structured tool call or conversational reply."""
        pass


class GeminiProvider(BaseAIProvider):
    """Direct Google AI Studio Gemini API Provider."""

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.AI_API_KEY or self.settings.OPENROUTER_API_KEY
        self.model = self.settings.AI_MODEL or "gemini-2.5-flash"
        self._rate_limit_until = 0.0

    async def plan_or_chat(
        self,
        messages: List[Dict[str, str]],
        tools_schema: Optional[List[Dict[str, Any]]] = None,
    ) -> AIStructuredResponse:
        if not self.api_key:
            logger.warning("No Gemini API Key configured. Using MockProvider.")
            return await MockProvider().plan_or_chat(messages, tools_schema)

        if time.time() < self._rate_limit_until:
            logger.warning("Gemini rate limit cooldown active. Using local fallback.")
            return await MockProvider().plan_or_chat(messages, tools_schema)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        # Build contents payload
        system_prompt = None
        contents = []

        for msg in messages:
            role = msg.get("role", "user")
            text = msg.get("content", "")
            if role == "system":
                system_prompt = {"parts": [{"text": text}]}
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": text}]})
            else:
                contents.append({"role": "user", "parts": [{"text": text}]})

        if not contents:
            contents.append({"role": "user", "parts": [{"text": "Hello"}]})

        # Format function declarations for Gemini
        gemini_tools = []
        if tools_schema:
            func_decls = []
            for t in tools_schema:
                fn_name = t.get("name") or t.get("function", {}).get("name")
                fn_desc = t.get("description") or t.get("function", {}).get("description", "")
                fn_params = t.get("parameters") or t.get("function", {}).get("parameters", {"type": "object", "properties": {}})
                if fn_name:
                    func_decls.append({
                        "name": fn_name,
                        "description": fn_desc,
                        "parameters": fn_params,
                    })
            if func_decls:
                gemini_tools = [{"function_declarations": func_decls}]

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.settings.AI_TEMPERATURE,
                "maxOutputTokens": 1024,
            },
        }
        if system_prompt:
            payload["systemInstruction"] = system_prompt
        if gemini_tools:
            payload["tools"] = gemini_tools

        try:
            async with httpx.AsyncClient(timeout=self.settings.AI_TIMEOUT_SECONDS) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 429:
                    self._rate_limit_until = time.time() + 30.0
                    logger.warning("Gemini 429 Rate Limit hit. Temporarily cooling down.")
                    return await MockProvider().plan_or_chat(messages, tools_schema)

                if resp.status_code != 200:
                    logger.error(f"Gemini API error (HTTP {resp.status_code}): {resp.text}")
                    return await MockProvider().plan_or_chat(messages, tools_schema)

                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return AIStructuredResponse(response_type="conversation", message="Boss, Gemini se response nahi aaya.")

                parts = candidates[0].get("content", {}).get("parts", [])
                text_msg = ""
                for p in parts:
                    if "functionCall" in p:
                        fc = p["functionCall"]
                        fn_name = fc.get("name")
                        fn_args = fc.get("args", {})
                        return AIStructuredResponse(
                            response_type="tool_call",
                            tool_name=fn_name,
                            arguments=fn_args,
                            confidence=0.98,
                            raw_response=data,
                        )
                    elif "text" in p:
                        text_msg += p["text"]

                return AIStructuredResponse(
                    response_type="conversation",
                    message=text_msg.strip(),
                    confidence=1.0,
                    raw_response=data,
                )

        except Exception as exc:
            logger.error(f"Gemini provider exception: {exc}")
            return await MockProvider().plan_or_chat(messages, tools_schema)


class MockProvider(BaseAIProvider):
    """Offline local rule-based fallback provider."""

    async def plan_or_chat(
        self,
        messages: List[Dict[str, str]],
        tools_schema: Optional[List[Dict[str, Any]]] = None,
    ) -> AIStructuredResponse:
        last_msg = messages[-1]["content"] if messages else ""
        query = last_msg.lower().strip()

        # Greetings
        if any(query.startswith(g) for g in ["hello", "hi", "hey", "namaste", "pranam"]):
            return AIStructuredResponse(
                response_type="conversation",
                message="Namaste Shivam! Main JARVIS hoon. Boliye main aapki kya madad kar sakta hoon?",
            )

        # Time
        if any(w in query for w in ["time", "samay", "date"]):
            return AIStructuredResponse(
                response_type="tool_call",
                tool_name="system.time",
                arguments={},
            )

        # Status
        if any(w in query for w in ["status", "health", "system"]):
            return AIStructuredResponse(
                response_type="tool_call",
                tool_name="diagnostics.health_check",
                arguments={},
            )

        return AIStructuredResponse(
            response_type="conversation",
            message="Haan Shivam, main sun raha hoon! Boliye kya help karun?",
        )
