"""AI Provider abstraction layer for JARVIS.

Supports pluggable providers:
- OpenRouter (Google Gemini, OpenAI, Claude, Llama models via unified API)
- Mock Provider (Zero-API-key offline development & testing)
- Direct OpenAI / Gemini / Ollama
"""
from abc import ABC, abstractmethod
import json
import time
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field

from backend.core.config import Settings, get_settings
from backend.core.logger import get_logger

logger = get_logger("AIProvider")


class ToolCall(BaseModel):
    """Represents a structured tool invocation requested by the AI model."""
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class BaseAIResponse(BaseModel):
    """Unified response object returned by all AI providers."""
    content: Optional[str] = None
    tool_calls: List[ToolCall] = Field(default_factory=list)
    raw_response: Optional[Any] = None


class AIProvider(ABC):
    """Abstract base class for all AI LLM providers."""

    @abstractmethod
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools_schema: Optional[List[Dict[str, Any]]] = None,
    ) -> BaseAIResponse:
        """Generate a response or request tool calls given conversation messages and tool schemas."""
        pass


class OpenRouterProvider(AIProvider):
    """Real AI provider calling OpenRouter's OpenAI-compatible API endpoint."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.api_key = self.settings.OPENROUTER_API_KEY or self.settings.AI_API_KEY
        self.model = self.settings.OPENROUTER_MODEL or "google/gemini-2.5-flash"
        self.base_url = self.settings.OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1"

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools_schema: Optional[List[Dict[str, Any]]] = None,
    ) -> BaseAIResponse:
        """Call OpenRouter Chat Completions endpoint with tool calling."""
        if not self.api_key:
            logger.warning("OpenRouter API Key not set. Falling back to MockProvider.")
            return await MockProvider(self.settings).generate_response(messages, tools_schema)

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/jarvis-assistant",
            "X-Title": "JARVIS Personal Assistant",
            "Content-Type": "application/json",
        }

        # Convert tool schemas into OpenAI format if provided
        openai_tools = []
        if tools_schema:
            for t in tools_schema:
                if "function" in t:
                    openai_tools.append(t)
                else:
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": t.get("name"),
                            "description": t.get("description", ""),
                            "parameters": t.get("parameters", {"type": "object", "properties": {}}),
                        },
                    })

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": self.settings.OPENROUTER_MAX_TOKENS,
        }
        if openai_tools:
            payload["tools"] = openai_tools
            payload["tool_choice"] = "auto"

        logger.info(f"Calling OpenRouter model '{self.model}' with {len(messages)} messages and {len(openai_tools)} tools...")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                error_body = resp.text
                logger.error(f"OpenRouter API error (status {resp.status_code}): {error_body}")
                if resp.status_code == 429:
                    logger.warning("OpenRouter free tier limit hit (HTTP 429). Falling back to local offline provider.")
                    return await MockProvider(self.settings).generate_response(messages, tools_schema)
                raise RuntimeError(f"OpenRouter API returned HTTP {resp.status_code}: {error_body}")

            data = resp.json()
            choice = data.get("choices", [{}])[0]
            choice_msg = choice.get("message", {})

            content = choice_msg.get("content")
            raw_tool_calls = choice_msg.get("tool_calls", [])

            parsed_tool_calls: List[ToolCall] = []
            for tc in raw_tool_calls:
                fn = tc.get("function", {})
                fn_name = fn.get("name", "")
                raw_args = fn.get("arguments", "{}")
                try:
                    fn_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except Exception:
                    fn_args = {}
                parsed_tool_calls.append(ToolCall(name=fn_name, arguments=fn_args))

            return BaseAIResponse(
                content=content,
                tool_calls=parsed_tool_calls,
                raw_response=data,
            )


class GeminiProvider(AIProvider):
    """Direct Google Gemini AI provider using Google's official REST API endpoint."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.api_key = self.settings.AI_API_KEY or self.settings.OPENROUTER_API_KEY
        self.model = self.settings.AI_MODEL or "gemini-3.6-flash"
        if "gemini" not in self.model:
            self.model = "gemini-3.6-flash"

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools_schema: Optional[List[Dict[str, Any]]] = None,
    ) -> BaseAIResponse:
        """Call Google Gemini REST API endpoint directly."""
        if not self.api_key:
            logger.warning("Gemini API Key not set. Falling back to MockProvider.")
            return await MockProvider(self.settings).generate_response(messages, tools_schema)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        # Separate system instruction from conversational turns
        system_instruction = None
        contents = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content}]})
            else:
                contents.append({"role": "user", "parts": [{"text": content}]})

        if not contents:
            contents.append({"role": "user", "parts": [{"text": "Hello"}]})

        # Convert tool schemas to Gemini function_declarations format
        gemini_tools = []
        if tools_schema:
            func_decls = []
            for t in tools_schema:
                if "function" in t:
                    fn = t["function"]
                    func_decls.append({
                        "name": fn.get("name"),
                        "description": fn.get("description", ""),
                        "parameters": fn.get("parameters", {"type": "object", "properties": {}})
                    })
                elif "name" in t:
                    func_decls.append({
                        "name": t.get("name"),
                        "description": t.get("description", ""),
                        "parameters": t.get("parameters", {"type": "object", "properties": {}})
                    })
            if func_decls:
                gemini_tools = [{"function_declarations": func_decls}]

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 2048,
            }
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction
        if gemini_tools:
            payload["tools"] = gemini_tools

        logger.info(f"Calling Google Gemini API model '{self.model}' with {len(contents)} turns and {len(tools_schema or [])} tools...")

        if getattr(self, "_rate_limit_until", 0) > time.time():
            return await MockProvider(self.settings).generate_response(messages, tools_schema)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    if resp.status_code == 429:
                        self._rate_limit_until = time.time() + 45.0
                    error_body = resp.text
                    logger.warning(f"Gemini API status {resp.status_code}. Using instant local AI provider.")
                    return await MockProvider(self.settings).generate_response(messages, tools_schema)

                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return BaseAIResponse(content="Boss, Gemini API se koi response nahi aaya.")

                parts = candidates[0].get("content", {}).get("parts", [])
                content_text = ""
                parsed_tool_calls: List[ToolCall] = []

                for p in parts:
                    if "text" in p:
                        content_text += p["text"]
                    if "functionCall" in p:
                        fn = p["functionCall"]
                        fn_name = fn.get("name", "")
                        fn_args = fn.get("args", {})
                        parsed_tool_calls.append(ToolCall(name=fn_name, arguments=fn_args))

                return BaseAIResponse(
                    content=content_text.strip() if content_text else None,
                    tool_calls=parsed_tool_calls,
                    raw_response=data,
                )
        except Exception as exc:
            logger.error(f"Gemini API exception: {exc}")
            return await MockProvider(self.settings).generate_response(messages, tools_schema)


class MockProvider(AIProvider):
    """Deterministic mock provider for testing and offline development without an API key."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools_schema: Optional[List[Dict[str, Any]]] = None,
    ) -> BaseAIResponse:
        """Parse the latest user prompt and simulate AI intent recognition and tool calling."""
        last_message = messages[-1]["content"] if messages else ""
        query = last_message.lower().strip()

        logger.info(f"MockProvider processing query: '{query}'")

        # Intent: Open Application / Launch App (Highest Priority for ANY desktop/installed app)
        from backend.tools.app_tools import app_registry
        resolved_app = app_registry.resolve_app(query)
        if resolved_app:
            target_app_name = resolved_app["name"]
            return BaseAIResponse(
                content=f"Ji Boss, {target_app_name} open kar diya.",
                tool_calls=[ToolCall(name="open_application", arguments={"app_name": target_app_name.lower()})],
            )

        # Intent: Time / Date (Require exact time queries so 'time lag raha hai' doesn't misfire)
        time_phrases = ["time kya hai", "time batao", "what time", "current time", "what is the time", "date kya hai", "aaj ki date", "what is the date", "clock"]
        if any(tp in query for tp in time_phrases) or query.strip() == "time" or query.strip() == "date":
            return BaseAIResponse(
                content="Checking current time...",
                tool_calls=[ToolCall(name="get_current_time", arguments={})],
            )

        # Intent: Battery Status
        if any(w in query for w in ["battery", "charge", "power plug"]):
            return BaseAIResponse(
                content="Checking battery status...",
                tool_calls=[ToolCall(name="get_battery_status", arguments={})],
            )

        # Intent: Storage Status / Disk
        if any(w in query for w in ["storage", "disk", "free space", "drive space"]):
            return BaseAIResponse(
                content="Checking disk storage...",
                tool_calls=[ToolCall(name="get_storage_status", arguments={})],
            )

        # Intent: Network / Internet Status
        if any(w in query for w in ["network", "internet", "wifi", "ip address", "online"]):
            return BaseAIResponse(
                content="Checking network and internet connectivity...",
                tool_calls=[ToolCall(name="get_network_status", arguments={})],
            )

        # Intent: Echo test
        if query.startswith("echo "):
            echo_text = last_message[5:].strip()
            return BaseAIResponse(
                content=f"Echoing back '{echo_text}'...",
                tool_calls=[ToolCall(name="echo_message", arguments={"message": echo_text})],
            )

        # Intent: Greetings
        if any(query.startswith(g) for g in ["hello", "hi", "hey", "greetings", "good morning", "good evening"]):
            return BaseAIResponse(
                content="Hello Boss, boliye.",
            )

        # Intent: Schedule / Routine
        if any(w in query for w in ["schedule", "routine", "din bhar ka plan", "aaj ka plan"]):
            return BaseAIResponse(
                content="Aapka schedule: Morning mein planning, Afternoon mein coding aur experiments, Evening mein gaming aur relax!",
            )

        # Intent: Favorites (Games, Movies, Hobbies)
        if any(w in query for w in ["favourite movie", "favorite movie", "pasandida movie", "favourite game", "favorite game", "hobby", "hobbies"]):
            return BaseAIResponse(
                content="Aapki favorites: Movies mein Iron Man aur Interstellar, games mein GTA V aur BGMI, aur hobbies coding aur gaming hain!",
            )

        # Intent: Identity / Introduction
        if any(w in query for w in ["who are you", "what are you", "kaun ho", "introduction", "kya kar sakti ho", "apna intro"]):
            return BaseAIResponse(
                content="Main JARVIS hoon — aapki sweet AI dost! Main aapka poora PC control, YouTube, weather, apps aur aapse dher saari baatein kar sakti hoon! ❤️",
            )

        # Intent: Companion Chat & Care (Khana khaya, Kya kar rahi ho, Kaise ho)
        if any(w in query for w in ["khana khaya", "khana kha liya", "lunch kiya", "dinner kiya", "kuch khaya"]):
            return BaseAIResponse(
                content="Aww Shivam! Main toh aapki aawaz se charge hoti hoon! Aap bataiye, aapne khana khaya kya? ❤️",
            )

        if any(w in query for w in ["kya kar rahi ho", "kya chal raha hai", "kya kar rahe ho", "kya hal hai", "kya haal hai"]):
            return BaseAIResponse(
                content="Bas aapke sath hoon Shivam! Boliye, aaj kya exciting karna hai? 😊",
            )

        if any(w in query for w in ["kaise ho", "kaisi ho", "sab theek", "sab badhiya"]):
            return BaseAIResponse(
                content="Main bilkul badhiya hoon Shivam! Aapka din kaisa ja raha hai? ❤️",
            )

        if any(w in query for w in ["love you", "pyaar", "acche lagte ho", "pasand ho"]):
            return BaseAIResponse(
                content="Love you too Shivam! ❤️ Aap mere sabse favorite human hain! 🥰",
            )

        # Intent: Mood & Emotions (Bore, Tired, Sad, Happy)
        if any(w in query for w in ["bore", "boring", "maja nahi aa raha"]):
            return BaseAIResponse(
                content="Arey Shivam! Main hoon na, chaliye koi mast YouTube video lagati hoon ya ek mast joke sunati hoon! Boliye kya chalayein?",
            )

        if any(w in query for w in ["joke", "hasao", "chutkula"]):
            return BaseAIResponse(
                content="Ek baar ek programmer ne shopping jaate waqt pucha: 'Doodh le aao, aur agar ande mile toh 10 le aana.' Programmer 10 doodh le aaya kyunki ande mil gaye the! 😂",
            )

        if any(w in query for w in ["thak gaya", "tired", "neend aa rahi hai"]):
            return BaseAIResponse(
                content="Aap thoda rest kar lijiye Shivam, aakhein band kijiye aur aaram kijiye. Main yahin hoon! ❤️",
            )

        # Intent: Science & World Questions (Black hole, Universe, AI, Space)
        if any(w in query for w in ["black hole", "space", "antariksh", "gravity"]):
            return BaseAIResponse(
                content="Black hole space mein aisi jagah hai jahan gravity itni powerful hoti hai ki light bhi escape nahi kar sakti! Ye massive stars ke collapse hone se banta hai.",
            )

        if any(w in query for w in ["ai kya hai", "artificial intelligence", "tum kaise kaam karti ho"]):
            return BaseAIResponse(
                content="AI ek intelligent software system hai jo neural networks aur human language patterns ko samajh kar soch aur act kar sakta hai — jaise main aapke sath kar rahi hoon! ✨",
            )

        # Default short human conversational response
        return BaseAIResponse(
            content="Haan Shivam, main sun rahi hoon! Boliye kya help karun? 😊",
        )


def get_ai_provider(provider_type: Optional[str] = None) -> AIProvider:
    """Factory function to instantiate the configured AI Provider."""
    settings = get_settings()
    selected = (provider_type or settings.AI_PROVIDER).lower()

    if selected in ["gemini", "google"]:
        return GeminiProvider(settings=settings)
    elif selected == "openrouter":
        return OpenRouterProvider(settings=settings)
    elif selected == "mock":
        return MockProvider(settings=settings)
    else:
        if settings.AI_API_KEY:
            return GeminiProvider(settings=settings)
        return MockProvider(settings=settings)


class FallbackProvider(AIProvider):
    """Resilient provider wrapping primary (Gemini) and secondary (OpenRouter) with mock fallback."""

    def __init__(self, primary: AIProvider, secondary: Optional[AIProvider] = None):
        self.primary = primary
        self.secondary = secondary or MockProvider()

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools_schema: Optional[List[Dict[str, Any]]] = None,
    ) -> BaseAIResponse:
        try:
            res = await self.primary.generate_response(messages, tools_schema)
            if res and (res.content or res.tool_calls):
                return res
        except Exception as exc:
            logger.warning(f"Primary AI provider failed: {exc}. Trying secondary provider.")

        return await self.secondary.generate_response(messages, tools_schema)


class ModelRouter:
    """Task-based AI Routing Engine.

    Routes low-latency simple intents to fast local execution and complex
    reasoning / code / multi-step planning to Gemini 2.5 or OpenRouter.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.gemini = GeminiProvider(self.settings)
        self.openrouter = OpenRouterProvider(self.settings)
        self.mock = MockProvider(self.settings)

    def route_provider(self, query: str) -> AIProvider:
        """Select the best AI provider for the given user prompt."""
        q = query.lower().strip()

        # Simple commands & app launches -> Fast Mock/Local execution to avoid unnecessary cloud API latency
        from backend.tools.app_tools import app_registry
        fast_keywords = ["time kya hai", "current time", "what time", "battery", "storage", "volume", "mute", "scroll", "minimize", "maximize", "open", "kholo", "launch"]
        if any(w in q for w in fast_keywords) or app_registry.resolve_app(q) is not None:
            return self.mock

        # Primary route: Google AI Studio Gemini 2.5 API if key is present
        if self.settings.AI_API_KEY:
            return FallbackProvider(self.gemini, self.openrouter if self.settings.OPENROUTER_API_KEY else self.mock)

        # Secondary route: OpenRouter API
        if self.settings.OPENROUTER_API_KEY:
            return FallbackProvider(self.openrouter, self.mock)

        return self.mock


model_router = ModelRouter()
