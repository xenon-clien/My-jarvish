@echo off
title JARVIS CORE INTERFACE
cd /d "c:\Users\shivam\Downloads\chatbot"

set "PATH=C:\Python314;C:\Python314\Scripts;%PATH%"
set JARVIS_DEV_SAFE_MODE=0
set JARVIS_ALLOW_LIVE_BROWSER_AUTOMATION=1
set JARVIS_ALLOW_PHYSICAL_INPUT=0

if exist "C:\Python314\python.exe" (
    "C:\Python314\python.exe" app.py
) else (
    python app.py
)
exit
