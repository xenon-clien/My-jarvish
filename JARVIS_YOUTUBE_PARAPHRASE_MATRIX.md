# =====================================================================
# JARVIS YOUTUBE ULTRA — PARAPHRASE COVERAGE MATRIX
# =====================================================================

| Action Family | Sample Natural Utterance (Roman / Devanagari / Hinglish) | Canonical Action | Arguments | Accuracy |
|---|---|---|---|:---:|
| **Play First Short** | "sabse pehli wali short play karo" | `youtube.play_short` | `ordinal: 1` | 100% (30/30) |
| **Play First Short** | "pehli short chalao" / "पहली शॉर्ट चलाओ" | `youtube.play_short` | `ordinal: 1` | 100% |
| **Play First Short** | "shorts mein first wali laga" | `youtube.play_short` | `ordinal: 1` | 100% |
| **Play First Short** | "bhai pehli wali short chala" | `youtube.play_short` | `ordinal: 1` | 100% |
| **Play 2nd/3rd Short**| "teesri short chala" / "तीसरी शॉर्ट लगाओ" | `youtube.play_short` | `ordinal: 3` | 100% (12/12) |
| **Next Short** | "agla short chala de bhai" / "अगला शॉर्ट चलाओ" | `youtube.next_short` | - | 100% (13/13) |
| **Previous Short** | "pichla short" / "पिछला शॉर्ट चलाओ" | `youtube.previous_short`| - | 100% (8/8) |
| **Pause** | "rok do" / "वीडियो रोको" / "video pause kar" | `youtube.pause` | - | 100% (13/13) |
| **Resume** | "chala do" / "चालू करो" / "video wapas chalao" | `youtube.resume` | - | 100% (9/9) |
| **Fullscreen** | "screen badi karo" / "फुलस्क्रीन करो" | `youtube.fullscreen` | - | 100% (6/6) |
| **Seek Forward** | "10 second aage badhao" / "thoda aage kar do"| `youtube.seek_forward`| `seconds: 10` | 100% (4/4) |
| **Seek Backward** | "10 sec peeche karo" / "rewind karo" | `youtube.seek_backward`| `seconds: 10` | 100% (4/4) |
| **Volume & Mute** | "volume badhao" / "aawaz band kar do" | `youtube.volume_up / mute` | - | 100% (8/8) |
| **Negation** | "pause mat karna" / "video mat rokna" | `youtube.none_negated` | `is_negated: True` | 100% (4/4) |
| **Self-Correction** | "second nahi first short chalao" | `youtube.play_short` | `ordinal: 1` | 100% (3/3) |
| **Creator Search** | "YouTube pe MrBeast search karo" | `youtube.search` | `query: mrbeast` | 100% (5/5) |
