@echo off
title J.A.R.V.I.S. AI Assistant
cd /d "C:\Users\shivam\Downloads\chatbot"
start /b "" python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
python scripts\voice_cli.py
pause
