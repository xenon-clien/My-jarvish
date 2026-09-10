# Live acceptance checklist

Run `JARVIS.bat` and test on the actual Chrome window. Do not mark a feature working only because a unit test passes.

1. `YouTube kholo`
2. `MrBeast search karo`
3. `pehli video chalao` and confirm the first visible video identity opened
4. Go home/search where Shorts shelf is visible, say `pehli short chala`; expected and actual video IDs must match
5. Repeat second and third Short
6. Repeat Short ordinal tests with Chrome resized
7. `pause`, `resume`
8. `fullscreen on`, `fullscreen off`
9. theater mode, captions, miniplayer where YouTube exposes controls
10. speed 1.5, seek forward/back, seek timestamp
11. YouTube volume and mute/unmute
12. Like only while signed in; adapter must return DEGRADED if state cannot be observed
13. replay
14. compound/natural paraphrases through Astra only after deterministic actions are stable

A feature is `LIVE_VERIFIED` only when the actual post-action browser state matches the request.
