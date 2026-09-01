"""Safe Audio Service and Endpoint Self-Repair Module for Windows."""
import subprocess
import time
from typing import Any, Dict

from backend.core.logger import get_logger

logger = get_logger("AudioRepair")


class AudioRepair:
    """Performs safe Windows Audio service restarts and endpoint resets."""

    @staticmethod
    def restart_audio_services() -> Dict[str, Any]:
        """Restart Audiosrv and AudioEndpointBuilder services."""
        logger.info("Restarting Windows Audio services...")
        try:
            cmd = (
                "powershell -NoProfile -Command \""
                "Restart-Service -Name 'AudioEndpointBuilder' -Force -ErrorAction SilentlyContinue; "
                "Restart-Service -Name 'Audiosrv' -Force -ErrorAction SilentlyContinue; "
                "Start-Service -Name 'Audiosrv' -ErrorAction SilentlyContinue\""
            )
            subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            time.sleep(1.5)
            return {
                "status": "success",
                "action": "restart_audio_services",
                "message": "Windows Audio services restarted and reinitialized.",
            }
        except Exception as e:
            return {"status": "error", "action": "restart_audio_services", "message": f"Audio service restart error: {e}"}

    @staticmethod
    def unmute_system_audio() -> Dict[str, Any]:
        """Ensure audio output is unmuted and set to a healthy audible volume."""
        try:
            from backend.tools.media_tools import control_media
            control_media(action="unmute")
            control_media(action="volume_up", steps=2)
            return {
                "status": "success",
                "action": "unmute_system_audio",
                "message": "Audio output unmuted and volume adjusted.",
            }
        except Exception as e:
            return {"status": "warning", "action": "unmute_system_audio", "message": f"Audio volume adjustment notice: {e}"}
