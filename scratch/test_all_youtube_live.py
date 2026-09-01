import asyncio
import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath("."))

from backend.ai.agent import JarvisAgent

youtube_features_to_test = [
    ("Video Pause", "video pause karo"),
    ("Video Resume / Play", "video chalao"),
    ("10s Forward", "10 second aage karo"),
    ("10s Rewind", "10 second peeche karo"),
    ("Seek to Timestamp", "video ko 5 minute 30 second par lagao"),
    ("Speed Up (2x)", "speed badhao"),
    ("Speed Down (Slow)", "speed kam karo"),
    ("Fullscreen", "fullscreen karo"),
    ("Theater Mode", "theater mode lagao"),
    ("Miniplayer", "miniplayer chalao"),
    ("Captions / Subtitles", "subtitles on karo"),
    ("Replay from 0:00", "video replay karo"),
    ("Next Short", "agla short dikhao"),
    ("Previous Short", "pichla short dikhao"),
    ("Play 1st Video on Screen", "pehli video chalao"),
    ("Play 2nd Video on Screen", "dusri video chalao"),
    ("Play 3rd Video on Screen", "3rd video chalao"),
    ("Like Video", "video like karo"),
    ("Dislike Video", "video dislike karo"),
    ("Subscribe Channel", "channel subscribe karo"),
    ("Share Video", "video share karo"),
    ("View Comments", "comments dikhao"),
    ("Scroll Down", "scroll karo"),
    ("Scroll Up", "upar scroll karo"),
    ("Volume Up", "volume badhao"),
    ("Volume Down", "volume kam karo"),
    ("Set Exact Volume 65%", "volume 65 percent karo"),
    ("Mute Audio", "mute karo"),
    ("Unmute Audio", "unmute karo"),
    ("Open YouTube Search", "youtube par Arijit Singh ke gaane chalao"),
    ("Open YouTube Home", "youtube kholo"),
]

async def run_audit():
    print(f"============================================================")
    print(f"AUDITING ALL {len(youtube_features_to_test)} YOUTUBE AI & AUTOMATION FEATURES")
    print(f"============================================================\n")
    agent = JarvisAgent()
    passed = 0
    failed = 0
    
    for idx, (label, cmd) in enumerate(youtube_features_to_test, 1):
        try:
            resp = await agent.process_user_input(cmd)
            is_ok = resp.state.value != "ERROR" and not ("error" in resp.message.lower() and "execute karne mein error" in resp.message.lower())
            status = "[PASS]" if is_ok else "[FAIL]"
            if is_ok:
                passed += 1
            else:
                failed += 1
            print(f"[{idx:02d}/{len(youtube_features_to_test)}] {status} | Feature: '{label}' -> Command: '{cmd}' -> Response: '{resp.message}'")
        except Exception as exc:
            failed += 1
            print(f"[{idx:02d}/{len(youtube_features_to_test)}] [CRASH] | Feature: '{label}' -> Command: '{cmd}' -> Exception: {exc}")

    print("\n" + "=" * 60)
    print(f"YOUTUBE AUDIT COMPLETE: Total {len(youtube_features_to_test)} | Passed: {passed} | Failed: {failed}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_audit())
