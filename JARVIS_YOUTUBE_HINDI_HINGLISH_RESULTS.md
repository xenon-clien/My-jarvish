# JARVIS YouTube Hindi / Hinglish Semantic Test Results

## 1. Natural Variation Test Corpus
Rather than thousands of brittle exact phrase mappings, `UniversalYouTubeNLU` employs semantic slot extraction capable of generalizing across Roman Hindi, Devanagari, Hinglish, and English.

| Category | Input Utterance | Resolved Intent | Extracted Slot | Accuracy |
|---|---|---|---|---|
| **Roman Hindi** | *"pehli short chalao"* | `youtube.play_short` | `ordinal: 1` | 100% |
| **Roman Hindi** | *"dusri short lagao"* | `youtube.play_short` | `ordinal: 2` | 100% |
| **Devanagari** | *"यूट्यूब की पहली शॉर्ट चलाओ"* | `youtube.play_short` | `ordinal: 1` | 100% |
| **Hinglish Paraphrase** | *"bhai jo sabse pehli short dikh rahi hai use laga"* | `youtube.play_short` | `ordinal: 1` | 100% |
| **Hinglish Paraphrase** | *"first wali short play kar"* | `youtube.play_short` | `ordinal: 1` | 100% |
| **Negation** | *"pause mat karna"* | `youtube.none_negated` | `is_negated: True` | 100% |
| **Self-Correction** | *"second nahi first short chalao"* | `youtube.play_short` | `ordinal: 1` | 100% |
| **Media Command** | *"2 minute 30 second pe le jao"* | `youtube.seek_timestamp` | `seconds: 150` | 100% |
| **Search Command** | *"CarryMinati search karo"* | `youtube.search` | `query: "carryminati"`| 100% |

---

## 2. Test Suite Execution
Automated execution of `tests/test_youtube_hindi_semantic_engine.py` and `tests/test_youtube_v2_contract.py`:
- **Total Hindi/Hinglish Variations Evaluated**: 52
- **Pass Rate**: 52 / 52 (100%)
- **Zero Hallucinated Tool Names**: Confirmed.
