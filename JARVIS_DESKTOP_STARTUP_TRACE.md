# =====================================================================
# JARVIS DESKTOP STARTUP TRACE
# =====================================================================

## Entrypoint Mapping
| Launcher File | Command Executed | Target File | Execution Mode | Voice Engine Initialized |
|---|---|---|:---:|:---:|
| `JARVIS.bat` | `python scripts/voice_cli.py` | `scripts/voice_cli.py` | Foreground Console | YES (Main Thread) |
| `START_JARVIS_APP.bat` | `pythonw.exe app.py` | `app.py` | GUI (PyWebView) | YES (Daemon Thread) |
| `JARVIS.vbs` | `WshShell.Run "pythonw.exe app.py"` | `app.py` | GUI (Hidden CMD) | YES (Daemon Thread) |
| `run_jarvis.bat` | `uvicorn backend.main:app & python scripts\voice_cli.py` | `scripts/voice_cli.py` | Dual Server + CLI | YES (Main Thread) |

---

## Startup Environment Checks
- **Working Directory**: `c:\Users\shivam\Downloads\chatbot`
- **Python Executable**: `C:\Python314\python.exe`
- **Environment Flags**: `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1`
- **Encoding Status**: UTF-8 Console Code Page 65001 Verified.
