# =====================================================================
# JARVIS YOUTUBE V2 SEMANTIC TEST RESULTS
# =====================================================================

## Test Execution Summary
- `tests/test_youtube_v2_contract.py`: **Passed (3/3 test suites)**
- `tests/test_youtube_hindi_semantic_engine.py`: **Passed (5/5 test suites)**
- `tests/test_vad_multi_stage.py`: **Passed (12/12 tests)**
- Full project regression test suite: **41 / 41 Passed (100%)**

## Semantic Slot Extraction Verification
1. **Verbs**: PLAY, SEARCH, NEXT, PREVIOUS, PAUSE, RESUME, FULLSCREEN, THEATER, MINIPLAYER, CAPTIONS, SPEED, SEEK, VOLUME, MUTE, UNMUTE, LIKE, REPLAY.
2. **Ordinals**: 1-based index (pehli/1st -> 1, dusri/2nd -> 2, teesri/3rd -> 3).
3. **Time / Duration Units**: "10 second" -> 10s, "ek minute" -> 60s, "2 minute" -> 120s, "bees second" -> 20s.
4. **Timestamps**: "2 minute 30 second" -> 150s (`02:30`), "1:35" -> 95s (`01:35`), "teen minute" -> 180s (`03:00`).
5. **Speed Target Rates**: "1.5x" / "dedh guna" -> 1.5, "2x" -> 2.0, "normal speed" -> 1.0.
6. **Negation**: "pause mat karna", "subtitle mat lagana" -> 100% intercepted as no-ops.
7. **Self-Corrections**: "second nahi first" -> parsed as ordinal 1; "pause nahi mute" -> parsed as mute.
