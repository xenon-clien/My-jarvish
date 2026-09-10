@echo off
setlocal
cd /d "%~dp0"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env

echo.
echo Setup complete.
echo Edit .env and add API keys if required, then run JARVIS.bat
echo.
pause
