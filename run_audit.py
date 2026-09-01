import sys
import os
from pathlib import Path

root = Path(r"c:\Users\shivam\Downloads\chatbot")
sys.path.insert(0, str(root))

report_file = r"c:\Users\shivam\Downloads\chatbot\diagnostic_report.txt"

with open(report_file, "w", encoding="utf-8") as f:
    f.write("=== DEEP CODEBASE & YOUTUBE PIPELINE AUDIT ===\n\n")
    
    from backend.nlu import SemanticIntentEngine, UniversalIntentRouter, UniversalIntent
    test_cases = [
        ("YouTube kholo", UniversalIntent.OPEN_APP),
        ("YT chala de", UniversalIntent.OPEN_APP),
        ("YouTube open kar", UniversalIntent.OPEN_APP),
        ("Machine learning search karo", UniversalIntent.SEARCH),
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
        status = "PASSED" if is_ok else "FAILED"
        tool_name = routed[0].tool_name if routed else "None"
        f.write(f"[{status}] '{text}' -> Intent: {res.primary_intent.value} | Tool: {tool_name}\n")
        if is_ok:
            passed += 1

    f.write(f"\nTotal: {passed}/{len(test_cases)} passed.\n")

print("Report written.")
