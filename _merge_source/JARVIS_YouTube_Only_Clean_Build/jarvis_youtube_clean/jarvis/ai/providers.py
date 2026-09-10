from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

import httpx

from jarvis.config import settings


@dataclass
class ProviderReply:
    success: bool
    provider: str
    model: str
    text: str = ""
    error_type: str | None = None
    error_message: str | None = None
    retryable: bool = False
    latency_ms: int = 0


class ProviderStateStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = Lock()

    def load(self) -> dict[str, Any]:
        with self._lock:
            if not self.path.exists():
                return {"astra": {"status": "AVAILABLE", "reason": None, "updated_at": None}}
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                return {"astra": {"status": "UNKNOWN", "reason": "state_file_unreadable", "updated_at": None}}

    def save(self, state: dict[str, Any]) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def set_astra(self, status: str, reason: str | None = None) -> None:
        state = self.load()
        state["astra"] = {"status": status, "reason": reason, "updated_at": int(time.time())}
        self.save(state)

    def reset_astra(self) -> None:
        self.set_astra("AVAILABLE", None)


STORE = ProviderStateStore(settings.data_dir / "provider_state.json")


def _classify(status: int | None, body: str) -> tuple[str, bool, bool]:
    """Return (error_type, retryable, persist_disable)."""
    msg = (body or "").lower()
    if any(x in msg for x in ["insufficient_quota", "quota exhausted", "credits exhausted", "billing hard limit", "free limit", "free tier limit"]):
        return "quota_exhausted", False, True
    if status in (401, 403) or any(x in msg for x in ["invalid api key", "authentication", "unauthorized", "access revoked", "not entitled"]):
        return "auth_or_access", False, True
    if status == 404 or any(x in msg for x in ["model_not_found", "model not found", "does not have access to model"]):
        return "model_access", False, True
    if status == 429:
        return "rate_limited", True, False
    if status is not None and status >= 500:
        return "server_error", True, False
    if status in (408,):
        return "timeout", True, False
    return "request_error", False, False


class AstraProvider:
    name = "experimental_labs_astra"

    def available_by_config(self) -> bool:
        return bool(settings.explabs_api_key and settings.explabs_base_url and settings.astra_model)

    def generate(self, system: str, user: str) -> ProviderReply:
        state = STORE.load().get("astra", {})
        if state.get("status") in {"DISABLED_QUOTA", "DISABLED_AUTH", "DISABLED_ACCESS"}:
            return ProviderReply(False, self.name, settings.astra_model, error_type="persistently_disabled", error_message=state.get("reason"))
        if not self.available_by_config():
            return ProviderReply(False, self.name, settings.astra_model, error_type="not_configured", error_message="EXPLABS_API_KEY is not configured")

        url = f"{settings.explabs_base_url}/chat/completions"
        payload = {
            "model": settings.astra_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
        }
        started = time.perf_counter()
        try:
            with httpx.Client(timeout=settings.request_timeout_s) as client:
                r = client.post(url, headers={"Authorization": f"Bearer {settings.explabs_api_key}", "Content-Type": "application/json"}, json=payload)
            latency = int((time.perf_counter() - started) * 1000)
            if r.is_success:
                data = r.json()
                text = data["choices"][0]["message"]["content"]
                return ProviderReply(True, self.name, settings.astra_model, text=text, latency_ms=latency)
            et, retryable, persist = _classify(r.status_code, r.text[:2000])
            if persist:
                STORE.set_astra("DISABLED_QUOTA" if et == "quota_exhausted" else "DISABLED_ACCESS", et)
            return ProviderReply(False, self.name, settings.astra_model, error_type=et, error_message=f"HTTP {r.status_code}", retryable=retryable, latency_ms=latency)
        except httpx.TimeoutException:
            return ProviderReply(False, self.name, settings.astra_model, error_type="timeout", error_message="request timeout", retryable=True, latency_ms=int((time.perf_counter()-started)*1000))
        except httpx.HTTPError as exc:
            return ProviderReply(False, self.name, settings.astra_model, error_type="network_error", error_message=type(exc).__name__, retryable=True, latency_ms=int((time.perf_counter()-started)*1000))
        except Exception as exc:
            return ProviderReply(False, self.name, settings.astra_model, error_type="provider_error", error_message=type(exc).__name__, retryable=False, latency_ms=int((time.perf_counter()-started)*1000))


class GeminiProvider:
    name = "gemini"

    def available_by_config(self) -> bool:
        return bool(settings.gemini_api_key and settings.gemini_model)

    def generate(self, system: str, user: str) -> ProviderReply:
        if not self.available_by_config():
            return ProviderReply(False, self.name, settings.gemini_model or "unconfigured", error_type="not_configured", error_message="Gemini fallback is not configured")
        model = settings.gemini_model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0},
        }
        started = time.perf_counter()
        try:
            with httpx.Client(timeout=settings.request_timeout_s) as client:
                r = client.post(url, params={"key": settings.gemini_api_key}, json=payload)
            latency = int((time.perf_counter() - started) * 1000)
            if r.is_success:
                data = r.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return ProviderReply(True, self.name, model, text=text, latency_ms=latency)
            et, retryable, _ = _classify(r.status_code, r.text[:2000])
            return ProviderReply(False, self.name, model, error_type=et, error_message=f"HTTP {r.status_code}", retryable=retryable, latency_ms=latency)
        except httpx.TimeoutException:
            return ProviderReply(False, self.name, model, error_type="timeout", error_message="request timeout", retryable=True, latency_ms=int((time.perf_counter()-started)*1000))
        except Exception as exc:
            return ProviderReply(False, self.name, model, error_type="provider_error", error_message=type(exc).__name__, retryable=False, latency_ms=int((time.perf_counter()-started)*1000))


class AIProviderRouter:
    def __init__(self):
        self.astra = AstraProvider()
        self.gemini = GeminiProvider()
        self.last_provider: str | None = None
        self.last_fallback_reason: str | None = None

    def generate(self, system: str, user: str) -> ProviderReply:
        first = self.astra.generate(system, user)
        if first.success:
            self.last_provider = first.provider
            self.last_fallback_reason = None
            return first
        self.last_fallback_reason = first.error_type
        second = self.gemini.generate(system, user)
        if second.success:
            self.last_provider = second.provider
        return second

    def status(self) -> dict[str, Any]:
        astra_state = STORE.load().get("astra", {})
        return {
            "primary": "experimental_labs_astra",
            "astra_model": settings.astra_model,
            "astra_state": astra_state,
            "fallback": "gemini",
            "gemini_model": settings.gemini_model or "not configured",
            "last_provider": self.last_provider,
            "last_fallback_reason": self.last_fallback_reason,
        }

    def reset_astra(self) -> None:
        STORE.reset_astra()
