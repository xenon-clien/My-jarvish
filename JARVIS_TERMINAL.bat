@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
title J.A.R.V.I.S. High-Speed AI Terminal
color 0a
cls
cd /d "%~dp0"
python scripts/voice_cli.py
pause
