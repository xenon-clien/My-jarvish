# =====================================================================
# JARVIS YOUTUBE 25 CAPABILITY MATRIX (CONTRACT V2.0)
# =====================================================================

| Intent ID | Semantic Slot Parser | Adapter Method | Execution Provider | Status |
|---|---|---|---|:---:|
| `youtube.open` | Verbs / Home | `open()` | Browser Tool (Win32) | **LIVE_VERIFIED** |
| `youtube.search` | Entity query | `search(query)` | Browser Tool (Win32) | **LIVE_VERIFIED** |
| `youtube.play_video` | Query / Ordinal | `play_video(query, ord)` | Browser Tool (Win32) | **LIVE_VERIFIED** |
| `youtube.play_short` | Ordinal 1..5 | `play_short(ordinal)` | Browser Tool (X=0.22..0.86) | **LIVE_VERIFIED** |
| `youtube.next_short` | Relative Next | `next_short()` | Media Tool (VK_DOWN) | **LIVE_VERIFIED** |
| `youtube.previous_short`| Relative Prev | `prev_short()` | Media Tool (VK_UP) | **LIVE_VERIFIED** |
| `youtube.pause` | Desired PAUSED | `pause()` | Media Tool (VK_SPACE / K) | **LIVE_VERIFIED** |
| `youtube.resume` | Desired PLAYING | `resume()` | Media Tool (VK_SPACE / K) | **LIVE_VERIFIED** |
| `youtube.set_fullscreen`| State ON/OFF | `set_fullscreen(enabled)`| Media Tool ('F' Key) | **LIVE_VERIFIED** |
| `youtube.set_theater_mode`| State ON/OFF | `set_theater_mode(enabled)`| Media Tool ('T' Key) | **LIVE_VERIFIED** |
| `youtube.set_miniplayer`| State ON/OFF | `set_miniplayer(enabled)`| Media Tool ('I' Key) | **LIVE_VERIFIED** |
| `youtube.set_captions` | State ON/OFF | `set_captions(enabled)`| Media Tool ('C' Key) | **LIVE_VERIFIED** |
| `youtube.set_playback_speed`| Rate 0.5..2.0 | `set_playback_speed(rate)`| Media Tool (Shift+> / Shift+<) | **LIVE_VERIFIED** |
| `youtube.speed_up` | Step +0.25 | `speed_up()` | Media Tool (Shift+>) | **LIVE_VERIFIED** |
| `youtube.speed_down` | Step -0.25 | `speed_down()` | Media Tool (Shift+<) | **LIVE_VERIFIED** |
| `youtube.seek_forward` | Duration (s) | `seek_forward(seconds)` | Media Tool ('L' / VK_RIGHT) | **LIVE_VERIFIED** |
| `youtube.seek_backward`| Duration (s) | `seek_backward(seconds)`| Media Tool ('J' / VK_LEFT) | **LIVE_VERIFIED** |
| `youtube.seek_timestamp`| Seconds offset | `seek_timestamp(seconds)`| Media Tool (URL Bar seek) | **LIVE_VERIFIED** |
| `youtube.set_volume` | Direct 0..100 | `set_volume(level)` | Media Tool (Pycaw Master) | **LIVE_VERIFIED** |
| `youtube.volume_up` | Step +10% | `volume_up()` | Media Tool (VK_VOLUME_UP) | **LIVE_VERIFIED** |
| `youtube.volume_down` | Step -10% | `volume_down()` | Media Tool (VK_VOLUME_DOWN) | **LIVE_VERIFIED** |
| `youtube.mute` | Desired MUTED | `mute()` | Media Tool (VK_VOLUME_MUTE) | **LIVE_VERIFIED** |
| `youtube.unmute` | Desired UNMUTED | `unmute()` | Media Tool (VK_VOLUME_MUTE) | **LIVE_VERIFIED** |
| `youtube.set_like` | Idempotent | `set_like(enabled)` | Media Tool (Like toggle) | **LIVE_VERIFIED** |
| `youtube.replay` | Start 00:00 | `replay()` | Media Tool ('0' Key) | **LIVE_VERIFIED** |
