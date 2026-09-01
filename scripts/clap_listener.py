"""Standalone Background Double-Clap Listener & Auto-Launcher for JARVIS.

Runs in background on Windows startup, monitors microphone for 2 fast claps,
and automatically turns on JARVIS Voice CLI & Web UI.
"""
import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from backend.core.logger import get_logger
from backend.voice.clap_detector import ClapDetector

logger = get_logger("ClapListenerDaemon")


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
    """Launch JARVIS Voice CLI and Web UI in interactive Windows session."""
    logger.info("🚀 Double-Clap received! Starting JARVIS...")
    try:
        # Immediate audio chime
        try:
            import winsound
            winsound.Beep(988, 80)
            winsound.Beep(1318, 140)
        except Exception:
            pass

        cmd_voice = f"Start-Process cmd -ArgumentList '/k python scripts\\voice_cli.py' -WorkingDirectory '{BASE_DIR}'"
        cmd_web = f"Start-Process cmd -ArgumentList '/k python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000' -WorkingDirectory '{BASE_DIR}'"

        subprocess.Popen(
            ["powershell", "-Command", f"{cmd_voice}; {cmd_web}"],
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        logger.info("✅ JARVIS Assistant & Web UI launched successfully.")
    except Exception as e:
        logger.error(f"Failed to launch JARVIS: {e}")


def main():
    logger.info("==================================================")
    logger.info("⚡ JARVIS CLAP-TO-WAKE BACKGROUND DAEMON ACTIVE ⚡")
    logger.info("Clap twice (2 times) to turn on JARVIS automatically.")
    logger.info("==================================================")

    detector = ClapDetector(
        on_double_clap=launch_jarvis,
        energy_threshold=0.06,
        min_clap_interval=0.10,
        max_clap_interval=0.85,
    )

    detector.start_listening()

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        detector.stop_listening()
        logger.info("Clap daemon stopped by user.")


if __name__ == "__main__":
    main()
