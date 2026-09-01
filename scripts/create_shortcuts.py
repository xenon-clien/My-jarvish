"""Creates 1-Click Desktop and Windows Auto-Startup Shortcuts for JARVIS AI."""
import os
from pathlib import Path
import win32com.client


def create_shortcuts():
    """Create Desktop and Windows Startup shortcuts."""
    shell = win32com.client.Dispatch("WScript.Shell")

    project_dir = str(Path(__file__).parent.parent.resolve())
    bat_path = os.path.join(project_dir, "JARVIS.bat")

    # 1. Desktop Shortcut
    desktop_dir = shell.SpecialFolders("Desktop")
    desktop_shortcut_path = os.path.join(desktop_dir, "JARVIS AI.lnk")
    shortcut = shell.CreateShortcut(desktop_shortcut_path)
    shortcut.TargetPath = bat_path
    shortcut.WorkingDirectory = project_dir
    shortcut.Description = "Launch JARVIS Voice AI Assistant"
    shortcut.Save()
    print(f"[OK] Created Desktop Shortcut: {desktop_shortcut_path}")

    # 2. Windows Startup Shortcut (auto-starts on laptop boot / opening)
    startup_dir = shell.SpecialFolders("Startup")
    startup_shortcut_path = os.path.join(startup_dir, "JARVIS AI.lnk")
    startup_shortcut = shell.CreateShortcut(startup_shortcut_path)
    startup_shortcut.TargetPath = bat_path
    startup_shortcut.WorkingDirectory = project_dir
    startup_shortcut.Description = "Auto-start JARVIS on Windows Boot"
    startup_shortcut.Save()
    print(f"[OK] Created Windows Auto-Start Shortcut: {startup_shortcut_path}")


if __name__ == "__main__":
    create_shortcuts()
