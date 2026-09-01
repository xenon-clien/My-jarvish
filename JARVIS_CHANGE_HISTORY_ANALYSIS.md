# =====================================================================
# JARVIS CHANGE HISTORY & ARCHITECTURAL EVOLUTION ANALYSIS
# =====================================================================

This report documents the architectural history, evolutionary stages, and root causes of regressions in the JARVIS project.

## 1. Git Repository Status
- **Finding**: No active `.git` repository directory was detected in the root project folder (`fatal: not a git repository`).
- **Evolutionary Timeline Reconstruction**: The project's change history has been reconstructed from directory structures, legacy module artifacts, and commit traces across `backend/`, `3.0/`, `scripts/`, and root batch files.

---

## 2. Architectural Evolution Phases
### Phase 1: Script-Based Automation Prototype (Root Files)
- Early iterations relied on flat Python scripts in the root directory (`test_mic_engine.py`, `check_browser_geometry.py`, `inspect_live_whatsapp.py`).
- Automation was driven by direct screen pixel coordinates and raw hotkey scripts (`scripts/hotkey_listener.py`).

### Phase 2: Modular Enterprise Architecture (`backend/`)
- Transitioned to structured packages: `backend/core/`, `backend/nlu/`, `backend/tools/`, `backend/voice/`, `backend/adapters/`.
- Introduced formal Pydantic argument schemas, permission levels, and structured JSON logging.
- Deployed native 16kHz mono audio streaming and Edge-TTS neural speech synthesis.

### Phase 3: The 152-App Expansion & Collision Emergence
- Prompts were issued to expand JARVIS across 152 applications simultaneously.
- As broad regex patterns were added to `semantic_engine.py`, command overlap occurred ("play first short" colliding with media, downloads, or generic window switches).
- Diagnostic subsystems (`backend/diagnostics/nemotron_debugger.py`) were introduced to analyze runtime failures.

### Phase 4: Deterministic Hardening & The Experimental `3.0/` Fork
- Introduced `EXACT_MAP` (147 phrases) in `semantic_engine.py` to guarantee zero-latency deterministic execution for frequent commands.
- A parallel rewrite was initiated in `3.0/` with domain routers and task queues, but remained disconnected from the active voice CLI runtime.

---

## 3. Why Regressions Occur During Bulk Feature Prompts
1. **Shared Monolithic Regex Pollution**: Modifying regex clusters to support new apps alters matching boundaries for previously working apps.
2. **Lack of Automated Hardware Mocking in Tests**: Because hardware tests hang during bulk execution, developers and AI agents skip running regression suites before declaring features complete.
3. **Screen Geometry Shifts**: Coordinate percentages calibrated on one monitor break when tested on different window sizes or scaled desktop displays.
