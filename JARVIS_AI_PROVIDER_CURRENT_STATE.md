# JARVIS AI Provider Architecture — Current State Forensic Audit

**Date**: 2026-09-06  
**Status**: AUDITED & BASELINE CHECKPOINT ESTABLISHED  
**Baseline Git Tag**: `pre-astra-provider-migration` (`4e8dbb81dc7afb53a2ed776279c7b6591275161c`)  
**Repository**: `c:\Users\shivam\Downloads\chatbot`

---

## 1. Executive Summary

Prior to this migration, JARVIS operated on a fragmented AI model configuration:
- **Primary Brain**: Google Gemini (`gemini-3.5-flash-lite`) invoked via direct REST calls to `https://generativelanguage.googleapis.com/v1beta`.
- **Secondary Provider**: OpenRouter calling `nvidia/nemotron-3.5-lightning:free` via `https://openrouter.ai/api/v1/chat/completions`.
- **Diagnostic Specialist**: NVIDIA Nemotron (`nvidia/nemotron-3.5-lightning:free`) tied directly to OpenRouter in `backend/diagnostics/nemotron_debugger.py` and guarded by `backend/diagnostics/nemotron_guard.py`.
- **Offline Fallback**: `MockProvider` in `backend/ai/providers.py` for deterministic offline rule execution.

This audit details all call sites, configurations, runtime paths, and dependencies prior to introducing **OpenAI GPT-6 Astra** (`gpt-6-astra`) as the primary brain with **Google Gemini** as automatic standby fallback.

---

## 2. Configuration & Environment Variables Audit

### 2.1 Settings in `backend/core/config.py`
```python
# AI Brain Provider (Google Gemini Primary Brain)
AI_PROVIDER: str = "gemini"
AI_API_KEY: str = ""
AI_MODEL: str = "gemini-3.5-flash-lite"

# OpenRouter & NVIDIA Nemotron Debugger Settings
OPENROUTER_API_KEY: str = ""
OPENROUTER_MODEL: str = "nvidia/nemotron-3.5-lightning:free"
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
OPENROUTER_MAX_TOKENS: int = 2048
NEMOTRON_MODEL: str = "nvidia/nemotron-3.5-lightning:free"
NEMOTRON_ENABLED: bool = True
NEMOTRON_DEBUG_ONLY: bool = True
NEMOTRON_MAX_FREE_REQUESTS_PER_DAY: int = 45
NEMOTRON_WARNING_THRESHOLD: int = 40
```

### 2.2 Active `.env` Keys
- `AI_PROVIDER=gemini`
- `AI_API_KEY=<configured>`
- `AI_MODEL=gemini-3.5-flash-lite`
- `OPENROUTER_API_KEY=<configured>`
- `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`
- `NEMOTRON_MODEL=nvidia/nemotron-3.5-lightning:free`
- `NEMOTRON_ENABLED=True`
- Missing: `ASTRA_API_KEY`, `ASTRA_MODEL`, `ASTRA_BASE_URL`, `OPENAI_API_KEY`.

---

## 3. Provider Call Sites & Routing Topology

### 3.1 `backend/ai/providers.py`
1. **`AIProvider` (Abstract Base Class)**:
   - Defines `generate_response(messages, tools_schema) -> BaseAIResponse`.
2. **`OpenRouterProvider`**:
   - Calls `https://openrouter.ai/api/v1/chat/completions`.
   - Used OpenRouter API key and Nemotron or Gemini model.
   - On HTTP 429, fell back directly to `MockProvider`.
3. **`GeminiProvider`**:
   - Direct Google Generative Language API call (`/v1beta/models/{model}:generateContent`).
   - Translates messages to Gemini format (`contents`, `systemInstruction`, `function_declarations`).
   - Implemented transient rate-limiting backoff (`_rate_limit_until`).
4. **`FallbackProvider`**:
   - Simple try-except wrapper between primary and secondary providers.
5. **`ModelRouter`**:
   - Routes simple intents to `MockProvider` and reasoning to `FallbackProvider(Gemini, OpenRouter)`.
6. **`get_ai_provider()` Factory**:
   - Resolved `AI_PROVIDER` to `GeminiProvider`, `OpenRouterProvider`, or `MockProvider`.

### 3.2 `backend/ai/agent.py`
- Line 64: `self.provider = provider or get_ai_provider()`.
- Line 252: `ai_response = await self.provider.generate_response(messages, tools_schema=tools_schemas)`.
- Line 256-261: If provider throws an uncaught exception, falls back to `MockProvider`.

### 3.3 `backend/diagnostics/nemotron_debugger.py`
- Line 40-42: Initialized with `OPENROUTER_API_KEY` and `nvidia/nemotron-3.5-lightning:free`.
- Line 142: Directly posted to `https://openrouter.ai/api/v1/chat/completions`.
- Coupled diagnosis strictly to OpenRouter.

### 3.4 `backend/diagnostics/nemotron_guard.py`
- Enforced hard cap of 45 requests/day on Nemotron free tier.
- Persisted counter to `logs/diagnostics/nemotron_quota.json`.
- Trapped HTTP 429 from OpenRouter to disable Nemotron calls.

### 3.5 `scripts/voice_cli.py`
- Line 220-237: `/ai-status` displayed Gemini as Primary Brain and Nemotron as Debugger.
- Line 291-316: Commands `/nemotron-status`, `/nemotron-enable`, `/nemotron-disable`.

---

## 4. Gap Analysis & Architecture Deficiencies

1. **No OpenAI / Astra Gateway Support**:
   - System lacked support for Astra's Experiential Labs gateway (`https://api.experientiallabs.ai/v1`) and model `gpt-6-astra`.
2. **Brittle Rate Limit Handling (429 Misclassification)**:
   - Previous logic treated all 429 errors as generic rate limits or instant failure, without discriminating between transient concurrency spikes vs actual quota/subscription exhaustion.
3. **Absence of State Persistence for Quota Failures**:
   - If an upstream quota was exhausted, subsequent requests would still hit the API and fail repeatedly, causing unnecessary latency on every user query.
4. **Tight Coupling to OpenRouter**:
   - Diagnostics and fallback were tied to OpenRouter, introducing external dependencies that are no longer desired.
5. **Missing Explicit Circuit Breaker & Administrative Reset**:
   - No structured `/provider reset astra` command existed to restore degraded or disabled providers after quota renewal.

---

## 5. Migration Strategy Roadmap

1. **Introduce `AstraProvider`**:
   - Connects to `https://api.experientiallabs.ai/v1/chat/completions` using the provided Astra key.
   - Configured for model `gpt-6-astra`.
   - Full tool calling (schema mapping and parsing).
2. **Implement `AIProviderRouter` with Safe Failover & Circuit Breaker**:
   - Astra (Primary) -> Gemini (Fallback) -> Mock (Offline).
   - Error classification engine (Category A, B, C, D).
   - Quota exhaustion persistence in `logs/ai/astra_state.json`.
   - Zero-call bypass on subsequent requests when quota is exhausted.
   - Developer command `/provider reset astra` for administrative recovery.
3. **Decouple Nemotron / OpenRouter**:
   - Disable Nemotron from normal runtime.
   - Retain Gemini intact as production fallback.
4. **Verify with Comprehensive Automated Test Suite**:
   - Unit tests covering all failover scenarios, including the mandatory zero-call quota bypass test.
