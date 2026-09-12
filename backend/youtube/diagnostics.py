"""Authoritative Diagnostics, State Inspection, and Safe Structured Tracing for YouTube Runtime V3.

Implements Phase 24 & Phase 25 invariants:
- Pure read-only diagnostic observation (youtube.observe).
- Human-readable summary for voice and UI responses.
- Structured safe trace logging without leaking user tokens or sensitive data.
"""
from typing import Any, Dict, Optional

from backend.core.logger import get_logger
from backend.youtube.models import PerceptionSnapshot

logger = get_logger("YouTubeDiagnosticsV3")


class YouTubeDiagnostics:
    """Provides safe diagnostic summaries and structured operational logging."""

    @staticmethod
    def format_diagnostic_summary(snapshot: PerceptionSnapshot, max_items: int = 5) -> str:
        """Format a human-readable perception diagnostic string for voice & chat UI."""
        if not snapshot.browser_running:
            return "Chrome browser band hai Boss. Koi YouTube window nahi mil rahi."

        if not snapshot.is_youtube:
            return f"Browser khula hai lekin YouTube par nahi hai. Current title: '{snapshot.window_title}'"

        pt = snapshot.page_type.value if hasattr(snapshot.page_type, "value") else str(snapshot.page_type)

        # 1. Video Playing View
        if pt == "VIDEO":
            title = snapshot.current_video.title
            vid = snapshot.current_video.video_id
            paused = snapshot.player.paused
            state_str = "Paused" if paused is True else ("Playing" if paused is False else "Loaded")
            curr_t = snapshot.player.current_time
            dur = snapshot.player.duration
            time_str = f"[{curr_t}s / {dur}s]" if curr_t != "UNKNOWN" and dur != "UNKNOWN" else ""
            return f"Abhi YouTube par video chal rahi hai: '{title}' ({state_str}) {time_str}. Video ID: {vid}."

        # 2. Shorts View
        if pt == "SHORTS":
            title = snapshot.current_video.title
            vid = snapshot.current_video.video_id
            return f"Abhi YouTube Shorts khula hai: '{title}'. Short ID: {vid}."

        # 3. Search Results View
        if pt == "SEARCH_RESULTS":
            q = snapshot.search_query
            vids = snapshot.visible_videos[:max_items]
            if not vids:
                return f"YouTube par '{q}' ke search results khule hain, lekin koi video cards visible nahi hain."
            lines = [f"YouTube Search: '{q}'. Top visible videos:"]
            for v in vids:
                lines.append(f"{v.ordinal}. {v.title} [{v.video_id}]")
            return "\n".join(lines)

        # 4. Home Feed View
        if pt == "HOME":
            vids = snapshot.visible_videos[:max_items]
            if not vids:
                return "YouTube Home screen khuli hai."
            lines = ["YouTube Home screen par ye videos dikh rahi hain:"]
            for v in vids:
                lines.append(f"{v.ordinal}. {v.title} [{v.video_id}]")
            return "\n".join(lines)

        return f"YouTube open hai. Page type: {pt}. Title: '{snapshot.window_title}'"

    @staticmethod
    def log_structured_trace(
        command: str,
        canonical_action: str,
        arguments: Dict[str, Any],
        snapshot_before: Optional[PerceptionSnapshot],
        selected_target_id: Optional[str],
        execution_method: str,
        snapshot_after: Optional[PerceptionSnapshot],
        verification_status: str,
    ) -> None:
        """Log structured, sanitized operational trace for production diagnostics."""
        trace = {
            "COMMAND": command,
            "NLU": {"action": canonical_action, "arguments": arguments},
            "SNAPSHOT_ID": snapshot_before.snapshot_id if snapshot_before else None,
            "PAGE_ID": snapshot_before.page_id if snapshot_before else None,
            "PAGE_GENERATION": snapshot_before.generation if snapshot_before else 0,
            "VISIBLE_TARGETS": [v.video_id for v in snapshot_before.visible_videos[:5]] if snapshot_before else [],
            "SELECTED_TARGET_ID": selected_target_id,
            "EXECUTION_METHOD": execution_method,
            "AFTER_ID": snapshot_after.current_video.video_id if snapshot_after else None,
            "AFTER_PAGE_TYPE": (snapshot_after.page_type.value if hasattr(snapshot_after.page_type, "value") else str(snapshot_after.page_type)) if snapshot_after else None,
            "VERIFICATION": verification_status,
        }
        logger.info(f"[YOUTUBE_V3_TRACE] {trace}")


# Global singleton instance
youtube_diagnostics = YouTubeDiagnostics()


def get_youtube_diagnostics() -> YouTubeDiagnostics:
    """Return the global YouTubeDiagnostics singleton."""
    return youtube_diagnostics
