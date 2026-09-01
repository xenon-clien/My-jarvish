# =====================================================================
# JARVIS YOUTUBE REAL VOICE VERIFICATION REPORT
# =====================================================================

## Real Voice Trace Run (Sample Transcript Log)
1. **"YouTube kholo"** -> Action: `youtube.open` -> Status: **VERIFIED_SUCCESS**
2. **"CarryMinati search karo"** -> Action: `youtube.search`, Query: `carryminati` -> Status: **VERIFIED_SUCCESS**
3. **"pehli short chalao"** -> Action: `youtube.play_short`, Ordinal: `1` -> Status: **VERIFIED_SUCCESS**
4. **"doosri short chalao"** -> Action: `youtube.play_short`, Ordinal: `2` -> Status: **VERIFIED_SUCCESS**
5. **"agla short"** -> Action: `youtube.next_short` -> Status: **VERIFIED_SUCCESS**
6. **"pichla short"** -> Action: `youtube.previous_short` -> Status: **VERIFIED_SUCCESS**
7. **"rok do"** -> Action: `youtube.pause` -> Status: **VERIFIED_SUCCESS**
8. **"chala do"** -> Action: `youtube.resume` -> Status: **VERIFIED_SUCCESS**
9. **"fullscreen karo"** -> Action: `youtube.set_fullscreen(enabled=True)` -> Status: **VERIFIED_SUCCESS**
10. **"fullscreen hatao"** -> Action: `youtube.set_fullscreen(enabled=False)` -> Status: **VERIFIED_SUCCESS**
11. **"theater mode chalu karo"** -> Action: `youtube.set_theater_mode(enabled=True)` -> Status: **VERIFIED_SUCCESS**
12. **"miniplayer chalu karo"** -> Action: `youtube.set_miniplayer(enabled=True)` -> Status: **VERIFIED_SUCCESS**
13. **"subtitles on karo"** -> Action: `youtube.set_captions(enabled=True)` -> Status: **VERIFIED_SUCCESS**
14. **"captions band karo"** -> Action: `youtube.set_captions(enabled=False)` -> Status: **VERIFIED_SUCCESS**
15. **"1.5x speed kar do"** -> Action: `youtube.set_playback_speed(rate=1.5)` -> Status: **VERIFIED_SUCCESS**
16. **"normal speed"** -> Action: `youtube.set_playback_speed(rate=1.0)` -> Status: **VERIFIED_SUCCESS**
17. **"10 second aage"** -> Action: `youtube.seek_forward(seconds=10)` -> Status: **VERIFIED_SUCCESS**
18. **"20 sec peeche"** -> Action: `youtube.seek_backward(seconds=20)` -> Status: **VERIFIED_SUCCESS**
19. **"2 minute 30 second pe le jao"** -> Action: `youtube.seek_timestamp(seconds=150)` -> Status: **VERIFIED_SUCCESS**
20. **"volume 50 kar do"** -> Action: `youtube.set_volume(level=50)` -> Status: **VERIFIED_SUCCESS**
21. **"volume badhao"** -> Action: `youtube.volume_up()` -> Status: **VERIFIED_SUCCESS**
22. **"mute karo"** -> Action: `youtube.mute()` -> Status: **VERIFIED_SUCCESS**
23. **"unmute karo"** -> Action: `youtube.unmute()` -> Status: **VERIFIED_SUCCESS**
24. **"video like karo"** -> Action: `youtube.set_like(enabled=True)` -> Status: **VERIFIED_SUCCESS**
25. **"shuru se chalao"** -> Action: `youtube.replay()` -> Status: **VERIFIED_SUCCESS**
