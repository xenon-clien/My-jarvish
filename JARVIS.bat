@echo off
cd /d "%~dp0"

set JARVIS_DEV_SAFE_MODE=0
set JARVIS_ALLOW_LIVE_BROWSER_AUTOMATION=1
set JARVIS_ALLOW_PHYSICAL_INPUT=0

start "" pythonw app.py
exit
