@echo off
setlocal
cd /d "%~dp0"
python -m compileall jarvis
python -m pytest -q
pause
