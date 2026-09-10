@echo off
setlocal
cd /d "%~dp0"

set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%LocalAppData%\Google\Chrome\Application\chrome.exe"

if not exist "%CHROME%" (
  echo Google Chrome was not found.
  echo Install Chrome or update JARVIS.bat with the correct path.
  pause
  exit /b 1
)

if not exist "%LocalAppData%\JARVIS\ChromeProfile" mkdir "%LocalAppData%\JARVIS\ChromeProfile"

start "JARVIS Chrome" "%CHROME%" --remote-debugging-port=9222 --user-data-dir="%LocalAppData%\JARVIS\ChromeProfile" --new-window https://www.youtube.com/

timeout /t 3 /nobreak >nul
python -m jarvis.main --voice

pause
