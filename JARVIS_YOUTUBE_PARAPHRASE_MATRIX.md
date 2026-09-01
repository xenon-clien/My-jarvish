# =====================================================================
# JARVIS YOUTUBE ULTRA — HARDENED PARAPHRASE MATRIX
# =====================================================================

| Intent Family | Sample Natural Utterances | Canonical Action | Structured Arguments | Desired State |
|---|---|---|---|---|
| **Play First Short** | "short chalao" / "pehli short chalao" / "first short laga do" / "पहली शॉर्ट चलाओ" | `youtube.play_short` | `ordinal: 1` | `SHORT_PLAYING` |
| **Play N-th Short** | "doosri short chalao" / "teesri short chala" / "तीसरी शॉर्ट लगाओ" | `youtube.play_short` | `ordinal: 2..5` | `SHORT_PLAYING` |
| **Next Short** | "next short" / "agla short chala" / "short niche scroll karo" / "अगला शॉर्ट चलाओ" | `youtube.next_short` | - | `NAVIGATED_NEXT_SHORT` |
| **Previous Short** | "pichla short" / "previous short chala" / "पिछला शॉर्ट चलाओ" | `youtube.previous_short` | - | `NAVIGATED_PREV_SHORT` |
| **Pause** | "pause" / "rok do" / "video rok do" / "पॉज करो" | `youtube.pause` | - | `PAUSED` |
| **Resume** | "resume" / "chala do" / "चालू करो" | `youtube.resume` | - | `PLAYING` |
| **Fullscreen ON** | "fullscreen karo" / "screen badi karo" / "फुलस्क्रीन करो" | `youtube.set_fullscreen` | `enabled: True` | `FULLSCREEN_ON` |
| **Fullscreen OFF** | "fullscreen hatao" / "exit fullscreen" / "fullscreen band karo" | `youtube.set_fullscreen` | `enabled: False` | `FULLSCREEN_OFF` |
| **Captions ON** | "captions on karo" / "subtitles lagao" / "subtitle chalu karo" | `youtube.set_captions` | `enabled: True` | `CAPTIONS_ON` |
| **Captions OFF** | "captions off karo" / "caption band karo" / "subtitles hatao" | `youtube.set_captions` | `enabled: False` | `CAPTIONS_OFF` |
| **Set Speed** | "1.5x speed kar do" / "speed dedh guna karo" / "2x pe chalao" / "normal speed" | `youtube.set_playback_speed` | `rate: 1.5, 2.0, 1.0` | `SPEED_SET` |
| **Seek Timestamp** | "2 minute 30 second pe le jao" / "1:35 pe chalao" / "teen minute pe jao" | `youtube.seek_timestamp` | `timestamp: '02:30', seconds: 150` | `SEEKED_TO_TIMESTAMP` |
| **Seek Relative** | "10 second aage" / "ek minute aage" / "20 sec peeche" / "2 minute peeche" | `youtube.seek_forward / backward` | `seconds: 10, 60, 20, 120` | `SEEKED_RELATIVE` |
| **Volume & Mute** | "volume badhao" / "volume kam karo" / "mute karo" / "unmute karo" | `youtube.volume_up / down / mute / unmute` | `step: 10` | `VOLUME_STATE` |
| **Negation** | "pause mat karna" / "video mat rokna" / "subtitle mat lagana" | `youtube.none_negated` | `is_negated: True` | `NO_OP_CANCELLED` |
| **Self-Correction** | "second nahi first short chalao" / "third... nahi second wali chalao" | `youtube.play_short` | `ordinal: 1, 2` | `CORRECTED_TARGET` |
| **Search Creator** | "YouTube pe MrBeast search karo" / "CarryMinati search karo" | `youtube.search` | `query: 'mrbeast', 'carryminati'` | `SEARCH_RESULTS` |
