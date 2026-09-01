import sys
sys.path.insert(0, r"c:\Users\shivam\Downloads\chatbot")

from backend.ai.intent_engine import fast_intent_engine
from backend.tools.app_tools import app_registry

print("=== FAST INTENT ENGINE VERIFICATION ===")
queries = [
    "play right side second video",
    "forward this video 10 min 30 sec",
    "video like karo",
    "channel subscribe karo",
    "comments dikhao",
    "shorts chalao",
    "next short",
    "open discord",
    "close discord"
]

all_ok = True
for q in queries:
    m = fast_intent_engine.match(q)
    if m:
        print(f"✅ PASS: {q:35} -> {m.intent_name:25} Tool: {m.tool_calls[0].name}")
    else:
        print(f"❌ FAIL: {q:35} -> NOT MATCHED")
        all_ok = False

print(f"\nEngine Status: {'🎉 ALL QUERIES 100% MATCHED' if all_ok else '❌ ISSUES FOUND'}")
