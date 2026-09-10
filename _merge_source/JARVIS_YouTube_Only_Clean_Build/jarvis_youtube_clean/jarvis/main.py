from __future__ import annotations

import argparse
import asyncio
import json

from jarvis.core.processor import CommandProcessor
from jarvis.voice.stt import SoundDeviceSTT
from jarvis.voice.tts import TTS


def _speakable(result) -> str:
    if result.action == "core.stop" and result.message == "STOP_REQUESTED":
        return "Shutting down, sir."
    if result.success:
        if result.action == "youtube.search":
            return "Search results ready hain, sir."
        if result.action == "youtube.play_short":
            return "Requested Short play ho gayi, sir."
        if result.action == "youtube.play_video":
            return "Requested video play ho gayi, sir."
        if result.action == "youtube.pause":
            return "Paused, sir."
        if result.action == "youtube.resume":
            return "Playing, sir."
        return result.message
    if result.status == "UNSUPPORTED":
        return result.message
    return f"Command verify nahi hui. {result.message}"


async def text_loop(processor: CommandProcessor):
    print("JARVIS YouTube-only text mode. /stop to exit.")
    while True:
        try:
            text = input("You > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        result = await processor.handle(text)
        print(f"JARVIS [{result.status}] > {result.message}")
        if result.actual:
            print(json.dumps(result.actual, indent=2, ensure_ascii=False, default=str))
        if result.action == "core.stop":
            break


async def voice_loop(processor: CommandProcessor):
    stt = SoundDeviceSTT()
    tts = TTS()
    print("JARVIS YouTube-only voice mode. Speak naturally. Ctrl+C to exit.")
    await tts.speak("Good evening, sir. JARVIS online hai. YouTube control ready hai.")
    while True:
        try:
            text = await asyncio.to_thread(stt.listen)
        except KeyboardInterrupt:
            break
        except Exception as exc:
            print(f"Voice input error: {type(exc).__name__}: {exc}")
            await asyncio.sleep(0.5)
            continue
        if not text:
            continue
        print(f"You > {text}")
        result = await processor.handle(text)
        print(f"JARVIS [{result.status}] > {result.message}")
        await tts.speak(_speakable(result))
        if result.action == "core.stop":
            break


async def amain(mode: str):
    p = CommandProcessor()
    try:
        if mode == "voice":
            await voice_loop(p)
        else:
            await text_loop(p)
    finally:
        await p.close()


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--voice", action="store_true")
    g.add_argument("--text", action="store_true")
    args = ap.parse_args()
    asyncio.run(amain("voice" if args.voice else "text"))


if __name__ == "__main__":
    main()
