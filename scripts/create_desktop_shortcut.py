"""Create Desktop Shortcut and Windows Startup Auto-Launcher for JARVIS."""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
desktop_dir = os.path.expandvars(r"%USERPROFILE%\Desktop")
startup_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")

# 1. Create a dedicated launcher batch script
bat_path = os.path.join(BASE_DIR, "run_jarvis.bat")
with open(bat_path, "w", encoding="utf-8") as f:
    f.write(f"""@echo off
title J.A.R.V.I.S. AI Assistant
cd /d "{BASE_DIR}"
start /b "" python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
python scripts\\voice_cli.py
pause
""")

print(f"Created: {bat_path}")

# 2. Create Windows Shortcut (.lnk) on Desktop with Hotkey Ctrl+Alt+J via PowerShell
ps_script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{desktop_dir}\\JARVIS.lnk')
$Shortcut.TargetPath = '{bat_path}'
$Shortcut.WorkingDirectory = '{BASE_DIR}'
$Shortcut.Description = 'JARVIS Dual-AI Assistant'
$Shortcut.Hotkey = 'Ctrl+Alt+J'
$Shortcut.Save()

$StartupShortcut = $WshShell.CreateShortcut('{startup_dir}\\JARVIS_AutoLaunch.lnk')
$StartupShortcut.TargetPath = '{bat_path}'
$StartupShortcut.WorkingDirectory = '{BASE_DIR}'
$StartupShortcut.Description = 'JARVIS Dual-AI AutoStart'
$StartupShortcut.Save()
"""

import subprocess
subprocess.run(["powershell", "-Command", ps_script], check=True)
print("✅ Desktop Shortcut 'JARVIS.lnk' created with Hotkey [Ctrl + Alt + J]!")
print("✅ Windows Startup Shortcut 'JARVIS_AutoLaunch.lnk' installed in Startup folder!")
