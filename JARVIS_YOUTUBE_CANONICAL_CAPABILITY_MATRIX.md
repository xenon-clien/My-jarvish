# JARVIS YouTube Canonical Capability Matrix (25 Intents)

All 25 canonical YouTube V2 contract intents are inventoried below with their single execution owner, observer, verifier, and verified status.

| # | Canonical Intent | Arguments | Single Execution Owner | State Observer | Closed-Loop Verifier | Verification Status |
|---|---|---|---|---|---|---|
| 1 | `youtube.open` | `query: str = ""` | `YouTubeAdapter.open` | `YouTubePageObserver` | URL / Title check | `LIVE_VERIFIED` |
| 2 | `youtube.search` | `query: str` | `YouTubeAdapter.search` | `YouTubePageObserver` | Search results URL check | `LIVE_VERIFIED` |
| 3 | `youtube.play_video` | `query: str = "", ordinal: int = 1` | `YouTubeAdapter.play_video` | `YouTubePageObserver` | Candidate ID match | `LIVE_VERIFIED` |
| 4 | `youtube.play_short` | `ordinal: int = 1` | `YouTubeAdapter.play_short` | `YouTubePageObserver` | Candidate ID match (`EXPECTED == ACTUAL`) | `LIVE_VERIFIED` |
| 5 | `youtube.next_short` | None | `YouTubeAdapter.next_short` | `YouTubePageObserver` | Delta check (`AFTER != BEFORE`) | `LIVE_VERIFIED` |
| 6 | `youtube.previous_short`| None | `YouTubeAdapter.prev_short` | `YouTubePageObserver` | Delta check (`AFTER != BEFORE`) | `LIVE_VERIFIED` |
| 7 | `youtube.pause` | None | `YouTubeAdapter.pause` | `YouTubePageObserver` | Playback state check (Idempotent) | `LIVE_VERIFIED` |
| 8 | `youtube.resume` | None | `YouTubeAdapter.resume` | `YouTubePageObserver` | Playback state check (Idempotent) | `LIVE_VERIFIED` |
| 9 | `youtube.set_fullscreen`| `enabled: bool = True` | `YouTubeAdapter.set_fullscreen`| `YouTubePageObserver` | Screen geometry check (Idempotent)| `LIVE_VERIFIED` |
| 10| `youtube.set_theater_mode`| `enabled: bool = True`| `YouTubeAdapter.set_theater_mode`| `YouTubePageObserver` | Execution response verification | `INTEGRATION_TESTED` |
| 11| `youtube.set_miniplayer`| `enabled: bool = True` | `YouTubeAdapter.set_miniplayer`| `YouTubePageObserver` | Execution response verification | `INTEGRATION_TESTED` |
| 12| `youtube.set_captions` | `enabled: bool = True` | `YouTubeAdapter.set_captions` | `YouTubePageObserver` | Keystroke state dispatch | `INTEGRATION_TESTED` |
| 13| `youtube.set_playback_speed`| `rate: float = 1.0`| `YouTubeAdapter.set_playback_speed`| `YouTubePageObserver` | Multiplier rate check | `INTEGRATION_TESTED` |
| 14| `youtube.speed_up` | `step: float = 0.25` | `YouTubeAdapter.speed_up` | `YouTubePageObserver` | Incremental rate check | `INTEGRATION_TESTED` |
| 15| `youtube.speed_down` | `step: float = 0.25` | `YouTubeAdapter.speed_down` | `YouTubePageObserver` | Decremental rate check | `INTEGRATION_TESTED` |
| 16| `youtube.seek_forward` | `seconds: int = 10` | `YouTubeAdapter.seek_forward` | `YouTubePageObserver` | Keystroke duration step | `LIVE_VERIFIED` |
| 17| `youtube.seek_backward`| `seconds: int = 10` | `YouTubeAdapter.seek_backward`| `YouTubePageObserver` | Keystroke duration step | `LIVE_VERIFIED` |
| 18| `youtube.seek_timestamp`| `seconds: int, raw_timestamp: str`| `YouTubeAdapter.seek_timestamp`| `YouTubePageObserver` | Normalized timestamp navigation | `INTEGRATION_TESTED` |
| 19| `youtube.set_volume` | `level: int = 50` | `YouTubeAdapter.set_volume` | `YouTubePageObserver` | Endpoint volume level check | `LIVE_VERIFIED` |
| 20| `youtube.volume_up` | `step: int = 10` | `YouTubeAdapter.volume_up` | `YouTubePageObserver` | Hardware step up | `LIVE_VERIFIED` |
| 21| `youtube.volume_down` | `step: int = 10` | `YouTubeAdapter.volume_down` | `YouTubePageObserver` | Hardware step down | `LIVE_VERIFIED` |
| 22| `youtube.mute` | None | `YouTubeAdapter.mute` | `YouTubePageObserver` | Hardware mute status (Idempotent) | `LIVE_VERIFIED` |
| 23| `youtube.unmute` | None | `YouTubeAdapter.unmute` | `YouTubePageObserver` | Hardware unmute status (Idempotent)| `LIVE_VERIFIED` |
| 24| `youtube.set_like` | `enabled: bool = True` | `YouTubeAdapter.set_like` | `YouTubePageObserver` | Like status check (Idempotent) | `LIVE_VERIFIED` |
| 25| `youtube.replay` | None | `YouTubeAdapter.replay` | `YouTubePageObserver` | Reset to start position (00:00) | `LIVE_VERIFIED` |
