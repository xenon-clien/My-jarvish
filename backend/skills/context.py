"""Universal Context Engine & Relative Reference Resolver for JARVIS AI.

Tracks live application state, foreground window, page URL, media state,
and translates relative natural-language references ("this", "that", "it", "second one",
"the current video", "previous tab", "scroll until comments") into concrete targets.
"""
import re
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import win32gui
    import win32process
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

from backend.core.logger import get_logger
from backend.skills.models import AppContextState

logger = get_logger("UniversalContextEngine")


class AppStateManager:
    """Manages real-time application context, history, and state tracking."""

    def __init__(self):
        self.state: AppContextState = AppContextState()

    def update_live_state(self) -> AppContextState:
        """Poll the current OS foreground window and update context state."""
        if not WIN32_AVAILABLE:
            return self.state

        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                title = win32gui.GetWindowText(hwnd)
                self.state.active_window_hwnd = hwnd
                self.state.active_window_title = title

                title_lower = title.lower()
                if "youtube" in title_lower:
                    self.state.active_app = "youtube"
                elif "chrome" in title_lower:
                    self.state.active_app = "chrome"
                elif "edge" in title_lower:
                    self.state.active_app = "edge"
                elif "visual studio code" in title_lower or "code" in title_lower:
                    self.state.active_app = "vscode"
                elif "spotify" in title_lower:
                    self.state.active_app = "spotify"
                elif "whatsapp" in title_lower:
                    self.state.active_app = "whatsapp"
                elif "discord" in title_lower:
                    self.state.active_app = "discord"
                elif "file explorer" in title_lower or "explorer" in title_lower:
                    self.state.active_app = "file_explorer"
                elif "settings" in title_lower:
                    self.state.active_app = "settings"
                else:
                    self.state.active_app = "desktop"
        except Exception as exc:
            logger.debug(f"Live state polling error: {exc}")

        return self.state

    def get_active_app(self) -> Optional[str]:
        """Return the currently detected active app name."""
        return self.update_live_state().active_app

    def get_last_target(self) -> Optional[str]:
        """Return the target of the last recorded action."""
        return self.state.last_action_target

    def record_action(self, action_name: str, target: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> None:
        """Record an executed action into the sequence history."""
        self.state.last_action = action_name
        self.state.last_action_target = target
        self.state.last_action_timestamp = time.time()
        self.state.action_history.append({
            "action": action_name,
            "target": target,
            "data": data or {},
            "timestamp": time.time(),
        })
        if len(self.state.action_history) > 30:
            self.state.action_history.pop(0)

    def get_last_action(self) -> Optional[Dict[str, Any]]:
        """Return the most recent action executed."""
        if self.state.action_history:
            return self.state.action_history[-1]
        return None


class RelativeCommandResolver:
    """Resolves relative commands ('it', 'this one', 'second video', 'right side') to concrete actions."""

    def __init__(self, state_manager: AppStateManager):
        self.state_manager = state_manager

    def resolve(self, text: str) -> Dict[str, Any]:
        """Parse natural language command and infer target from live context."""
        cleaned = text.lower().strip()
        live_state = self.state_manager.update_live_state()
        active_app = live_state.active_app or "general"

        resolved: Dict[str, Any] = {
            "application": active_app,
            "relative_target": None,
            "action": None,
            "ordinal_index": None,
            "position": None,
            "entity": None,
        }

        # 1. Ordinal matching (second one, 3rd video, 4th item)
        ordinal_map = {
            "first": 1, "1st": 1, "pehla": 1, "pehli": 1,
            "second": 2, "2nd": 2, "dusra": 2, "doosra": 2, "dusri": 2,
            "third": 3, "3rd": 3, "teesra": 3, "tisra": 3, "teesri": 3,
            "fourth": 4, "4th": 4, "chautha": 4,
            "fifth": 5, "5th": 5, "paanchwa": 5,
            "sixth": 6, "6th": 6, "chhatha": 6,
        }
        for word, idx in ordinal_map.items():
            if re.search(rf"\b{word}\b", cleaned):
                resolved["ordinal_index"] = idx
                break

        # 2. Position matching (right side, left, above, below)
        if any(w in cleaned for w in ["right side", "right", "daayein"]):
            resolved["position"] = "right"
        elif any(w in cleaned for w in ["left side", "left", "baayein"]):
            resolved["position"] = "left"
        elif any(w in cleaned for w in ["above", "upar", "top"]):
            resolved["position"] = "top"
        elif any(w in cleaned for w in ["below", "niche", "neeche", "bottom"]):
            resolved["position"] = "bottom"

        # 3. Relative Pronoun Resolution ("it", "this", "that", "the current one")
        if any(w in cleaned for w in ["it", "this", "that", "yeh", "woh", "isko", "usko"]):
            last_act = self.state_manager.get_last_action()
            if last_act:
                resolved["entity"] = last_act.get("target") or active_app
            else:
                resolved["entity"] = active_app

        # 4. Contextual Semantic Actions
        if any(w in cleaned for w in ["like", "like it", "iss video ko like", "is video ko like", "like this"]):
            resolved["action"] = "like"
        elif any(w in cleaned for w in ["share", "share it", "video share", "share this"]):
            resolved["action"] = "share"
        elif any(w in cleaned for w in ["subscribe", "channel subscribe", "subscribe karo"]):
            resolved["action"] = "subscribe"
        elif any(w in cleaned for w in ["comments", "comment section", "scroll until comments"]):
            resolved["action"] = "comments_down"
        elif any(w in cleaned for w in ["next", "agla", "next one", "play next"]):
            resolved["action"] = "next"
        elif any(w in cleaned for w in ["previous", "pichla", "prev one"]):
            resolved["action"] = "previous"

        return resolved


# Global state instances
state_manager = AppStateManager()
app_state_manager = state_manager
relative_resolver = RelativeCommandResolver(state_manager)

