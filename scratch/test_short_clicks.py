import sys
import os

sys.path.insert(0, os.path.abspath("."))

from backend.nlu.semantic_engine import SemanticIntentEngine
from backend.nlu.router import UniversalIntentRouter

commands = [
    "short chalao",
    "short pe click karo",
    "shorts pe click karo",
    "is short ko chalao",
    "ye short chalao",
    "short play karo",
    "pehla short chalao",
    "first short chalao",
    "play short",
    "short open karo",
    "shorts open karo",
    "iss short ko open karo",
    "video chalao",
    "click karo",
    "ispe click karo",
    "isko chalao",
]

print("=" * 60)
print("TESTING SHORTS & CLICK PHRASES NLU & ROUTER")
print("=" * 60)

for cmd in commands:
    parsed = SemanticIntentEngine.parse(cmd)
    routes = UniversalIntentRouter.route(parsed)
    print(f"\nCommand: '{cmd}'")
    print(f"  Primary Intent: {parsed.primary_intent.value} (Confidence: {parsed.confidence:.2f})")
    print(f"  Entities: Ordinal={parsed.entities.ordinal_index}, Position='{parsed.entities.position_relative}', Query='{parsed.entities.query}', Pronoun='{parsed.entities.pronoun_reference}'")
    if routes:
        for r in routes:
            print(f"  -> Routed Tool: '{r.tool_name}' Args: {r.arguments} Msg: '{r.immediate_response}'")
    else:
        print("  -> NO ROUTE FOUND!")
