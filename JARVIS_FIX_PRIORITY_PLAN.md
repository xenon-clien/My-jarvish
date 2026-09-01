# =====================================================================
# JARVIS FIX PRIORITY PLAN & ARCHITECTURAL ROADMAP
# =====================================================================

This document presents a structured, non-destructive, prioritized roadmap (P0 through P9) to achieve 100% industrial reliability across all JARVIS operations.

---

## Priority 0 (P0) — Clean Voice Pipeline & Single-Attempt Response
- **Goal**: Guarantee that user commands are captured on the very first attempt with $< 350	ext{ms}$ latency and zero shouting.
- **Actions**:
  1. Maintain Adaptive Delta VAD (`ambient_mean + 12.0 RMS`) and 30x AGC gain.
  2. Enforce instant first-result return across parallel STT threads (`en-IN` / `hi-IN`).
  3. Ensure TTS cooldown remains strictly $\le 0.10	ext{s}$ with instant speech interruption.

---

## Priority 1 (P1) — Domain-Scoped Deterministic Intent Routing
- **Goal**: Eliminate command misrouting and cross-app collisions permanently.
- **Actions**:
  1. Implement hierarchical routing: `Transcript -> Active Foreground App -> Domain Scope -> Intent -> Tool`.
  2. If Chrome/YouTube is in the foreground, route "next", "play", "3rd" strictly to `youtube.*`.
  3. If WhatsApp is in the foreground, route "call", "send" strictly to `whatsapp.*`.

---

## Priority 2 (P2) — Strict Tool Namespacing (`app.action`)
- **Goal**: Prevent flat global namespace pollution.
- **Actions**:
  1. Namespace all tools formally: `youtube.play`, `youtube.next_short`, `system.volume`, `whatsapp.call`, `files.find`.
  2. Disallow un-namespaced global verbs that create semantic ambiguity.

---

## Priority 3 (P3) — Dynamic Viewport & Accessibility Tree Grounding
- **Goal**: Completely eliminate brittle coordinate guessing.
- **Actions**:
  1. Use Windows UIAutomation (`uiautomation` / `pywinauto`) to bind directly to named UI element handles.
  2. For web players, rely strictly on native keyboard navigation (`VK_DOWN`, `VK_UP`, `VK_SPACE`, `Shift+N`) with center-player focus locks.

---

## Priority 4 (P4) — Two-Phase Execution & Verification Engine
- **Goal**: Guarantee that no tool reports "Success" without runtime verification.
- **Actions**:
  1. Implement `execute()` and `verify()` contracts across all tools.
  2. Verify window title changes, process existence, or audio playback before dispatching TTS confirmation.

---

## Priority 5 (P5) — Task Decomposition for Compound Multi-Step Commands
- **Goal**: Reliably execute compound commands ("Chrome kholo, YouTube kholo, first video chalao").
- **Actions**:
  1. Split compound utterances into sequential task pipelines: `Task 1 -> Task 2 -> Task 3`.
  2. Wait for each sub-task's verification before initiating the next step.

---

## Priority 6 (P6) — Tiered 152-App Integration Architecture
- **Goal**: Establish honest, reliable boundaries for all 152 applications.
- **Actions**:
  1. **Tier 1 (Dedicated Adapters)**: YouTube, WhatsApp, System (Full internal UI control).
  2. **Tier 2 (Common Tools)**: Chrome, Edge, VS Code, Spotify, File Explorer (Shortcuts + Process).
  3. **Tier 3 (Universal Process Control)**: All remaining ~145 apps (Launch, Focus, Close, Minimize, Maximize).
  4. Document capabilities honestly without creating fake stub functions.

---

## Priority 7 (P7) — Audio Hardware Test Mocking & Continuous Regression Suite
- **Goal**: Enable instantaneous 100% test suite execution on every code change.
- **Actions**:
  1. Add `unittest.mock` audio fixtures to `test_clap_detector.py` and `test_voice.py`.
  2. Ensure all 33 test files run in $< 5$ seconds via `pytest`.

---

## Priority 8 (P8) — Codebase Consolidation & Deprecation of Duplicate Trees
- **Goal**: Eliminate context confusion between `backend/` and `3.0/`.
- **Actions**:
  1. Migrate any valuable concepts from `3.0/` into `backend/`.
  2. Archive or cleanly deprecate `3.0/` so all developers and AI agents focus 100% on the production `backend/` tree.

---

## Priority 9 (P9) — Full Automated Self-Healing & Diagnostic Observability
- **Goal**: Allow JARVIS to automatically detect and report runtime anomalies.
- **Actions**:
  1. Maintain Nemotron 3.5 Lightning diagnostic engine gated by quota guards.
  2. Record structured JSONL failure bundles with Playwright traces on exceptions.
