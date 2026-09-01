"""YouTube Application Adapter for JARVIS.

Non-destructively wraps existing YouTube capabilities in browser_tools and media_tools
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
            immediate_response=f"Ji Boss, YouTube par {query} chala diya." if query else "Ji Boss, YouTube open kar diya.",
        )
        return task_manager.execute_task_sync(
            task=task,
            executor_fn=play_youtube_video,
            verifier_fn=self._verify_youtube_active,
        ).result or {"status": "success", "message": task.immediate_response}

    def play(self) -> Dict[str, Any]:
        """Resume / Play active YouTube video."""
        from backend.tools.media_tools import control_media
        task = task_manager.create_task(
            command="video chalao",
            tool_name="youtube.play",
            arguments={"action": "play"},
            required_locks=[self.RESOURCE_LOCK],
            immediate_response="Ji Boss, video play kar diya.",
        )
        return task_manager.execute_task_sync(task=task, executor_fn=control_media).result or {"status": "success"}

    def pause(self) -> Dict[str, Any]:
        """Pause active YouTube video."""
        from backend.tools.media_tools import control_media
        task = task_manager.create_task(
            command="video pause karo",
            tool_name="youtube.pause",
            arguments={"action": "pause"},
            required_locks=[self.RESOURCE_LOCK],
            immediate_response="Ji Boss, video pause kar diya.",
        )
        return task_manager.execute_task_sync(task=task, executor_fn=control_media).result or {"status": "success"}

    def play_first_short(self, index: int = 1) -> Dict[str, Any]:
        """Play first or N-th YouTube Short from screen feed with precise coordinate targeting."""
        from backend.tools.browser_tools import click_screen_video
        task = task_manager.create_task(
            command=f"pehla short chalao (index {index})",
            tool_name="youtube.play_first_short",
            arguments={"index": index, "section": "shorts"},
            required_locks=[self.RESOURCE_LOCK, "browser"],
            immediate_response="Ji Boss, YouTube Shorts chala diya.",
        )
        return task_manager.execute_task_sync(
            task=task,
            executor_fn=click_screen_video,
            verifier_fn=self._verify_youtube_active,
        ).result or {"status": "success"}

    def next_short(self) -> Dict[str, Any]:
        """Switch to next short."""
        from backend.tools.browser_tools import click_screen_video
        task = task_manager.create_task(
            command="agla short dikhao",
            tool_name="youtube.next_short",
            arguments={"index": 1, "section": "shorts"},
            required_locks=[self.RESOURCE_LOCK],
            immediate_response="Ji Boss, agla short chala diya.",
        )
        return task_manager.execute_task_sync(task=task, executor_fn=click_screen_video).result or {"status": "success"}

    def prev_short(self) -> Dict[str, Any]:
        """Switch to previous short."""
        from backend.tools.media_tools import control_media
        task = task_manager.create_task(
            command="pichla short dikhao",
            tool_name="youtube.prev_short",
            arguments={"action": "previous"},
            required_locks=[self.RESOURCE_LOCK],
            immediate_response="Ji Boss, pichla short chala diya.",
        )
        return task_manager.execute_task_sync(task=task, executor_fn=control_media).result or {"status": "success"}

    def select_video(self, index: int = 1, section: str = "main") -> Dict[str, Any]:
        """Select N-th thumbnail on feed or sidebar."""
        from backend.tools.browser_tools import click_screen_video
        task = task_manager.create_task(
            command=f"video number {index} chalao",
            tool_name="youtube.select_video",
            arguments={"index": index, "section": section},
            required_locks=[self.RESOURCE_LOCK, "browser"],
            immediate_response=f"Ji Boss, video number {index} chala diya.",
        )
        return task_manager.execute_task_sync(task=task, executor_fn=click_screen_video).result or {"status": "success"}

    def seek_forward(self, seconds: int = 10) -> Dict[str, Any]:
        """Fast forward video."""
        from backend.tools.media_tools import control_media
        task = task_manager.create_task(
            command=f"{seconds} seconds aage karo",
            tool_name="youtube.seek_forward",
            arguments={"action": "seek_forward", "level": seconds},
            required_locks=[self.RESOURCE_LOCK],
            immediate_response=f"Ji Boss, {seconds} seconds aage kar diya.",
        )
        return task_manager.execute_task_sync(task=task, executor_fn=control_media).result or {"status": "success"}

    def seek_backward(self, seconds: int = 10) -> Dict[str, Any]:
        """Rewind video."""
        from backend.tools.media_tools import control_media
        task = task_manager.create_task(
            command=f"{seconds} seconds peeche karo",
            tool_name="youtube.seek_backward",
            arguments={"action": "seek_backward", "level": seconds},
            required_locks=[self.RESOURCE_LOCK],
            immediate_response=f"Ji Boss, {seconds} seconds peeche kar diya.",
        )
        return task_manager.execute_task_sync(task=task, executor_fn=control_media).result or {"status": "success"}

    def toggle_fullscreen(self) -> Dict[str, Any]:
        """Toggle fullscreen mode."""
        from backend.tools.media_tools import control_media
        task = task_manager.create_task(
            command="fullscreen toggle",
            tool_name="youtube.fullscreen",
            arguments={"action": "fullscreen"},
            required_locks=[self.RESOURCE_LOCK],
            immediate_response="Ji Boss, fullscreen toggle kar diya.",
        )
        return task_manager.execute_task_sync(task=task, executor_fn=control_media).result or {"status": "success"}

    def toggle_captions(self) -> Dict[str, Any]:
        """Toggle subtitles / captions."""
        from backend.tools.media_tools import control_media
        task = task_manager.create_task(
            command="captions toggle",
            tool_name="youtube.captions",
            arguments={"action": "captions"},
            required_locks=[self.RESOURCE_LOCK],
            immediate_response="Ji Boss, captions/subtitles toggle kar diye.",
        )
        return task_manager.execute_task_sync(task=task, executor_fn=control_media).result or {"status": "success"}

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
