"""Deep diagnostic script to verify every file, module, syntax, and tool in JARVIS."""
import sys
import os
import py_compile
from pathlib import Path

root = Path(r"c:\Users\shivam\Downloads\chatbot")
sys.path.insert(0, str(root))

print("==================================================")
print("🔍 1. COMPILING ALL PYTHON FILES FOR SYNTAX ERRORS")
print("==================================================")
error_files = []
for py_file in root.rglob("*.py"):
    if ".git" in str(py_file) or "__pycache__" in str(py_file):
        continue
    try:
        py_compile.compile(str(py_file), doraise=True)
    except Exception as e:
        print(f"❌ SYNTAX/COMPILE ERROR IN: {py_file}\n   -> {e}")
        error_files.append((py_file, e))

if not error_files:
    print("✅ ZERO syntax or compilation errors found in any Python file!\n")
else:
    print(f"⚠️ Found {len(error_files)} corrupt or broken files!\n")

print("==================================================")
print("🔍 2. TESTING ALL SYSTEM MODULE IMPORTS")
print("==================================================")
try:
    import backend.core.config
    import backend.core.logger
    import backend.core.permissions
    import backend.database.database
    import backend.database.repositories
    import backend.tools.registry
    import backend.tools.browser_tools
    import backend.tools.media_tools
    import backend.tools.whatsapp_tools
    import backend.tools.app_tools
    import backend.tools.skill_tools
    import backend.skills.models
    import backend.skills.actions
    import backend.skills.context
    import backend.skills.registry
    import backend.nlu.models
    import backend.nlu.normalizer
    import backend.nlu.entities
    import backend.nlu.semantic_engine
    import backend.nlu.router
    import backend.nlu.debug
    import backend.ai.agent
    import backend.ai.intent_engine
    print("✅ ALL modules imported cleanly with 0 runtime errors!\n")
except Exception as e:
    print(f"❌ IMPORT FAILURE: {e}\n")

print("==================================================")
print("🔍 3. INSPECTING REGISTERED TOOLS")
print("==================================================")
from backend.tools.registry import default_registry
tools = default_registry.list_tools()
print(f"Total tools registered in registry: {len(tools)}")
for t in tools:
    print(f"  • {t.name} (Category: {t.category})")

print("\n==================================================")
print("🔍 4. TESTING COMPLETE YOUTUBE ACTION SUITE NLU")
print("==================================================")
from backend.nlu import SemanticIntentEngine, UniversalIntentRouter, UniversalIntent

test_cases = [
    ("YouTube kholo", UniversalIntent.OPEN_APP),
    ("YT chala de", UniversalIntent.OPEN_APP),
    ("YouTube open kar", UniversalIntent.OPEN_APP),
    ("Machine learning search karo", UniversalIntent.SEARCH),
    ("Python tutorial chalao", UniversalIntent.OPEN_APP),
    ("Video pause kar", UniversalIntent.PAUSE),
    ("Video chalao", UniversalIntent.PLAY),
    ("Agla video laga", UniversalIntent.NEXT_MEDIA),
    ("Pichla video chala", UniversalIntent.PREVIOUS_MEDIA),
    ("10 seconds aage kar", UniversalIntent.SEEK_FORWARD),
    ("10 second peeche kar", UniversalIntent.SEEK_BACKWARD),
    ("Video like karo", UniversalIntent.LIKE),
    ("Channel subscribe karo", UniversalIntent.SUBSCRIBE),
    ("Video share karo", UniversalIntent.SHARE),
    ("Comments dikhao", UniversalIntent.COMMENTS_VIEW),
    ("Wapas video par scroll karo", UniversalIntent.COMMENTS_HIDE),
    ("Volume badhao", UniversalIntent.VOLUME_UP),
    ("Volume kam karo", UniversalIntent.VOLUME_DOWN),
    ("Mute karo", UniversalIntent.MUTE_AUDIO),
    ("Second video chala", UniversalIntent.SELECT),
    ("Harsh ko voice call lagao", UniversalIntent.CALL_CONTACT),
    ("Harsh ko message karo hello", UniversalIntent.SEND_MESSAGE),
    ("Message karo harsh ko", UniversalIntent.SEND_MESSAGE),
]

passed = 0
for text, expected_intent in test_cases:
    res = SemanticIntentEngine.parse(text)
    routed = UniversalIntentRouter.route(res)
    is_ok = (res.primary_intent == expected_intent) and (routed is not None and len(routed) > 0)
    status = "✅" if is_ok else "❌"
    print(f"{status} '{text}' -> Intent: {res.primary_intent.value} | Tool: {routed[0].tool_name if routed else 'None'}")
    if is_ok:
        passed += 1

print(f"\nScore: {passed}/{len(test_cases)} tests passed!")
print("==================================================")
