@echo off
setlocal
cd /d "%~dp0"
python -m jarvis.main --text
pause
