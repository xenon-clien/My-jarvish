"""Install JARVIS Clap-To-Wake to Windows Startup Folder.

Ensures that even after laptop shutdown or reboot, the background double-clap
listener automatically boots with Windows.
"""
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
vbs_source = os.path.join(BASE_DIR, "scripts", "start_jarvis_background.vbs")

startup_folder = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
dest_file = os.path.join(startup_folder, "JARVIS_ClapListener.vbs")

def install_startup():
    print(f"Installing JARVIS Autostart to: {dest_file}")
    try:
        shutil.copyfile(vbs_source, dest_file)
        print("✅ SUCCESS: JARVIS Clap-To-Wake registered in Windows Startup Folder!")
        print("Whenever laptop restarts/boots after shutdown, Clap-To-Wake will start automatically in background.")
        return True
    except Exception as e:
        print(f"❌ Failed to install startup shortcut: {e}")
        return False

if __name__ == "__main__":
    install_startup()
