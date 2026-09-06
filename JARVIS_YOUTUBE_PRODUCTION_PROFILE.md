# JARVIS YouTube-Only Production Profile

## 1. Executive Summary & Philosophy
JARVIS has been transitioned from an overly broad multi-app architecture (attempting to automate 152 desktop and web applications simultaneously) into a strictly focused, grounded, single-application production profile: **YOUTUBE ONLY**.

This architectural pivot ensures:
- **Zero Hallucination / Router Confusion**: LLMs and semantic parsers are not overwhelmed by hundreds of conflicting tools.
- **Single Execution Owner**: Business logic belongs exclusively to `YouTubeAdapter`.
- **Truthful Status Reporting**: Capabilities are backed by closed-loop state verification rather than assumed success.

---

## 2. Production Allowlist Configuration
The active production application allowlist is defined in `backend/core/config.py` within `Settings`:

```python
# Production Application Allowlist (Single-App Focus)
PRODUCTION_ENABLED_APPS: List[str] = ["youtube"]
```

### Preservation Policy (Zero Code Deletion)
In strict accordance with engineering safety constraints:
- Existing 152 application definitions in `backend/tools/app_tools.py` and `app_registry` were **NOT physically deleted**.
- Existing application adapters (e.g., `whatsapp_adapter.py`, `spotify_adapter.py`, `system_adapter.py`) remain in the codebase for future phased expansion.
- Applications outside `PRODUCTION_ENABLED_APPS` are strictly decoupled from active runtime tool exposure.

---

## 3. Tool Exposure & Provider Isolation Policy
When resolving any command in production:
- **Astra (GPT-6 Astra)** receives **ONLY** canonical `youtube.*` tools (and Gemini-safe underscore aliases) plus essential non-application system infrastructure (`get_current_time`, `get_system_status`, `get_battery_status`, `get_storage_status`, `get_network_status`).
- **Google Gemini Fallback** follows the exact same tool exposure policy.
- **Zero-Exposure Guarantee**: `whatsapp.*`, `spotify.*`, `vscode.*`, `find_files`, and the 152-app launching catalog are completely filtered out from LLM schema generation.
- **Provider Parity**: Changing the active AI provider from Astra to Gemini (or vice versa) results in **zero change** to the available tool schema.

---

## 4. Truthful Disabled Application Interception
When a user requests automation for an application outside the production allowlist, JARVIS intercepts the command deterministically in `backend/core/command_processor.py` and `backend/tools/app_tools.py`.

### User Interception Contract:
- Command: *"WhatsApp kholo"* / *"WhatsApp par message bhejo"*
  - Response: `"WhatsApp automation is not enabled in the current production profile."`
- Command: *"Spotify chalao"* / *"Play song on Spotify"*
  - Response: `"Spotify automation is not enabled in the current production profile."`
- Command: *"VS Code open karo"*
  - Response: `"VS Code automation is not enabled in the current production profile."`
- Execution Status: `VERIFIED_SUCCESS` (Clean, deterministic notice with zero random fallback).
