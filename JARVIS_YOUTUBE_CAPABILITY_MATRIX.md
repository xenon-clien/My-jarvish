# =====================================================================
# JARVIS YOUTUBE CAPABILITY MATRIX (V2 CONTRACT)
# =====================================================================

| Capability ID | Category | Status | Supported Arguments | State Effect |
|---|---|---|---|---|
| `youtube.open` | Navigation | LIVE_VERIFIED | - | NAVIGATED_HOME |
| `youtube.search` | Search | LIVE_VERIFIED | `query: str` | SEARCH_RESULTS_DISPLAYED |
| `youtube.play_video` | Playback | LIVE_VERIFIED | `query: str`, `ordinal: int=1` | VIDEO_PLAYING |
| `youtube.play_short` | Shorts | LIVE_VERIFIED | `ordinal: int=1` | SHORT_PLAYING |
| `youtube.next_short` | Shorts | LIVE_VERIFIED | - | NAVIGATED_NEXT_SHORT |
| `youtube.previous_short`| Shorts | LIVE_VERIFIED | - | NAVIGATED_PREV_SHORT |
| `youtube.pause` | Playback | LIVE_VERIFIED | - | PAUSED |
| `youtube.resume` | Playback | LIVE_VERIFIED | - | PLAYING |
| `youtube.set_fullscreen`| Display | LIVE_VERIFIED | `enabled: bool=True` | FULLSCREEN_STATE_SET |
| `youtube.set_theater_mode`| Display | LIVE_VERIFIED | `enabled: bool=True` | THEATER_MODE_SET |
| `youtube.set_miniplayer`| Display | LIVE_VERIFIED | `enabled: bool=True` | MINIPLAYER_STATE_SET |
| `youtube.set_captions`| Subtitles | LIVE_VERIFIED | `enabled: bool=True` | CAPTIONS_STATE_SET |
| `youtube.set_playback_speed`| Speed | LIVE_VERIFIED | `rate: float` | SPEED_SET |
| `youtube.speed_up` | Speed | LIVE_VERIFIED | `step: float=0.25` | SPEED_INCREASED |
| `youtube.speed_down` | Speed | LIVE_VERIFIED | `step: float=0.25` | SPEED_DECREASED |
| `youtube.seek_forward`| Navigation | LIVE_VERIFIED | `seconds: int=10` | SEEKED_FORWARD |
| `youtube.seek_backward`| Navigation | LIVE_VERIFIED | `seconds: int=10` | SEEKED_BACKWARD |
| `youtube.seek_timestamp`| Navigation | LIVE_VERIFIED | `seconds: int`, `raw_timestamp: str` | SEEKED_TO_TIMESTAMP |
| `youtube.set_volume` | Audio | LIVE_VERIFIED | `level: int (0-100)` | VOLUME_LEVEL_SET |
| `youtube.volume_up` | Audio | LIVE_VERIFIED | `step: int=10` | VOLUME_INCREASED |
| `youtube.volume_down` | Audio | LIVE_VERIFIED | `step: int=10` | VOLUME_DECREASED |
| `youtube.mute` | Audio | LIVE_VERIFIED | - | MUTED |
| `youtube.unmute` | Audio | LIVE_VERIFIED | - | UNMUTED |
| `youtube.set_like` | Interaction | LIVE_VERIFIED | `enabled: bool=True` | LIKED_STATE_SET |
| `youtube.replay` | Navigation | LIVE_VERIFIED | - | REPLAYED |
