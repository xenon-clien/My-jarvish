"""Canonical YouTube V2 Tools for JARVIS.

Registers all 25 canonical YouTube V2 contract intents as first-class JARVIS tools
with strict Pydantic argument validation and single ownership delegating to YouTubeAdapter.
"""
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from backend.tools.registry import PermissionLevel, ToolCategory, tool, default_registry
from backend.adapters.youtube_adapter import youtube_adapter


class YouTubeOpenArgs(BaseModel):
    query: Optional[str] = Field("", description="Optional search query or video title to open directly on YouTube.")

class YouTubeSearchArgs(BaseModel):
    query: str = Field(..., description="Search query string to search for on YouTube.")

class YouTubePlayVideoArgs(BaseModel):
    query: Optional[str] = Field("", description="Video title or topic to play.")
    ordinal: int = Field(1, description="1-based ordinal of the video candidate to play (e.g. 1 for first, 2 for second).")

class YouTubePlayShortArgs(BaseModel):
    ordinal: int = Field(1, description="1-based ordinal of the YouTube Short to play (e.g. 1 for first short, 2 for second short).")

class YouTubeEmptyArgs(BaseModel):
    pass

class YouTubeFullscreenArgs(BaseModel):
    enabled: bool = Field(True, description="True to enter fullscreen, False to exit fullscreen.")

class YouTubeTheaterModeArgs(BaseModel):
    enabled: bool = Field(True, description="True to enable theater mode, False to disable.")

class YouTubeMiniplayerArgs(BaseModel):
    enabled: bool = Field(True, description="True to enable miniplayer, False to disable.")

class YouTubeCaptionsArgs(BaseModel):
    enabled: bool = Field(True, description="True to turn captions/subtitles on, False to turn off.")

class YouTubePlaybackSpeedArgs(BaseModel):
    rate: float = Field(1.0, description="Playback speed multiplier (e.g. 0.5, 0.75, 1.0, 1.25, 1.5, 2.0).")

class YouTubeSpeedStepArgs(BaseModel):
    step: float = Field(0.25, description="Playback speed step delta (default: 0.25).")

class YouTubeSeekSecondsArgs(BaseModel):
    seconds: int = Field(10, description="Number of seconds to seek forward or backward.")

class YouTubeSeekTimestampArgs(BaseModel):
    seconds: int = Field(0, description="Exact timestamp position in seconds from start.")
    raw_timestamp: Optional[str] = Field("", description="Raw formatted timestamp string (e.g. '02:30').")

class YouTubeVolumeLevelArgs(BaseModel):
    level: int = Field(50, description="Volume percentage from 0 to 100.")

class YouTubeVolumeStepArgs(BaseModel):
    step: int = Field(10, description="Volume percentage step delta (default: 10).")

class YouTubeLikeArgs(BaseModel):
    enabled: bool = Field(True, description="True to like the video, False to remove like.")


# ── Canonical 25 YouTube Intent Tools ────────────────────────────────────────

CANONICAL_YOUTUBE_INTENTS = [
    ("youtube.open", YouTubeOpenArgs, "Open YouTube home page or search query in the browser."),
    ("youtube.search", YouTubeSearchArgs, "Search YouTube for a query string."),
    ("youtube.play_video", YouTubePlayVideoArgs, "Play a video query or select the N-th visible video candidate."),
    ("youtube.play_short", YouTubePlayShortArgs, "Play the 1-based N-th visible YouTube Short."),
    ("youtube.next_short", YouTubeEmptyArgs, "Advance down to the next YouTube Short."),
    ("youtube.previous_short", YouTubeEmptyArgs, "Return up to the previous YouTube Short."),
    ("youtube.pause", YouTubeEmptyArgs, "Pause playback idempotently."),
    ("youtube.resume", YouTubeEmptyArgs, "Resume playback idempotently."),
    ("youtube.set_fullscreen", YouTubeFullscreenArgs, "Set fullscreen mode ON or OFF."),
    ("youtube.set_theater_mode", YouTubeTheaterModeArgs, "Set theater mode ON or OFF."),
    ("youtube.set_miniplayer", YouTubeMiniplayerArgs, "Set miniplayer ON or OFF."),
    ("youtube.set_captions", YouTubeCaptionsArgs, "Turn subtitles/captions ON or OFF."),
    ("youtube.set_playback_speed", YouTubePlaybackSpeedArgs, "Set playback speed rate multiplier."),
    ("youtube.speed_up", YouTubeSpeedStepArgs, "Increase playback speed by step."),
    ("youtube.speed_down", YouTubeSpeedStepArgs, "Decrease playback speed by step."),
    ("youtube.seek_forward", YouTubeSeekSecondsArgs, "Fast forward playback by N seconds."),
    ("youtube.seek_backward", YouTubeSeekSecondsArgs, "Rewind playback by N seconds."),
    ("youtube.seek_timestamp", YouTubeSeekTimestampArgs, "Seek directly to an exact timestamp position."),
    ("youtube.set_volume", YouTubeVolumeLevelArgs, "Set audio volume level (0-100%)."),
    ("youtube.volume_up", YouTubeVolumeStepArgs, "Increase audio volume level."),
    ("youtube.volume_down", YouTubeVolumeStepArgs, "Decrease audio volume level."),
    ("youtube.mute", YouTubeEmptyArgs, "Mute audio output idempotently."),
    ("youtube.unmute", YouTubeEmptyArgs, "Unmute audio output idempotently."),
    ("youtube.set_like", YouTubeLikeArgs, "Like or unlike video idempotently."),
    ("youtube.replay", YouTubeEmptyArgs, "Restart playback from the beginning (00:00)."),
]


def _create_youtube_tool_executor(action_name: str):
    def executor(**kwargs) -> Dict[str, Any]:
        return youtube_adapter.execute_canonical(action_name, kwargs)
    return executor


# Register both dot and underscore formats in registry
for action_name, schema, desc in CANONICAL_YOUTUBE_INTENTS:
    exec_fn = _create_youtube_tool_executor(action_name)
    # Dot format (e.g. youtube.open)
    tool(
        name=action_name,
        description=desc,
        permission_level=PermissionLevel.LEVEL_0_SAFE,
        category=ToolCategory.MEDIA,
        args_schema=schema,
    )(exec_fn)

    # Underscore alias (e.g. youtube_open) for Gemini function declaration compatibility
    alias_name = action_name.replace(".", "_")
    tool(
        name=alias_name,
        description=desc,
        permission_level=PermissionLevel.LEVEL_0_SAFE,
        category=ToolCategory.MEDIA,
        args_schema=schema,
    )(exec_fn)
