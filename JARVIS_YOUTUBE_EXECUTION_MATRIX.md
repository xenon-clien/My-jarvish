# =====================================================================
# JARVIS YOUTUBE ULTRA — GROUNDED EXECUTION MATRIX
# =====================================================================

## Grounded Execution Pipeline
```
Canonical Action + Arguments
  ↓
CommandProcessor Resource Lock ('youtube')
  ↓
Target Grounded Tool Execution
  - click_screen_video(index=ordinal, section='shorts') -> Calibrated 5-column grid (X=0.22, 0.38, 0.54, 0.70, 0.86)
  - control_media(action='next_short' | 'prev_short') -> Virtual Key Events
  - control_media(action='fullscreen') -> 'F' key toggle to match desired state
  - control_media(action='captions') -> 'C' key toggle to match desired state
  - control_media(action='speed_up' | 'speed_down') -> Shift + > / Shift + <
  - play_youtube_video(query=...) -> Single-tab URL search
  ↓
Execution Status: VERIFIED_SUCCESS
```

| Canonical Action | Grounded Tool | UI Target Coordinates / Keys | Verification Status |
|---|---|---|:---:|
| `youtube.play_short(1)` | `click_screen_video(1)` | `(X=0.22 * width, Y=0.46 * height)` | **PASS** |
| `youtube.play_short(2)` | `click_screen_video(2)` | `(X=0.38 * width, Y=0.46 * height)` | **PASS** |
| `youtube.play_short(3)` | `click_screen_video(3)` | `(X=0.54 * width, Y=0.46 * height)` | **PASS** |
| `youtube.next_short` | `control_media('next_short')` | `VK_DOWN` | **PASS** |
| `youtube.previous_short`| `control_media('prev_short')` | `VK_UP` | **PASS** |
| `youtube.pause` | `control_media('pause')` | `VK_SPACE` / `VK_MEDIA_PLAY_PAUSE` | **PASS** |
| `youtube.resume` | `control_media('play')` | `VK_SPACE` / `VK_MEDIA_PLAY_PAUSE` | **PASS** |
| `youtube.set_fullscreen`| `control_media('fullscreen')` | `F` Key | **PASS** |
| `youtube.set_captions` | `control_media('captions')` | `C` Key | **PASS** |
| `youtube.seek_forward` | `control_media('seek_forward')`| `VK_RIGHT` | **PASS** |
| `youtube.seek_backward`| `control_media('seek_backward')`| `VK_LEFT` | **PASS** |
