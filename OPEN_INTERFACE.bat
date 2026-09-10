@echo off
title JARVIS CORE INTERFACE
cd /d "c:\Users\shivam\Downloads\chatbot"

set JARVIS_DEV_SAFE_MODE=0
set JARVIS_ALLOW_LIVE_BROWSER_AUTOMATION=1
set JARVIS_ALLOW_PHYSICAL_INPUT=0

python app.py
exit
