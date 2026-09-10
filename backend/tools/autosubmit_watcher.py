"""
AutoSubmit Watcher for Antigravity IDE (PERMANENTLY DISABLED).

This module previously scanned child windows and injected physical mouse clicks.
It has been permanently neutralized to protect user desktop safety and prevent
mouse hijacking, cursor jumping, and interference with Antigravity IDE.
"""
import logging
from typing import Optional, Tuple
from backend.core.safety import is_physical_automation_allowed

logger = logging.getLogger("AutoSubmit")


def _left_click(x: int, y: int) -> None:
    """Safely blocked left-click."""
    if not is_physical_automation_allowed():
        logger.debug("[SAFETY] Blocked AutoSubmit _left_click attempt.")
        return


def _scan_and_click() -> None:
    """Permanently disabled background scanner."""
    logger.debug("[SAFETY] AutoSubmit _scan_and_click is permanently disabled.")
    return


def start_autosubmit_watcher() -> bool:
    """Permanently disabled. Zero background threads, zero physical mouse clicks."""
    logger.warning("AutoSubmit watcher is permanently disabled for system safety.")
    return False
