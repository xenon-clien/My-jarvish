import sys
import os

sys.path.insert(0, os.path.abspath("."))

from backend.voice.speech_to_text import _clean_phonetic_variations
from backend.nlu.semantic_engine import SemanticIntentEngine
from backend.nlu.router import UniversalIntentRouter

test_phrases = [
    "play first short",
    "play first shot",
    "play first shirt",
    "play first sort",
    "पहला शॉर्ट चलाओ",
    "पहला शॉट चलाओ",
    "पहला शॉर्ट्स चलाओ",
    "first short chalao",
    "first shot chalao",
    "short chalao",
    "shot chalao",
    "shorts chalao",
    "play first video",
    "पहला वीडियो चलाओ",
]

print("=" * 60)
print("TESTING PHONETIC NORMALIZATION & ROUTING FOR SHORTS")
print("=" * 60)

for p in test_phrases:
    cleaned = _clean_phonetic_variations(p)
    parsed = SemanticIntentEngine.parse(cleaned)
    routes = UniversalIntentRouter.route(parsed)
    tool_names = [r.tool_name for r in routes] if routes else []
    print(f"\nRaw Input:   '{p}'")
    print(f"Cleaned:     '{cleaned}'")
    print(f"Intent:      {parsed.primary_intent.value} (Confidence: {parsed.confidence:.2f})")
    print(f"Tool Route:  {tool_names}")
    if routes:
        print(f"  -> Args: {routes[0].arguments} | Response: '{routes[0].immediate_response}'")
