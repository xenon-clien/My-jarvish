# =====================================================================
# JARVIS YOUTUBE V1 TO V2 CAPABILITY DIFF
# =====================================================================

| Capability | V1 Status | V2 Status | Classification | Notes |
|---|---|---|---|---|
| `youtube.open` | Supported | `youtube.open` | PRESERVED | Opens YouTube / focuses browser |
| `youtube.search` | Supported | `youtube.search` | PRESERVED | Searches query |
| `youtube.play_video` | Supported | `youtube.play_video` | PRESERVED | Supports query or ordinal |
| `youtube.play_short` | Required ordinal | `youtube.play_short` | PRESERVED | Ordinal made optional with default=1 |
| `youtube.next_short` | Supported | `youtube.next_short` | PRESERVED | Relative downward navigation |
| `youtube.previous_short`| Supported | `youtube.previous_short`| PRESERVED | Relative upward navigation |
| `youtube.pause` | Supported | `youtube.pause` | PRESERVED | Desired state: PAUSED |
| `youtube.resume` | Supported | `youtube.resume` | PRESERVED | Desired state: PLAYING |
| `youtube.fullscreen` | Blind Toggle | `youtube.set_fullscreen`| RENAMED / STATE | Explicit `enabled: bool` |
| `youtube.theater_mode` | Blind Toggle | `youtube.set_theater_mode`| MISSING_BY_ERROR RESTORED | Restored with 'T' hotkey in `media_tools.py` |
| `youtube.miniplayer` | Tool Only | `youtube.set_miniplayer`| RESTORED | Exposes 'I' hotkey in `media_tools.py` |
| `youtube.captions` | Blind Toggle | `youtube.set_captions` | RENAMED / STATE | Explicit `enabled: bool` |
| `youtube.speed_up` | Step only | `youtube.speed_up` | PRESERVED | Relative step |
| `youtube.speed_down` | Step only | `youtube.speed_down` | PRESERVED | Relative step |
| `youtube.playback_speed`| Missing | `youtube.set_playback_speed`| NEW / ENHANCED | Exact rate multiplier (1.5x, 2.0x, etc.) |
| `youtube.seek_forward` | 10s default | `youtube.seek_forward` | PRESERVED | Supports arbitrary seconds |
| `youtube.seek_backward`| 10s default | `youtube.seek_backward`| PRESERVED | Supports arbitrary seconds |
| `youtube.seek_timestamp`| String only | `youtube.seek_timestamp`| NORMALIZED | Normalized `seconds: int` |
| `youtube.volume_up` | Supported | `youtube.volume_up` | PRESERVED | Step volume increase |
| `youtube.volume_down` | Supported | `youtube.volume_down` | PRESERVED | Step volume decrease |
| `youtube.set_volume` | Tool Only | `youtube.set_volume` | RESTORED | Exposes direct 0-100 level |
| `youtube.mute` | Supported | `youtube.mute` | PRESERVED | Desired state: MUTED |
| `youtube.unmute` | Supported | `youtube.unmute` | PRESERVED | Desired state: UNMUTED |
| `youtube.like` | Blind Toggle | `youtube.set_like` | IDEMPOTENT | Never unlikes on positive like |
| `youtube.replay` | Supported | `youtube.replay` | PRESERVED | Seeks to 0:00 start |
