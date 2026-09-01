import sys
import os

sys.path.insert(0, os.path.abspath("."))

from backend.voice.speech_to_text import _clean_phonetic_variations
from backend.nlu.semantic_engine import SemanticIntentEngine
from backend.nlu.router import UniversalIntentRouter

pure_hindi_phrases = [
    "pehli video pe click karo",
    "dusri video pe click karo",
    "teesri video pe click karo",
    "pehla video chalao",
    "dusra video chalao",
    "pehli video chalao",
    "dusri video chalao",
    "pehla short chalao",
    "pehli short chalao",
    "pehla short pe click karo",
    "neeche scroll karo",
    "thoda neeche scroll karo",
    "upar scroll karo",
    "video rok do",
    "video chala do",
    "aage badhao",
    "peeche karo",
    "aawaz badhao",
    "aawaz kam karo",
    "fullscreen karo",
    "chhota karo",
    "subtitles chalu karo",
    "scroll karo aur pehli video chalao",
    "scroll karo aur pehla short chalao",
]

print("=" * 60)
print("AUDITING PURE HINDI COMMAND PARSING & ROUTING")
print("=" * 60)

for p in pure_hindi_phrases:
    cleaned = _clean_phonetic_variations(p)
    parsed = SemanticIntentEngine.parse(cleaned)
    routes = UniversalIntentRouter.route(parsed)
    tool_names = [r.tool_name for r in routes] if routes else []
    print(f"\nHindi Input: '{p}'")
    print(f"  Cleaned:   '{cleaned}'")
    print(f"  Intent:    {parsed.primary_intent.value} (Confidence: {parsed.confidence:.2f})")
    print(f"  Entities:  Ordinal={parsed.entities.ordinal_index}, Position='{parsed.entities.position_relative}', Query='{parsed.entities.query}'")
    print(f"  Tools:     {tool_names}")
    if routes:
        for r in routes:
            print(f"    -> Tool: {r.tool_name} | Args: {r.arguments} | Msg: '{r.immediate_response}'")
    else:
        print("    -> NO ROUTE!")
