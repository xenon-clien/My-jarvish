import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath("."))

from backend.nlu.semantic_engine import SemanticIntentEngine
from backend.nlu.router import UniversalIntentRouter
from backend.ai.agent import JarvisAgent

commands_to_test = [
    "play first video",
    "play second video",
    "play 1st video",
    "pehli video chalao",
    "dusri video chalao",
    "first video chalao",
    "second video play karo",
    "right side wali video chalao",
    "right side 2nd video",
    "agla video chalao",
]

print("=" * 60)
print("DIAGNOSING 'PLAY FIRST VIDEO' & ORDINAL SELECTIONS")
print("=" * 60)

for cmd in commands_to_test:
    parsed = SemanticIntentEngine.parse(cmd)
    routes = UniversalIntentRouter.route(parsed)
    routed_tools = [r.tool_name for r in routes] if routes else []
    print(f"\nCommand: '{cmd}'")
    print(f"  Primary Intent: {parsed.primary_intent.value} (Confidence: {parsed.confidence:.2f})")
    print(f"  Entities: Ordinal={parsed.entities.ordinal_index}, Query='{parsed.entities.query}', App='{parsed.entities.application}', Position='{parsed.entities.position_relative}'")
    print(f"  Routed Tools: {routed_tools}")
    if routes:
        for r in routes:
            print(f"    -> Tool: '{r.tool_name}' Args: {r.arguments} Msg: '{r.immediate_response}'")
