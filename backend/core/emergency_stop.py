"""Global Emergency Stop Manager for JARVIS AI.

Cancels all pending automation, file transfers, browser actions,
and releases all resource locks safely when triggered by:
- Developer / CLI commands: "/stop", "/emergency-stop"
- Voice: "Jarvish stop" / "Stop all actions"
- Gesture: 2-second Closed Fist
- UI: "STOP ALL ACTIONS" button
"""

import time
from typing import Dict, Any
from backend.core.logger import get_logger
from backend.core.safety import set_emergency_stop

logger = get_logger("EmergencyStop")


class EmergencyStopManager:
    """Global emergency stop coordinator."""

    def __init__(self):
        self.is_halted: bool = False
        self.last_halt_time: float = 0.0
        self.last_halt_reason: str = ""

    def trigger_stop(self, reason: str = "User Emergency Stop") -> Dict[str, Any]:
        """Trigger an emergency halt across all assistant subsystems."""
        self.is_halted = True
        self.last_halt_time = time.time()
        self.last_halt_reason = reason
        set_emergency_stop(True)
        logger.warning(f"EMERGENCY STOP TRIGGERED: '{reason}'")

        # Force release all acquired resource locks in TaskManager
        try:
            from backend.core.task_manager import task_manager
            task_manager.lock_manager.force_release_all()
        except Exception as e:
            logger.debug(f"Error releasing locks on emergency stop: {e}")

        # Cancel pending file transfers if any
        try:
            from backend.plugins.files.file_transfer_manager import file_transfer_manager
            file_transfer_manager.cancel_pending_transfer()
        except Exception:
            pass

        return {
            "status": "EMERGENCY_STOPPED",
            "reason": reason,
            "timestamp": self.last_halt_time,
            "message": f"JARVIS emergency stop triggered: {reason}. All pending actions cancelled and locks released.",
        }

    def reset_stop(self) -> Dict[str, Any]:
        """Reset emergency stop state to allow normal operations."""
        self.is_halted = False
        set_emergency_stop(False)
        logger.info("Emergency stop state reset. JARVIS is ready.")
        return {
            "status": "ACTIVE",
            "message": "Emergency stop cleared. JARVIS is operational.",
        }


# Global singleton instance
emergency_stop_manager = EmergencyStopManager()
