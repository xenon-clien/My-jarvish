# =====================================================================
# JARVIS ERROR HANDLING, CODE CONFLICTS & CONCURRENCY AUDIT
# =====================================================================

This report details exception handling policies, swallowed errors, race conditions, namespace collisions, and legacy code conflicts across the codebase.

## 1. Exception Handling & Swallowed Errors
### Patterns Identified in Source Code:
1. **Defensive Window Enumeration Swallowing**:
   - File: `backend/tools/ui_automation.py` & `backend/tools/browser_tools.py`
   - Pattern: `try: win32gui.GetWindowText(hwnd) except Exception: pass`
   - Evaluation: **ACCEPTABLE**. Windows frequently terminates temporary background windows during enumeration, producing transient Win32 invalid handle errors that should be ignored.
2. **Audio Callback Stream Status Handling**:
   - File: `backend/voice/speech_to_text.py`
   - Pattern: `if status: logger.debug(f"Audio stream status: {status}")`
   - Evaluation: **ACCEPTABLE**. Non-fatal buffer overflows/underflows are logged without terminating the main listening thread.
3. **Tool Execution Boundaries**:
   - File: `backend/tools/registry.py` (`BaseTool.execute()`)
   - Pattern: Catches `ValidationError`, `asyncio.TimeoutError`, and generic `Exception`, packaging them into structured `ToolResult(success=False, error=...)`.
   - Evaluation: **EXCELLENT**. Errors are never swallowed; they are preserved for diagnostics and voice feedback.

---

## 2. Concurrency & Race Conditions
1. **TTS vs STT Audio Recapture (Self-Listening Feedback Loop)**:
   - *Risk*: When JARVIS speaks, the microphone can hear the laptop speakers and interpret JARVIS's own words as a user command.
   - *Mitigation*: In `speech_to_text.py` line 125, `tts_manager.is_speaking()` check aborts listening during TTS playback.
2. **Consecutive Key Dispatch Collisions**:
   - *Risk*: Rapidly pressing "Next Short" can send `VK_DOWN` events before the browser DOM finishes scrolling to the next video.
   - *Mitigation*: Bounded sleep intervals (`time.sleep(0.04)`) between key down and key up events ensure Windows message pump processes each scan code cleanly.

---

## 3. Legacy vs New Code Conflicts
1. **Parallel Codebase (`3.0/`)**:
   - Directory `3.0/` contains a complete separate architecture with its own `main.py`, `core/`, `ai/`, `engine/`, and `tests/`.
   - **Conflict**: It is NOT imported or called by `scripts/voice_cli.py` or `backend/main.py`. It exists as an orphaned prototype that creates developer confusion.
2. **Plugin Subsystem vs Direct Tool Registry**:
   - `backend/plugins/` (`browser_plugin.py`, `media_plugin.py`, `youtube_plugin.py`) duplicates capabilities already present in `backend/tools/` (`browser_tools.py`, `media_tools.py`).
   - **Resolution Required**: Standardize on `backend/tools/` as the single authoritative tool layer.
