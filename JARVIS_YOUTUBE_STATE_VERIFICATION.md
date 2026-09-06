# JARVIS YouTube Closed-Loop State Verification

## 1. State Verification Contract
Every YouTube action executes a closed-loop verification cycle:
`OBSERVE BEFORE -> EXECUTE ONLY IF REQUIRED -> OBSERVE AFTER -> VERIFY EFFECT`

---

## 2. Idempotent Playback Controls (Phase 17 & 25)

### `youtube.pause`
- If currently `PAUSED`: Action is a no-op success. Returns `LIVE_VERIFIED` with message *"Video pehle se hi paused hai Boss."*
- If currently `PLAYING`: Sends pause event, verifies resulting state.

### `youtube.resume`
- If currently `PLAYING`: Action is a no-op success. Returns `LIVE_VERIFIED` with message *"Video pehle se hi chal rahi hai Boss."*
- If currently `PAUSED`: Sends resume event, verifies resulting state.

### `youtube.set_fullscreen`
- Observes monitor resolution and window bounding rectangle.
- If already in requested fullscreen state: No-op success. Avoids blind toggling.

### `youtube.set_like`
- If user requests *"video like karo"* and video is already liked:
  - **CRITICAL FIX**: Does NOT click or toggle unlike!
  - Returns `LIVE_VERIFIED` with message *"Video pehle se hi liked hai Boss."*

---

## 3. Directional Delta Verification (Phase 18)
For `youtube.next_short` and `youtube.previous_short`:
- `BEFORE video_id` is recorded.
- Navigation command dispatched.
- `AFTER video_id` is recorded.
- Verified condition: `AFTER video_id != BEFORE video_id` and both IDs are valid.
