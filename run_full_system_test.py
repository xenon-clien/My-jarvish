import sys
import os
sys.path.insert(0, r"c:\Users\shivam\Downloads\chatbot")

import time
from backend.ai.intent_engine import fast_intent_engine
from backend.tools.app_tools import app_registry
from backend.voice.speech_to_text import stt_manager
from backend.tools.browser_tools import get_weather_info

print("=" * 60)
print("🚀 J.A.R.V.I.S. FULL SYSTEM END-TO-END VERIFICATION TEST")
print("=" * 60)

test_suite = [
    ("Play right side second video", "click_right_side_video_2", "click_screen_video", {"index": 2, "section": "right"}),
    ("Right side 3rd video lagao", "click_right_side_video_3", "click_screen_video", {"index": 3, "section": "right"}),
    ("Forward this video 10 min 30 sec", "youtube_seek_timestamp", "control_media", {"action": "seek_timestamp", "time_str": "10m30s"}),
    ("Video like karo", "youtube_like", "control_media", {"action": "like"}),
    ("Channel subscribe karo", "youtube_subscribe", "control_media", {"action": "subscribe"}),
    ("Comments dikhao", "youtube_comments_down", "control_media", {"action": "comments_down"}),
    ("Shorts chalao", "open_youtube_shorts", "play_youtube_video", {"query": "", "wants_short": True}),
    ("Next short", "youtube_next_short", "click_screen_video", {"index": 1, "section": "shorts"}),
    ("Open discord", "open_discord", "open_application", {"app_name": "discord"}),
    ("Close discord", "close_discord", "close_application", {"app_name": "discord"}),
    ("Aaj punjab mein mausam kaisa hai", "weather_punjab", "get_weather_info", {"location": "Punjab"}),
    ("Delhi ka weather", "weather_delhi", "get_weather_info", {"location": "Delhi"}),
]

print("\n--- 1. Testing Fast Intent Matching ---")
all_intents_passed = True
for query, exp_intent, exp_tool, exp_args in test_suite:
    match = fast_intent_engine.match(query)
    if not match:
        print(f"❌ FAIL: '{query}' -> No match found!")
        all_intents_passed = False
        continue
    
    tool_ok = match.tool_calls and match.tool_calls[0].name == exp_tool
    args_ok = match.tool_calls and match.tool_calls[0].arguments == exp_args
    if tool_ok and args_ok:
        print(f"✅ PASS: '{query:36}' -> Tool: {exp_tool:20} Args: {exp_args}")
    else:
        print(f"❌ FAIL: '{query:36}' -> Got Tool: {match.tool_calls[0].name if match.tool_calls else None} Args: {match.tool_calls[0].arguments if match.tool_calls else None}")
        all_intents_passed = False

print("\n--- 2. Testing Live Multi-City Weather Tool ---")
w_res = get_weather_info("Punjab")
print(f"Punjab Weather Output: {w_res.get('message', 'No message')}")
weather_ok = w_res.get("status") == "success"
print(f"Weather Tool Status: {'✅ WORKING' if weather_ok else '❌ FAILED'}")

print("\n--- 3. Testing 95+ App Dynamic Resolution ---")
resolved_discord = app_registry.resolve_app("discord")
resolved_spotify = app_registry.resolve_app("spotify")
resolved_chrome = app_registry.resolve_app("chrome")
print(f"Discord Resolve: {resolved_discord['name'] if resolved_discord else 'None'}")
print(f"Spotify Resolve: {resolved_spotify['name'] if resolved_spotify else 'None'}")
print(f"Chrome Resolve:  {resolved_chrome['name'] if resolved_chrome else 'None'}")
apps_ok = resolved_discord and resolved_spotify and resolved_chrome
print(f"App Registry Status: {'✅ WORKING' if apps_ok else '❌ FAILED'}")

print("\n--- 4. Testing Microphone Hardware Availability ---")
mic_ok = stt_manager.is_microphone_available()
print(f"Microphone Hardware Detected: {'✅ YES' if mic_ok else '❌ NO'}")

print("\n--- 5. Right Sidebar Coordinates on 1366x768 (Live Layout) ---")
screen_w, screen_h = 1366, 768
v1_y = int(screen_h * 0.30)
v2_y = int(screen_h * 0.48)
v3_y = int(screen_h * 0.65)
v4_y = int(screen_h * 0.82)
click_x = int(screen_w * 0.78)
print(f"Video 1 Target: ({click_x}, {v1_y}) [Popatlal Taarak Mehta]")
print(f"Video 2 Target: ({click_x}, {v2_y}) [Fukra Insaan Assam Flood]")
print(f"Video 3 Target: ({click_x}, {v3_y}) [Delhi Se Haridwar On Bike]")
print(f"Video 4 Target: ({click_x}, {v4_y}) [Traitors 2 Parul Gulati]")

print("\n" + "=" * 60)
if all_intents_passed and weather_ok and apps_ok and mic_ok:
    print("🎉 ALL SYSTEMS ARE 100% OPERATIONAL, VERIFIED & WORKING!")
else:
    print("⚠️ SOME SYSTEMS FAILED VERIFICATION")
print("=" * 60)
