# =====================================================================
# JARVIS DEPENDENCY GRAPH & SYSTEM COUPLING AUDIT
# =====================================================================

This document analyzes the structural dependencies, module couplings, and single points of failure across the JARVIS architecture.

## 1. System Dependency Architecture
```mermaid
graph TD
    subgraph UI_And_Entrypoints
        VCLI[scripts/voice_cli.py]
        CLI[scripts/cli.py]
        API[backend/main.py]
    end

    subgraph Audio_Pipeline
        SD[sounddevice Hardware Stream] --> STT[backend/voice/speech_to_text.py]
        TTS[backend/voice/text_to_speech.py] --> EDGE[edge_tts / pyttsx3]
    end

    subgraph NLU_And_Routing
        TRANS[backend/nlu/translator.py]
        NORM[backend/nlu/normalizer.py]
        SEM[backend/nlu/semantic_engine.py]
        ROUTER[backend/nlu/router.py]
    end

    subgraph AI_Core
        AGENT[backend/ai/agent.py]
        PROV[backend/ai/providers.py]
        GEMINI[Google Gemini API]
    end

    subgraph Diagnostics_And_Safety
        DIAG[backend/diagnostics/engine.py]
        NEMO[backend/diagnostics/nemotron_debugger.py]
        OPENROUTER[NVIDIA Nemotron 3.5]
    end

    subgraph Tool_Execution
        TREG[backend/tools/registry.py]
        BTOOLS[backend/tools/browser_tools.py]
        MTOOLS[backend/tools/media_tools.py]
        STOOLS[backend/tools/system_tools.py]
        FTOOLS[backend/tools/file_tools.py]
        WTOOLS[backend/tools/whatsapp_tools.py]
        UIAUTO[backend/tools/ui_automation.py]
    end

    subgraph OS_Layer
        WIN32[ctypes / win32gui / win32process]
        CHROME[Google Chrome / YouTube]
        WHATSAPP[WhatsApp Desktop]
        SHELL[Windows OS / PowerShell]
    end

    VCLI --> STT
    STT --> TRANS --> NORM --> SEM
    SEM --> ROUTER
    SEM -.->|Confidence < 0.65| AGENT
    AGENT --> PROV --> GEMINI
    PROV --> TREG
    ROUTER --> TREG
    TREG --> BTOOLS & MTOOLS & STOOLS & FTOOLS & WTOOLS & UIAUTO
    BTOOLS & MTOOLS & STOOLS & FTOOLS & WTOOLS & UIAUTO --> WIN32
    WIN32 --> CHROME & WHATSAPP & SHELL
    TREG -.->|Failure Event| DIAG
    DIAG --> NEMO --> OPENROUTER
    ROUTER --> TTS
```

---

## 2. Single Points of Failure (SPOF)
1. **Audio Device Initialization (`sounddevice`)**:
   - `speech_to_text.py` connects directly to Windows WASAPI audio input. If another app claims exclusive mode or sample rate changes, voice capture fails entirely.
2. **Foreground Window Active Focus (`win32gui`)**:
   - Browser and media tools rely on `force_foreground_window(hwnd)`. If Windows UIPI (User Interface Privilege Isolation) prevents thread attachment, keyboard shortcuts fail.
3. **Global Tool Registry State (`default_registry`)**:
   - All tools register to a single in-memory instance `default_registry`. Any runtime mutation or unhandled exception during registration affects all subsequent tool calls.
4. **Internet Connectivity for Primary Brain & Speech**:
   - Google Speech API and Gemini API require continuous WAN connectivity. Offline mode gracefully falls back to SAPI5 TTS and regex routing.

---

## 3. High Coupling Hotspots
- `backend/tools/browser_tools.py` $\leftrightarrow$ `backend/tools/media_tools.py`: Both implement overlapping YouTube playback functions (`click_screen_video` vs `control_media`).
- `backend/nlu/semantic_engine.py` $\leftrightarrow$ `backend/nlu/router.py`: Tight coupling where intent enums must be identically synchronized across both files.
