# JARVIS YouTube Authoritative Production Path Trace

## 1. End-to-End Pipeline Architecture
The active production runtime pipeline follows an explicit, observable execution path from user audio input to verified desktop state:

```
[Real Microphone / Audio Input]
               │
               ▼
[Speech-To-Text (stt_manager)]
  backend/voice/speech_to_text.py
               │
               ▼
[Universal Language Translation & Normalization]
  backend/voice/translator.py -> backend/voice/normalizer.py
               │
               ▼
[CommandProcessor Application Context Resolution]
  backend/core/command_processor.py:resolve_application_context()
               │
               ├──> [Disabled App Interception] -> Return "App automation is not enabled..."
               │
               ▼
[Canonical YouTube NLU Parsing]
  backend/nlu/youtube_nlu.py:UniversalYouTubeNLU.parse()
               │
               ├──> Confidence >= 0.85 & Valid Intent
               │         │
               │         ▼
               │    [Authoritative Execution Owner]
               │      backend/adapters/youtube_adapter.py:execute_canonical()
               │         │
               │         ├──> [Dynamic Grounding & Element Discovery]
               │         │      backend/adapters/youtube_grounding.py:youtube_page_observer
               │         │
               │         ├──> [Low-Level Windows Primitives]
               │         │      backend/tools/browser_tools.py (URL navigation, foreground focus)
               │         │      backend/tools/media_tools.py (Hardware media keystrokes)
               │         │
               │         ▼
               │    [Closed-Loop State Verifier]
               │      backend/adapters/youtube_adapter.py:verify_state()
               │
               ▼ (Ambiguous / Generative Fallback)
[Scoped AI Agent Reasoning (Astra / Gemini Fallback)]
  backend/ai/agent.py:JarvisAgent.process_user_input()
  (Exposes ONLY youtube.* canonical tools + system info)
               │
               ▼
[Audio / Spoken Acknowledgement & Command Trace Record]
  backend/voice/text_to_speech.py -> backend/observability/command_tracer.py
```

---

## 2. Component Responsibility Matrix

| Component | Source File | Authoritative Responsibility |
|---|---|---|
| **STT Engine** | `backend/voice/speech_to_text.py` | Audio capture, VAD framing, Whisper transcription |
| **Normalizer** | `backend/voice/normalizer.py` | Devanagari transliteration, phonetic normalization, number extraction |
| **Command Processor** | `backend/core/command_processor.py` | Application context precedence, allowlist enforcement, task routing |
| **YouTube NLU** | `backend/nlu/youtube_nlu.py` | 1-based ordinal extraction, entity parsing, slot normalization |
| **Single Execution Owner** | `backend/adapters/youtube_adapter.py` | Authoritative business logic, task locking, verification dispatcher |
| **Page Observer & Grounding** | `backend/adapters/youtube_grounding.py` | UIA Omnibox URL extraction, desktop attachment, candidate discovery |
| **Browser Primitives** | `backend/tools/browser_tools.py` | Low-level in-place tab navigation, foreground window management |
| **Media Primitives** | `backend/tools/media_tools.py` | Hardware key dispatch (VK_MEDIA_PLAY_PAUSE, VK_DOWN, VK_UP, VK_F) |
| **AI Brain Provider** | `backend/ai/providers.py` | OpenAI GPT-6 Astra primary with Google Gemini fallback |
