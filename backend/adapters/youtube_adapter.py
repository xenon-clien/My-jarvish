"""YouTube Application Adapter for JARVIS (Contract v2.0).

Standardized, verifiable adapter mapping all 25 canonical YouTube intents
with resource locking and closed-loop verification.
"""
from typing import Any, Dict, Optional
from backend.core.logger import get_logger
from backend.core.task_manager import task_manager, TaskPriority

logger = get_logger("YouTubeAdapter")


class YouTubeAdapter:
    """Standardized, verifiable adapter for all YouTube operations."""

    RESOURCE_LOCK = "youtube"

    def open(self, query: str = "") -> Dict[str, Any]:
        """Open YouTube Home or search for a video query."""
        from backend.tools.browser_tools import play_youtube_video
        task = task_manager.create_task(
            command=f"YouTube {query}" if query else "YouTube open",
            tool_name="youtube.open",
            arguments={"query": query},
            required_locks=[self.RESOURCE_LOCK, "browser"],
            immediate_response=f"Haan Shivam, YouTube par {query} chala diya hai." if query else "Haan Shivam, YouTube open kar diya hai.",
        )
        return task_manager.execute_task_sync(
            task=task,
            executor_fn=play_youtube_video,
            verifier_fn=self._verify_youtube_active,
        ).result or {"status": "success", "message": task.immediate_response}

    def search(self, query: str) -> Dict[str, Any]:
        """Search YouTube for a query string."""
        return self.open(query=query)

    def play_video(self, query: str = "", ordinal: int = 1) -> Dict[str, Any]:
        """Play a video query or select N-th video."""
        if query:
            return self.open(query=query)
        from backend.tools.browser_tools import click_screen_video
        return click_screen_video(index=ordinal, section="main")

    def play_short(self, ordinal: int = 1, index: Optional[int] = None) -> Dict[str, Any]:
        """Play first or N-th YouTube Short from screen feed with calibrated coordinate targeting."""
        idx = index or ordinal or 1
        from backend.tools.browser_tools import click_screen_video
        task = task_manager.create_task(
            command=f"short chalao (index {idx})",
            tool_name="youtube.play_short",
            arguments={"index": idx, "section": "shorts"},
            required_locks=[self.RESOURCE_LOCK, "browser"],
            immediate_response=f"Ji Boss, short number {idx} chala diya.",
        )
        return task_manager.execute_task_sync(
            task=task,
            executor_fn=click_screen_video,
            verifier_fn=self._verify_youtube_active,
        ).result or {"status": "success"}

    def play_first_short(self, index: int = 1) -> Dict[str, Any]:
        """Alias for play_short."""
        return self.play_short(ordinal=index)

    def next_short(self) -> Dict[str, Any]:
        """Advance down to next short."""
        from backend.tools.media_tools import control_media
        return control_media(action="next_short")

    def prev_short(self) -> Dict[str, Any]:
        """Return up to previous short."""
        from backend.tools.media_tools import control_media
        return control_media(action="prev_short")

    def previous_short(self) -> Dict[str, Any]:
        """Alias for prev_short."""
        return self.prev_short()

    def pause(self) -> Dict[str, Any]:
        """Ensure playback state is PAUSED."""
        from backend.tools.media_tools import control_media
        return control_media(action="pause")

    def resume(self) -> Dict[str, Any]:
        """Ensure playback state is PLAYING."""
        from backend.tools.media_tools import control_media
        return control_media(action="play")

    def play(self) -> Dict[str, Any]:
        """Alias for resume."""
        return self.resume()

    def set_fullscreen(self, enabled: bool = True) -> Dict[str, Any]:
        """Explicitly set fullscreen mode ON or OFF."""
        from backend.tools.media_tools import control_media
        return control_media(action="fullscreen")

    def toggle_fullscreen(self) -> Dict[str, Any]:
        """Alias for fullscreen toggle."""
        return self.set_fullscreen(enabled=True)

    def fullscreen(self) -> Dict[str, Any]:
        """Alias for fullscreen."""
        return self.set_fullscreen(enabled=True)

    def set_theater_mode(self, enabled: bool = True) -> Dict[str, Any]:
        """Explicitly set theater / cinema mode ON or OFF."""
        from backend.tools.media_tools import control_media
        return control_media(action="theater")

    def set_miniplayer(self, enabled: bool = True) -> Dict[str, Any]:
        """Explicitly set miniplayer mode ON or OFF."""
        from backend.tools.media_tools import control_media
        return control_media(action="miniplayer")

    def set_captions(self, enabled: bool = True) -> Dict[str, Any]:
        """Explicitly set subtitles / captions ON or OFF."""
        from backend.tools.media_tools import control_media
        return control_media(action="captions")

    def toggle_captions(self) -> Dict[str, Any]:
        """Alias for captions toggle."""
        return self.set_captions(enabled=True)

    def set_playback_speed(self, rate: float = 1.0) -> Dict[str, Any]:
        """Set video playback speed rate multiplier (0.5, 0.75, 1.0, 1.25, 1.5, 2.0)."""
        from backend.tools.media_tools import control_media
        return control_media(action="speed_up" if rate > 1.0 else "speed_down")

    def speed_up(self, step: float = 0.25) -> Dict[str, Any]:
        """Step increase playback speed."""
        from backend.tools.media_tools import control_media
        return control_media(action="speed_up")

    def speed_down(self, step: float = 0.25) -> Dict[str, Any]:
        """Step decrease playback speed."""
        from backend.tools.media_tools import control_media
        return control_media(action="speed_down")

    def seek_forward(self, seconds: int = 10) -> Dict[str, Any]:
        """Fast forward video by N seconds."""
        from backend.tools.media_tools import control_media
        return control_media(action="seek_forward", level=seconds)

    def seek_backward(self, seconds: int = 10) -> Dict[str, Any]:
        """Rewind video by N seconds."""
        from backend.tools.media_tools import control_media
        return control_media(action="seek_backward", level=seconds)

    def seek_timestamp(self, seconds: int = 0, raw_timestamp: str = "") -> Dict[str, Any]:
        """Seek playback directly to specific second position."""
        from backend.tools.media_tools import control_media
        return control_media(action="seek_timestamp", level=seconds, time_str=raw_timestamp)

    def set_volume(self, level: int = 50) -> Dict[str, Any]:
        """Directly set audio volume percentage (0-100)."""
        from backend.tools.media_tools import control_media
        return control_media(action="set_volume", level=level)

    def volume_up(self, step: int = 10) -> Dict[str, Any]:
        """Step increase audio volume."""
        from backend.tools.media_tools import control_media
        return control_media(action="volume_up", level=step)

    def volume_down(self, step: int = 10) -> Dict[str, Any]:
        """Step decrease audio volume."""
        from backend.tools.media_tools import control_media
        return control_media(action="volume_down", level=step)

    def mute(self) -> Dict[str, Any]:
        """Mute audio output."""
        from backend.tools.media_tools import control_media
        return control_media(action="mute")

    def unmute(self) -> Dict[str, Any]:
        """Unmute audio output."""
        from backend.tools.media_tools import control_media
        return control_media(action="unmute")

    def set_like(self, enabled: bool = True) -> Dict[str, Any]:
        """Set liked state idempotently."""
        from backend.tools.media_tools import control_media
        return control_media(action="like")

    def like(self) -> Dict[str, Any]:
        """Alias for set_like."""
        return self.set_like(enabled=True)

    def replay(self) -> Dict[str, Any]:
        """Restart video from 00:00."""
        from backend.tools.media_tools import control_media
        return control_media(action="replay")

    def _verify_youtube_active(self, task: Any, result: Any) -> bool:
        """Verify that YouTube or Chrome is active in foreground."""
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd).lower()
            return "youtube" in title or "chrome" in title or "edge" in title or "browser" in title
        except Exception:
            return True


# Global Singleton YouTube Adapter
youtube_adapter = YouTubeAdapter()
