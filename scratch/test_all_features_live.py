import asyncio
import sys
import os

# Configure UTF-8 for stdout
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath("."))

from backend.ai.agent import JarvisAgent
from backend.diagnostics.engine import diagnostic_engine

test_commands = [
    "video pause karo",
    "video chalao",
    "scroll karo",
    "upar scroll karo",
    "10 second aage karo",
    "10 second peeche karo",
    "video ko 5 minute 30 second par lagao",
    "speed badhao",
    "speed kam karo",
    "fullscreen karo",
    "theater mode lagao",
    "miniplayer chalao",
    "subtitles on karo",
    "video replay karo",
    "agla short dikhao",
    "pichla short dikhao",
    "pehli video chalao",
    "dusri video chalao",
    "3rd video chalao",
    "video like karo",
    "video dislike karo",
    "channel subscribe karo",
    "video share karo",
    "comments dikhao",
    "volume badhao",
    "volume kam karo",
    "mute karo",
    "unmute karo",
    "chrome kholo",
    "notepad kholo",
    "calculator kholo",
    "faltu tabs band karo",
]

async def run_audit():
    print(f"Auditing all {len(test_commands)} JARVIS commands with live Agent and Diagnostic Engine...\n")
    agent = JarvisAgent()
    
    passed = 0
    failed = 0
    
    for idx, cmd in enumerate(test_commands, 1):
        try:
            resp = await agent.process_user_input(cmd)
            status = "[PASS]" if resp.state.value != "ERROR" else "[FAIL]"
            if resp.state.value != "ERROR":
                passed += 1
            else:
                failed += 1
            print(f"[{idx:02d}/{len(test_commands)}] {status} | '{cmd}' -> Response: '{resp.message}'")
        except Exception as exc:
            failed += 1
            print(f"[{idx:02d}/{len(test_commands)}] [CRASH] | '{cmd}' -> Exception: {exc}")

    print("\n" + "=" * 60)
    print(f"Audit Complete: Total {len(test_commands)} | Passed: {passed} | Failed: {failed}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_audit())
