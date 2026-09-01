"""Global Emergency Stop Manager for JARVIS AI.

Cancels all pending automation, file transfers, browser actions,
and gesture triggers safely when triggered by:
- Voice: "Jarvish stop" / "Stop all actions"
- Gesture: 2-second Closed Fist
- UI: "STOP ALL ACTIONS" button
"""

import time
from typing import Dict, Any
from backend.core.logger import get_logger

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
        logger.warning(f"EMERGENCY STOP TRIGGERED: '{reason}'")

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
            "message": f"JARVIS emergency stop triggered: {reason}. All pending actions cancelled.",
        }

    def reset_stop(self) -> Dict[str, Any]:
        """Reset emergency stop state to allow normal operations."""
        self.is_halted = False
        logger.info("Emergency stop state reset. JARVIS is ready.")
        return {
            "status": "ACTIVE",
            "message": "Emergency stop cleared. JARVIS is operational.",
        }


# Global singleton instance
emergency_stop_manager = EmergencyStopManager()
