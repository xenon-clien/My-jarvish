"""Central Safety Configuration and Automation Guards for JARVIS AI.

Enforces non-interactive safe development mode, guards all physical hardware
input operations (mouse, keyboard, wheel), prevents foreground window stealing,
and isolates testing and development environments from the real desktop.
"""

import os
import sys
from typing import Any, Dict, Optional
from backend.core.logger import get_logger

logger = get_logger("SafetyCore")

# Global emergency stop state
_EMERGENCY_STOP_ACTIVE: bool = False


def is_dev_safe_mode() -> bool:
    """Return True if running in development safe mode.
    
    Default is True unless explicitly set to '0', 'false', or 'no'.
    Automatically True when running under pytest or test harnesses.
    """
    if "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
        return True

    val = os.environ.get("JARVIS_DEV_SAFE_MODE", "1").strip().lower()
    return val not in ("0", "false", "no", "off")


def is_physical_automation_allowed() -> bool:
    """Return True only if physical hardware automation (mouse/keyboard) is explicitly enabled.
    
    Must be explicitly enabled via JARVIS_ALLOW_PHYSICAL_INPUT=1 AND
    development safe mode must NOT be active AND emergency stop must not be active.
    Default is strictly False.
    """
    if _EMERGENCY_STOP_ACTIVE:
        return False

    if is_dev_safe_mode():
        return False

    val = os.environ.get("JARVIS_ALLOW_PHYSICAL_INPUT", "0").strip().lower()
    return val in ("1", "true", "yes", "on")


def is_live_browser_automation_allowed() -> bool:
    """Return True only if real browser manipulation is explicitly opted into.
    
    Requires JARVIS_LIVE_TEST=1 or JARVIS_ALLOW_LIVE_BROWSER_AUTOMATION=1 AND
    emergency stop must not be active.
    Default is strictly False.
    """
    if _EMERGENCY_STOP_ACTIVE:
        return False

    # Under pytest or test harnesses, strictly False unless explicitly mocked/live_test
    if "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
        live_test = os.environ.get("JARVIS_LIVE_TEST", "0").strip().lower() in ("1", "true", "yes", "on")
        return live_test

    allow_browser = os.environ.get("JARVIS_ALLOW_LIVE_BROWSER_AUTOMATION", "0").strip().lower() in ("1", "true", "yes", "on")
    live_test = os.environ.get("JARVIS_LIVE_TEST", "0").strip().lower() in ("1", "true", "yes", "on")
    if allow_browser or live_test:
        return True

    if is_dev_safe_mode():
        return False

    return False


def is_foreground_stealing_allowed() -> bool:
    """Return True only if switching foreground focus away from the active window is permitted.
    
    Default is strictly False in dev/test contexts to prevent interfering with
    the user's typing, scrolling, or IDE focus.
    """
    if _EMERGENCY_STOP_ACTIVE or is_dev_safe_mode():
        return False

    val = os.environ.get("JARVIS_ALLOW_FOREGROUND_FOCUS", "0").strip().lower()
    return val in ("1", "true", "yes", "on") and is_physical_automation_allowed()


def emergency_stop_active() -> bool:
    """Check if emergency stop is currently engaged."""
    return _EMERGENCY_STOP_ACTIVE


def set_emergency_stop(active: bool) -> None:
    """Set the global emergency stop state."""
    global _EMERGENCY_STOP_ACTIVE
    _EMERGENCY_STOP_ACTIVE = active
    if active:
        logger.warning("[SAFETY] Global emergency stop engaged. All hardware automation blocked.")
    else:
        logger.info("[SAFETY] Global emergency stop cleared.")


def safe_blocked_result(action: str, reason: Optional[str] = None) -> Dict[str, Any]:
    """Generate a standardized safe response when physical automation is blocked."""
    msg = reason or "physical automation disabled in development mode"
    logger.info(f"[SAFETY_GUARD] Blocked action '{action}': {msg}")
    return {
        "success": False,
        "status": "LIVE_AUTOMATION_DISABLED",
        "action": action,
        "reason": msg,
        "message": f"Action '{action}' was blocked by safety policy ({msg}).",
    }


# ── Safe Hardware Wrappers ──────────────────────────────────────────────────

def safe_set_cursor_pos(x: int, y: int) -> bool:
    """Safely move mouse cursor only if physical automation is explicitly permitted."""
    if not is_physical_automation_allowed():
        logger.debug(f"[SAFETY_GUARD] Blocked SetCursorPos({x}, {y})")
        return False
    try:
        import ctypes
        return bool(ctypes.windll.user32.SetCursorPos(int(x), int(y)))
    except Exception as exc:
        logger.debug(f"SetCursorPos error: {exc}")
        return False


def safe_mouse_event(flags: int, dx: int = 0, dy: int = 0, data: int = 0, extra: int = 0) -> bool:
    """Safely dispatch mouse event only if physical automation is explicitly permitted."""
    if not is_physical_automation_allowed():
        logger.debug(f"[SAFETY_GUARD] Blocked mouse_event(flags={hex(flags)}, dx={dx}, dy={dy}, data={data})")
        return False
    try:
        import ctypes
        ctypes.windll.user32.mouse_event(flags, dx, dy, data, extra)
        return True
    except Exception as exc:
        logger.debug(f"mouse_event error: {exc}")
        return False


def safe_keybd_event(vk: int, scan: int = 0, flags: int = 0, extra: int = 0) -> bool:
    """Safely dispatch keyboard event only if physical automation is explicitly permitted."""
    if not is_physical_automation_allowed():
        logger.debug(f"[SAFETY_GUARD] Blocked keybd_event(vk={hex(vk)}, scan={scan}, flags={flags})")
        return False
    try:
        import ctypes
        ctypes.windll.user32.keybd_event(vk, scan, flags, extra)
        return True
    except Exception as exc:
        logger.debug(f"keybd_event error: {exc}")
        return False


def safe_set_foreground_window(hwnd: int) -> bool:
    """Safely change foreground window only if foreground focus stealing is permitted."""
    if not is_foreground_stealing_allowed():
        logger.debug(f"[SAFETY_GUARD] Blocked SetForegroundWindow(hwnd={hwnd})")
        return False
    try:
        import ctypes
        return bool(ctypes.windll.user32.SetForegroundWindow(hwnd))
    except Exception as exc:
        logger.debug(f"SetForegroundWindow error: {exc}")
        return False
