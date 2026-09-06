# NVIDIA Nemotron & OpenRouter Removal & Decoupling Report
## Decoupling Normal AI Runtime from NVIDIA Nemotron / OpenRouter

**Date**: 2026-09-06  
**Status**: COMPLETE & VERIFIED  
**Objective**: Remove NVIDIA Nemotron and OpenRouter from normal runtime, primary conversational routing, and diagnostic flows.  

---

## 1. Executive Summary

Prior to this migration, OpenRouter and NVIDIA Nemotron (`nvidia/nemotron-3.5-lightning:free`) were embedded in two distinct areas of JARVIS:
1. As a secondary fallback provider in `ModelRouter` in `backend/ai/providers.py`.
2. As a diagnostic code debugger in `backend/diagnostics/nemotron_debugger.py`.

Per engineering requirements, NVIDIA Nemotron and OpenRouter have been removed/disabled from normal AI stack operations without breaking existing import interfaces.

---

## 2. Changes Applied by File

### 2.1 Configuration (`backend/core/config.py` & `.env`)
- `NEMOTRON_ENABLED` set to `False` by default.
- `NEMOTRON_DEBUG_ONLY` set to `False`.
- `OPENROUTER_API_KEY` marked as deprecated / optional.
- Production authority now points strictly to `AI_PRIMARY_PROVIDER="astra"` and `AI_FALLBACK_PROVIDER="gemini"`.

### 2.2 Provider Abstraction Layer (`backend/ai/providers.py`)
- Removed `OpenRouterProvider` from the normal resolution path of `get_ai_provider()`.
- `ModelRouter` now routes complex reasoning and conversation directly through `AIProviderRouter` (Astra -> Gemini -> Mock).
- `OpenRouterProvider` and `FallbackProvider` classes are retained strictly for backward compatibility with external legacy scripts, but are not invoked during normal assistant execution.

### 2.3 Diagnostic Subsystem (`backend/diagnostics/nemotron_debugger.py`)
- Decoupled `NemotronDebugger` from mandatory OpenRouter HTTP calls.
- When `nemotron_guard.canUseNemotron()` returns `(False, "DISABLED")`, the debugger automatically delegates diagnostic analysis to `AIProviderRouter` (`get_ai_provider()`) or local empirical rule diagnostics.
- External calls to `https://openrouter.ai/api/v1/chat/completions` are completely eliminated from normal runtime.

### 2.4 Diagnostic Usage Guard (`backend/diagnostics/nemotron_guard.py`)
- Inactive in production (`self.enabled == False`).
- Retained to prevent accidental billing and enforce 100% free-tier safety should the module ever be queried.

### 2.5 Developer CLI & Observability (`scripts/voice_cli.py`)
- Updated `/ai-status` and added `/provider status` to present the authoritative two-tier architecture:
  - **Primary Brain**: OpenAI GPT-6 Astra (`gpt-6-astra`)
  - **Standby Fallback**: Google Gemini (`gemini-3.5-flash-lite`)
  - **NVIDIA Nemotron / OpenRouter**: Marked as `DISABLED from normal runtime (Decoupled)`.

---

## 3. Dependency & Regression Safety Audit

- **Imports Checked**: All modules importing `backend.diagnostics.nemotron_debugger` or `backend.ai.providers` continue to load cleanly with zero `ImportError` or `AttributeError`.
- **Runtime Dependency**: JARVIS no longer requires an `OPENROUTER_API_KEY` to boot, operate, or run self-diagnostics.
- **Cost Safety**: Zero external OpenRouter requests are dispatched during ordinary operation or error handling.
