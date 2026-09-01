import sys
import os
sys.path.insert(0, r"c:\Users\shivam\Downloads\chatbot")

from backend.skills.registry import skill_registry
from backend.skills.context import relative_resolver, state_manager
from backend.skills.actions import action_engine
from backend.tools.skill_tools import analyze_app, test_app_health
from backend.ai.intent_engine import fast_intent_engine

print("=" * 65)
print("🧪 UNIVERSAL APP SKILL & DISCOVERY ENGINE TEST SUITE")
print("=" * 65)

# 1. Test Skill Registry Loading
print("\n--- 1. Testing Core Skills Registry ---")
skills = skill_registry.list_skills()
print(f"Total Loaded Application Skills: {len(skills)}")
for s in skills:
    print(f"  • {s['display_name']:30} -> {s['capability_count']:2d} Capabilities (v{s['version']})")

assert len(skills) >= 8, f"Expected at least 8 skills, got {len(skills)}"
print("✅ Core Skill Registry Loading: PASSED")

# 2. Test Analyze App Tool
print("\n--- 2. Testing 'analyze_app' Tool ---")
yt_analysis = analyze_app("youtube")
print("YouTube Analysis Output Preview:")
print("-" * 40)
print(yt_analysis.get("message"))
print("-" * 40)
assert yt_analysis.get("status") == "success"
assert yt_analysis.get("total_capabilities") >= 20
print("✅ App Discovery Analysis: PASSED")

# 3. Test App Health & Feature Matrix Tool
print("\n--- 3. Testing 'test_app_health' & Feature Matrix ---")
health_report = test_app_health("youtube")
print(f"Tests Run: {health_report.get('tests_run')} | Passed: {health_report.get('passed')} | Failed: {health_report.get('failed')}")
print(f"Status Message: {health_report.get('message')}")
assert health_report.get("failed") == 0
print("✅ App Health & Feature Matrix: PASSED")

# 4. Test Relative Command Resolver
print("\n--- 4. Testing Context & Relative Commands ---")
test_relative = [
    ("Play the second one", 2, None),
    ("Like it", None, "like"),
    ("Share it", None, "share"),
    ("Subscribe to it", None, "subscribe"),
    ("Scroll until comments", None, "comments_down"),
]

for phrase, exp_idx, exp_act in test_relative:
    res = relative_resolver.resolve(phrase)
    match_intent = fast_intent_engine.match(phrase)
    print(f"  Phrase: '{phrase:24}' -> Resolved Action: {res.get('action')}, Index: {res.get('ordinal_index')} | FastIntent: {match_intent.intent_name if match_intent else None}")
    if exp_idx:
        assert res.get("ordinal_index") == exp_idx
    if exp_act:
        assert res.get("action") == exp_act

print("✅ Relative Command Resolution: PASSED")

print("\n" + "=" * 65)
print("🎉 ALL UNIVERSAL APP SKILL & FEATURE MATRIX TESTS PASSED 100%!")
print("=" * 65)
