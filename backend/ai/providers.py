"""AI Provider abstraction layer for JARVIS.

Supports pluggable providers:
- OpenRouter (Google Gemini, OpenAI, Claude, Llama models via unified API)
- Mock Provider (Zero-API-key offline development & testing)
- Direct OpenAI / Gemini / Ollama
"""
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
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

class ProviderStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    TEMPORARILY_DEGRADED = "TEMPORARILY_DEGRADED"
    DISABLED_QUOTA = "DISABLED_QUOTA"
    DISABLED_AUTH = "DISABLED_AUTH"
    DISABLED_ACCESS = "DISABLED_ACCESS"


class ErrorCategory(str, Enum):
    CATEGORY_A_TEMPORARY = "CATEGORY_A_TEMPORARY"
    CATEGORY_B_QUOTA_EXHAUSTED = "CATEGORY_B_QUOTA_EXHAUSTED"
    CATEGORY_C_AUTH_INVALID = "CATEGORY_C_AUTH_INVALID"
    CATEGORY_D_MODEL_CONFIG = "CATEGORY_D_MODEL_CONFIG"


class AstraPersistedState(BaseModel):
    """Persisted circuit-breaker and quota state for Astra across restarts."""
    status: ProviderStatus = ProviderStatus.AVAILABLE
    reason: Optional[str] = None
    last_error_time: float = 0.0
    retry_after: float = 0.0
    consecutive_failures: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    fallback_requests: int = 0
    last_used_model: str = "gpt-6-astra"
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class AstraAPIError(Exception):
    """Custom exception containing classified category and status code for Astra errors."""
    def __init__(self, status_code: int, category: ErrorCategory, message: str):
        super().__init__(f"[{category.value}] HTTP {status_code}: {message}")
        self.status_code = status_code
        self.category = category
        self.error_message = message


class AstraProvider(AIProvider):
    """Primary AI provider calling OpenAI GPT-6 Astra via Experiential Labs OpenAI-compatible gateway."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.api_key = getattr(self.settings, "ASTRA_API_KEY", "") or getattr(self.settings, "OPENAI_API_KEY", "")
        self.model = getattr(self.settings, "ASTRA_MODEL", "gpt-6-astra")
        self.base_url = getattr(self.settings, "ASTRA_BASE_URL", "https://api.experientiallabs.ai/v1")
        self.timeout = float(getattr(self.settings, "ASTRA_TIMEOUT_SECONDS", 15.0))

    def classify_error(
        self,
        status_code: int,
        response_text: str,
        exc: Optional[Exception] = None
    ) -> Tuple[ErrorCategory, str]:
        """Classify Astra gateway errors into distinct operational categories.
        
        Category A: Temporary (500, 502, 503, 504, network timeout, concurrency rate limits).
        Category B: Quota Exhausted / Organization Under Review / Balance Expired.
        Category C: Authentication / Invalid API Key (401).
        Category D: Model configuration / Bad request (400, 404).
        """
        text_lower = (response_text or "").lower()

        # Category B Check: Quota Exhausted / Org Review / Billing
        quota_signatures = [
            "insufficient_quota",
            "org_under_review",
            "under review",
            "quota",
            "billing",
            "exceeded your current quota",
            "exceeded your balance",
            "credit limit",
        ]
        has_quota_signature = any(sig in text_lower for sig in quota_signatures)

        if status_code == 429:
            if has_quota_signature:
                return (
                    ErrorCategory.CATEGORY_B_QUOTA_EXHAUSTED,
                    f"Astra quota exhausted or account under review: {response_text[:300]}",
                )
            return (
                ErrorCategory.CATEGORY_A_TEMPORARY,
                f"Astra concurrency / rate limit hit (HTTP 429): {response_text[:300]}",
            )

        if status_code in [402, 403]:
            if has_quota_signature or "forbidden" in text_lower or "payment" in text_lower:
                return (
                    ErrorCategory.CATEGORY_B_QUOTA_EXHAUSTED,
                    f"Astra access forbidden / quota required (HTTP {status_code}): {response_text[:300]}",
                )
            return (
                ErrorCategory.CATEGORY_C_AUTH_INVALID,
                f"Astra forbidden / access denied (HTTP {status_code}): {response_text[:300]}",
            )

        if status_code == 401 or "invalid api key" in text_lower or "unauthorized" in text_lower:
            return (
                ErrorCategory.CATEGORY_C_AUTH_INVALID,
                f"Astra authentication failure (HTTP 401): {response_text[:300]}",
            )

        if status_code in [400, 404]:
            return (
                ErrorCategory.CATEGORY_D_MODEL_CONFIG,
                f"Astra model or syntax error (HTTP {status_code}): {response_text[:300]}",
            )

        if status_code in [500, 502, 503, 504]:
            return (
                ErrorCategory.CATEGORY_A_TEMPORARY,
                f"Astra gateway server error (HTTP {status_code}): {response_text[:300]}",
            )

        if exc:
            return (
                ErrorCategory.CATEGORY_A_TEMPORARY,
                f"Astra network / communication failure: {exc}",
            )

        return (
            ErrorCategory.CATEGORY_A_TEMPORARY,
            f"Astra HTTP {status_code} error: {response_text[:300]}",
        )

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools_schema: Optional[List[Dict[str, Any]]] = None,
    ) -> BaseAIResponse:
        """Call Astra chat completions API endpoint with structured tool calling."""
        if not self.api_key:
            cat, reason = self.classify_error(401, "Astra API key not configured")
            raise AstraAPIError(401, cat, reason)

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/jarvis-assistant",
            "X-Title": "JARVIS Personal Assistant",
            "Content-Type": "application/json",
        }

        # Format tool schemas into standard OpenAI format
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
            "max_tokens": 2048,
        }
        if openai_tools:
            payload["tools"] = openai_tools
            payload["tool_choice"] = "auto"

        logger.info(f"Calling Primary AI (Astra model '{self.model}') with {len(messages)} messages and {len(openai_tools)} tools...")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code != 200:
                    cat, reason = self.classify_error(resp.status_code, resp.text)
                    logger.warning(f"Astra API error (HTTP {resp.status_code}, Category: {cat.value}): {reason}")
                    raise AstraAPIError(resp.status_code, cat, reason)

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
        except AstraAPIError:
            raise
        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as net_err:
            cat, reason = self.classify_error(0, "", exc=net_err)
            raise AstraAPIError(0, cat, reason)
        except Exception as exc:
            cat, reason = self.classify_error(0, "", exc=exc)
            raise AstraAPIError(0, cat, reason)


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
        self.model = self.settings.AI_MODEL or "gemini-3.5-flash-lite"
        if "gemini" not in self.model or self.model in ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
            self.model = "gemini-3.5-flash-lite"

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
            async with httpx.AsyncClient(timeout=15.0) as client:
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


class AIProviderRouter(AIProvider):
    """Authoritative AI Provider Router with Safe Quota-Aware Failover.
    
    Primary: OpenAI GPT-6 Astra (gpt-6-astra)
    Standby Fallback: Google Gemini (gemini-3.5-flash-lite)
    Emergency Offline: MockProvider (Deterministic Local Rules)
    
    Features:
    - Persistent circuit breaker (logs/ai/astra_state.json).
    - Zero-request bypass on subsequent calls when quota is exhausted or auth is invalid.
    - Automatic fallback to Gemini with schema preservation.
    - Developer reset command via `/provider reset astra`.
    """

    def __init__(self, settings: Optional[Settings] = None, state_file_path: Optional[str] = None):
        self.settings = settings or get_settings()
        self.astra = AstraProvider(self.settings)
        self.gemini = GeminiProvider(self.settings)
        self.mock = MockProvider(self.settings)
        self._lock = threading.RLock()

        log_dir = Path(os.path.join(os.path.dirname(__file__), "..", "..", "logs", "ai")).resolve()
        log_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = Path(state_file_path) if state_file_path else (log_dir / "astra_state.json")

        self.state = AstraPersistedState()
        self._load_state()

    def _load_state(self) -> None:
        """Load persisted circuit-breaker and quota state from disk."""
        with self._lock:
            if self.state_file.exists():
                try:
                    with open(self.state_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.state = AstraPersistedState(**data)
                except Exception as e:
                    logger.warning(f"Could not read Astra state file ({e}); initializing default state.")

    def _save_state(self) -> None:
        """Persist circuit-breaker and quota state to disk."""
        with self._lock:
            try:
                self.state.updated_at = datetime.now().isoformat()
                with open(self.state_file, "w", encoding="utf-8") as f:
                    f.write(self.state.model_dump_json(indent=2))
            except Exception as e:
                logger.error(f"Failed to persist Astra state: {e}")

    def reset_astra_state(self) -> Dict[str, Any]:
        """Manual developer reset command (/provider reset astra).
        
        Restores Astra status to AVAILABLE and re-enables live checking.
        """
        with self._lock:
            self.state.status = ProviderStatus.AVAILABLE
            self.state.reason = "Manual reset by administrator / command"
            self.state.consecutive_failures = 0
            self.state.retry_after = 0.0
            self._save_state()
            logger.info("[AIProviderRouter] Astra state manually reset to AVAILABLE. Live routing re-enabled.")
            return self.get_status_summary()

    def get_status_summary(self) -> Dict[str, Any]:
        """Return structured diagnostic summary of AI provider routing architecture."""
        with self._lock:
            return {
                "architecture": "PRIMARY: OpenAI GPT-6 Astra | FALLBACK: Google Gemini | OFFLINE: Mock",
                "primary_provider": "astra",
                "fallback_provider": "gemini",
                "astra_model": self.astra.model,
                "gemini_model": self.gemini.model,
                "astra_status": self.state.status.value,
                "astra_reason": self.state.reason,
                "total_requests": self.state.total_requests,
                "successful_requests": self.state.successful_requests,
                "fallback_requests": self.state.fallback_requests,
                "consecutive_failures": self.state.consecutive_failures,
                "retry_after": self.state.retry_after,
                "state_file": str(self.state_file),
                "updated_at": self.state.updated_at,
            }

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools_schema: Optional[List[Dict[str, Any]]] = None,
    ) -> BaseAIResponse:
        """Execute request with Astra Primary, Gemini Fallback, and Zero-Request Quota bypass."""
        with self._lock:
            self._load_state()
            current_status = self.state.status

        # -------------------------------------------------------------
        # STEP 1: CIRCUIT BREAKER QUOTA / AUTH ZERO-CALL BYPASS CHECK
        # -------------------------------------------------------------
        if current_status in [ProviderStatus.DISABLED_QUOTA, ProviderStatus.DISABLED_AUTH, ProviderStatus.DISABLED_ACCESS]:
            logger.info(
                f"[AIProviderRouter] Circuit Breaker Active: Astra is {current_status.value}. "
                f"Bypassing Astra entirely (0 network calls) -> Routing directly to Google Gemini fallback."
            )
            with self._lock:
                self.state.fallback_requests += 1
                self._save_state()
            return await self._fallback_to_gemini(
                messages, tools_schema, reason=f"Astra circuit breaker active ({current_status.value})"
            )

        if current_status == ProviderStatus.TEMPORARILY_DEGRADED:
            if time.time() < self.state.retry_after:
                remaining = round(self.state.retry_after - time.time(), 1)
                logger.info(
                    f"[AIProviderRouter] Astra is TEMPORARILY_DEGRADED ({remaining}s backoff remaining). "
                    f"Routing directly to Google Gemini fallback."
                )
                with self._lock:
                    self.state.fallback_requests += 1
                    self._save_state()
                return await self._fallback_to_gemini(
                    messages, tools_schema, reason=f"Astra temporary degradation active ({remaining}s remaining)"
                )
            else:
                logger.info("[AIProviderRouter] Temporary degradation backoff expired. Attempting probe request to Astra.")

        # -------------------------------------------------------------
        # STEP 2: PRIMARY PROVIDER INVOCATION (GPT-6 ASTRA)
        # -------------------------------------------------------------
        with self._lock:
            self.state.total_requests += 1
            self._save_state()

        try:
            response = await self.astra.generate_response(messages, tools_schema)
            # Success: restore AVAILABLE status and reset failures
            with self._lock:
                self.state.status = ProviderStatus.AVAILABLE
                self.state.consecutive_failures = 0
                self.state.retry_after = 0.0
                self.state.reason = None
                self.state.successful_requests += 1
                self._save_state()
            return response
        except AstraAPIError as api_err:
            return await self._handle_astra_failure(messages, tools_schema, api_err.category, api_err.error_message)
        except Exception as exc:
            cat, reason = self.astra.classify_error(0, "", exc=exc)
            return await self._handle_astra_failure(messages, tools_schema, cat, reason)

    async def _handle_astra_failure(
        self,
        messages: List[Dict[str, str]],
        tools_schema: Optional[List[Dict[str, Any]]],
        category: ErrorCategory,
        reason: str,
    ) -> BaseAIResponse:
        """Handle Astra failure according to error category and route to Gemini fallback."""
        with self._lock:
            self.state.consecutive_failures += 1
            self.state.last_error_time = time.time()
            self.state.reason = reason
            self.state.fallback_requests += 1

            if category == ErrorCategory.CATEGORY_B_QUOTA_EXHAUSTED:
                self.state.status = ProviderStatus.DISABLED_QUOTA
                logger.critical(
                    f"[AIProviderRouter] [QUOTA_EXHAUSTED] Astra quota or account review issue: {reason}. "
                    f"Transitioned status to DISABLED_QUOTA. Subsequent requests will immediately bypass Astra."
                )
            elif category == ErrorCategory.CATEGORY_C_AUTH_INVALID:
                self.state.status = ProviderStatus.DISABLED_AUTH
                logger.error(
                    f"[AIProviderRouter] [AUTH_INVALID] Astra authentication failed: {reason}. "
                    f"Transitioned status to DISABLED_AUTH. Subsequent requests will bypass Astra."
                )
            elif category == ErrorCategory.CATEGORY_A_TEMPORARY:
                self.state.status = ProviderStatus.TEMPORARILY_DEGRADED
                self.state.retry_after = time.time() + 30.0
                logger.warning(
                    f"[AIProviderRouter] [TEMPORARY_DEGRADATION] Astra temporary error: {reason}. "
                    f"Degrading for 30s before retry. Falling back to Gemini."
                )
            else:
                logger.warning(f"[AIProviderRouter] Astra configuration error: {reason}. Falling back to Gemini.")

            self._save_state()

        return await self._fallback_to_gemini(messages, tools_schema, reason=f"Astra failure: {reason}")

    async def _fallback_to_gemini(
        self,
        messages: List[Dict[str, str]],
        tools_schema: Optional[List[Dict[str, Any]]],
        reason: str,
    ) -> BaseAIResponse:
        """Execute request using Google Gemini standby fallback, preserving tool schemas."""
        logger.info(f"[AIProviderRouter] [FALLBACK] Executing Google Gemini standby fallback (Trigger: {reason})...")
        try:
            gemini_response = await self.gemini.generate_response(messages, tools_schema)
            if gemini_response and (gemini_response.content or gemini_response.tool_calls):
                logger.info("[AIProviderRouter] [FALLBACK_SUCCESS] Google Gemini standby fallback succeeded.")
                return gemini_response
        except Exception as gemini_exc:
            logger.error(f"[AIProviderRouter] Google Gemini fallback failed: {gemini_exc}. Falling back to local offline MockProvider.")

        # Ultimate safety fallback: MockProvider
        logger.warning("[AIProviderRouter] Falling back to offline deterministic MockProvider.")
        return await self.mock.generate_response(messages, tools_schema)


ai_provider_router = AIProviderRouter()


def get_ai_provider(provider_type: Optional[str] = None) -> AIProvider:
    """Factory function to instantiate the configured AI Provider.
    
    Defaults to the safe AIProviderRouter (Astra Primary -> Gemini Fallback -> Mock Offline).
    """
    settings = get_settings()
    primary = getattr(settings, "AI_PRIMARY_PROVIDER", "astra")
    selected = (provider_type or primary or settings.AI_PROVIDER).lower()

    if selected in ["astra", "openai", "router", "default"]:
        return ai_provider_router
    elif selected in ["gemini", "google"]:
        return GeminiProvider(settings=settings)
    elif selected == "openrouter":
        return OpenRouterProvider(settings=settings)
    elif selected == "mock":
        return MockProvider(settings=settings)
    else:
        return ai_provider_router


class FallbackProvider(AIProvider):
    """Resilient provider wrapping primary and secondary with mock fallback."""

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
    reasoning / code / multi-step planning to Astra Primary (with Gemini Fallback).
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.ai_router = ai_provider_router
        self.mock = MockProvider(self.settings)

    def route_provider(self, query: str) -> AIProvider:
        """Select the best AI provider for the given user prompt."""
        q = query.lower().strip()

        # Simple commands & app launches -> Fast Mock/Local execution to avoid unnecessary cloud API latency
        from backend.tools.app_tools import app_registry
        fast_keywords = ["time kya hai", "current time", "what time", "battery", "storage", "volume", "mute", "scroll", "minimize", "maximize", "open", "kholo", "launch"]
        if any(w in q for w in fast_keywords) or app_registry.resolve_app(q) is not None:
            return self.mock

        # Primary route: AIProviderRouter (Astra Primary + Gemini Standby Fallback + Mock Offline)
        return self.ai_router


model_router = ModelRouter()
