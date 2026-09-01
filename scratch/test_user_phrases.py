import sys
import os

sys.path.insert(0, os.path.abspath("."))

from backend.nlu.semantic_engine import SemanticIntentEngine
from backend.nlu.router import UniversalIntentRouter

commands = [
    "neeche scroll karo",
    "play first short",
    "play 1st short",
    "pehla short chalao",
    "first short play karo",
    "short chalao",
]

print("=" * 60)
print("TESTING USER PHRASES NLU & ROUTER")
print("=" * 60)

for cmd in commands:
    parsed = SemanticIntentEngine.parse(cmd)
    routes = UniversalIntentRouter.route(parsed)
    print(f"\nCommand: '{cmd}'")
    print(f"  Primary Intent: {parsed.primary_intent.value} (Confidence: {parsed.confidence:.2f})")
    print(f"  Entities: Ordinal={parsed.entities.ordinal_index}, App='{parsed.entities.application}', Query='{parsed.entities.query}'")
    if routes:
        for r in routes:
            print(f"  -> Routed Tool: '{r.tool_name}' Args: {r.arguments} Msg: '{r.immediate_response}'")
    else:
        print("  -> NO ROUTE FOUND!")
