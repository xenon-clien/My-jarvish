@echo off
cd /d "%~dp0"

set "PATH=C:\Python314;C:\Python314\Scripts;%PATH%"
set JARVIS_DEV_SAFE_MODE=0
set JARVIS_ALLOW_LIVE_BROWSER_AUTOMATION=1
set JARVIS_ALLOW_PHYSICAL_INPUT=0

if exist "C:\Python314\pythonw.exe" (
    start "" "C:\Python314\pythonw.exe" app.py
) else (
    start "" pythonw.exe app.py
)
exit
