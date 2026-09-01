import sys
import os

sys.path.insert(0, os.path.abspath("."))

from backend.nlu.semantic_engine import SemanticIntentEngine
from backend.nlu.router import UniversalIntentRouter

commands = [
    "pehla short chalao",
    "pehli video pe click karo",
    "neeche scroll karo",
    "video pause karo",
    "video chala do",
    "aage badhao",
    "pehla short",
    "short chalao",
    "play first short",
    "play first video",
    "scroll karo aur pehla short chalao",
]

print("=" * 60)
print("LIVE VALIDATION OF ALL USER COMMANDS")
print("=" * 60)

for cmd in commands:
    p = SemanticIntentEngine.parse(cmd)
    routes = UniversalIntentRouter.route(p)
    tools = [r.tool_name for r in routes] if routes else []
    args = [r.arguments for r in routes] if routes else []
    print(f"\nCommand: '{cmd}'")
    print(f"  -> Intent: {p.primary_intent.value} | Confidence: {p.confidence:.2f}")
    print(f"  -> Routed: {tools} with args: {args}")
    if routes:
        print(f"  -> JARVIS speaks: '{routes[0].immediate_response}'")
