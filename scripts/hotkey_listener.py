"""Native Windows Global Hotkey Daemon for JARVIS.

Uses Windows native user32.RegisterHotKey to provide guaranteed, zero-latency
global hotkey activation (Ctrl + Alt + J) from any application.
"""
import ctypes
from ctypes import wintypes
import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAT_PATH = os.path.join(BASE_DIR, "run_jarvis.bat")

user32 = ctypes.windll.user32

# Modifiers
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000
VK_J = 0x4A
HOTKEY_ID = 101


def is_jarvis_running() -> bool:
    """Check if voice_cli.py or jarvis window is already active."""
    try:
        output = subprocess.check_output(
            ["powershell", "-Command", "Get-Process -Name python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty MainWindowTitle"],
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return "JARVIS" in output or "voice_cli" in output
    except Exception:
        return False


def launch_jarvis():
    """Launch JARVIS Voice CLI and Web UI."""
    print("🚀 Hotkey Triggered! Launching JARVIS...")
    try:
        import winsound
        winsound.Beep(988, 70)
        winsound.Beep(1318, 120)
    except Exception:
        pass

    try:
        subprocess.Popen(
            ["cmd.exe", "/c", f"start \"\" \"{BAT_PATH}\""],
            cwd=BASE_DIR,
            shell=True,
        )
        print("✅ JARVIS launched successfully.")
    except Exception as e:
        print(f"❌ Launch error: {e}")


def main():
    print("==================================================")
    print("⚡ JARVIS NATIVE GLOBAL HOTKEY DAEMON ACTIVE ⚡")
    print("Press [Ctrl + Alt + J] anywhere to open JARVIS.")
    print("==================================================")

    # Register Hotkey: Ctrl + Alt + J
    res = user32.RegisterHotKey(None, HOTKEY_ID, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_J)
    if not res:
        # Retry without MOD_NOREPEAT (for older Windows builds)
        res = user32.RegisterHotKey(None, HOTKEY_ID, MOD_CONTROL | MOD_ALT, VK_J)
        if not res:
            print("⚠️ Failed to register hotkey. It may already be in use.")
            return

    print("✅ Global Hotkey [Ctrl + Alt + J] Registered with Windows OS!")

    msg = wintypes.MSG()
    try:
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == 0x0312:  # WM_HOTKEY
                if msg.wParam == HOTKEY_ID:
                    launch_jarvis()
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    except KeyboardInterrupt:
        pass
    finally:
        user32.UnregisterHotKey(None, HOTKEY_ID)
        print("Hotkey unregistered.")


if __name__ == "__main__":
    main()
