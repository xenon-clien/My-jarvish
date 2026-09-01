# ⚡ J.A.R.V.I.S. Personal AI Assistant for Windows

An intelligent, modular, voice-controlled, safe AI agent system built in Python for Windows 10/11.

---

## 🌟 Key Features (Phase 1)
- **Modular Architecture**: Clean separation between AI Brain, Tool Registry, Permission Engine, Security Boundary, and API/CLI interfaces.
- **Strict 4-Tier Permission System**: Ensures dangerous and sensitive operations (e.g. file deletion, external communication) are never executed silently without explicit confirmation.
- **Pluggable AI Providers**: Unified `AIProvider` abstraction supporting `Mock` (zero-API-key offline testing), with `Gemini`, `OpenAI`, and `Ollama` support.
- **Safe Sandboxed Tools**: Built-in Pydantic validation, execution timeouts, error boundaries, and path restrictions.
- **FastAPI Backend & Interactive Rich CLI**: High-performance REST API with automatic Swagger docs (`/docs`) and a colorized terminal client.

---

## 🏗️ Project Architecture

```
c:\Users\shivam\Downloads\chatbot\
├── backend/
│   ├── app/
│   ├── core/           # Config (Pydantic), Logger (Sanitized), Permissions, Security
│   ├── ai/             # Agent orchestrator, Pluggable Providers, Prompts
│   ├── tools/          # Tool Registry, Decorators, System Diagnostic Tools
│   ├── database/       # SQLite Connection & Table Schemas
│   ├── api/            # FastAPI Endpoints (/health, /api/chat, /api/tools)
│   └── main.py         # Application Entrypoint
├── scripts/
│   └── cli.py          # Interactive Terminal Assistant
├── tests/              # Automated Test Suite (Pytest)
├── .env.example        # Environment variable template
├── requirements.txt    # Project dependencies
└── README.md
```

---

## 🚀 Quickstart Guide

### 1. Install Dependencies
In PowerShell inside the project directory:
```powershell
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` (a ready-to-run default `.env` is already provided):
```powershell
Copy-Item .env.example .env
```

### 3. Run Automated Tests
```powershell
python -m pytest tests/ -v
```

### 4. Start the Interactive CLI Assistant
```powershell
python scripts/cli.py
```

### 5. Start the FastAPI Server & Swagger UI
```powershell
python -m uvicorn backend.main:app --reload --port 8000
```
Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) in your browser to test interactive API calls.

---

## 🛡️ Permission Levels
- **Level 0 (Safe)**: Read-only diagnostics (Time, System specs, Health).
- **Level 1 (Normal Computer)**: Opening allowed applications, creating folders, moving files.
- **Level 2 (Communication)**: Sending WhatsApp/Telegram messages, sending emails.
- **Level 3 (Destructive/Sensitive)**: Deleting files, modifying security/system settings. Always prompts for user confirmation.
