# =====================================================================
# JARVIS YOUTUBE V2 CANONICAL ADAPTER MAPPING
# =====================================================================

| Canonical Intent | YouTubeAdapter Method | Underlying Grounded Tool | Verification Strategy |
|---|---|---|---|
| `youtube.open` | `youtube_adapter.open()` | `play_youtube_video("")` | Foreground window title check |
| `youtube.search` | `youtube_adapter.search(query)` | `play_youtube_video(query)` | URL / Tab search check |
| `youtube.play_video` | `youtube_adapter.play_video(query, ordinal)` | `play_youtube_video` / `click_screen_video` | Foreground window title check |
| `youtube.play_short` | `youtube_adapter.play_short(ordinal)` | `click_screen_video(ordinal, 'shorts')` | Calibrated coordinate verification |
| `youtube.next_short` | `youtube_adapter.next_short()` | `control_media('next_short')` | VK_DOWN event |
| `youtube.previous_short`| `youtube_adapter.prev_short()` | `control_media('prev_short')` | VK_UP event |
| `youtube.pause` | `youtube_adapter.pause()` | `control_media('pause')` | Playback state -> PAUSED |
| `youtube.resume` | `youtube_adapter.resume()` | `control_media('play')` | Playback state -> PLAYING |
| `youtube.set_fullscreen`| `youtube_adapter.set_fullscreen(enabled)` | `control_media('fullscreen')` | 'F' key toggle |
| `youtube.set_theater_mode`| `youtube_adapter.set_theater_mode(enabled)` | `control_media('theater')` | 'T' key toggle |
| `youtube.set_miniplayer`| `youtube_adapter.set_miniplayer(enabled)` | `control_media('miniplayer')` | 'I' key toggle |
| `youtube.set_captions`| `youtube_adapter.set_captions(enabled)` | `control_media('captions')` | 'C' key toggle |
| `youtube.set_playback_speed`| `youtube_adapter.set_playback_speed(rate)` | `control_media('speed_up' / 'speed_down')` | Shift+> / Shift+< |
| `youtube.speed_up` | `youtube_adapter.speed_up(step)` | `control_media('speed_up')` | Shift+> |
| `youtube.speed_down` | `youtube_adapter.speed_down(step)` | `control_media('speed_down')` | Shift+< |
| `youtube.seek_forward` | `youtube_adapter.seek_forward(seconds)` | `control_media('seek_forward', seconds)` | 'L' key / VK_RIGHT |
| `youtube.seek_backward`| `youtube_adapter.seek_backward(seconds)` | `control_media('seek_backward', seconds)` | 'J' key / VK_LEFT |
| `youtube.seek_timestamp`| `youtube_adapter.seek_timestamp(seconds)` | `control_media('seek_timestamp', seconds)` | URL `&t=...s` injection |
| `youtube.set_volume` | `youtube_adapter.set_volume(level)` | `control_media('set_volume', level)` | Pycaw endpoint volume level |
| `youtube.volume_up` | `youtube_adapter.volume_up(step)` | `control_media('volume_up', step)` | VK_VOLUME_UP |
| `youtube.volume_down` | `youtube_adapter.volume_down(step)` | `control_media('volume_down', step)` | VK_VOLUME_DOWN |
| `youtube.mute` | `youtube_adapter.mute()` | `control_media('mute')` | VK_VOLUME_MUTE |
| `youtube.unmute` | `youtube_adapter.unmute()` | `control_media('unmute')` | VK_VOLUME_MUTE |
| `youtube.set_like` | `youtube_adapter.set_like(enabled)` | `control_media('like')` | Idempotent like state |
| `youtube.replay` | `youtube_adapter.replay()` | `control_media('replay')` | '0' Key seek to start |
