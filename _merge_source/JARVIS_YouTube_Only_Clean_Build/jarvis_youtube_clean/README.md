# JARVIS YouTube-Only Clean Build

This is a clean Windows-first JARVIS build focused on **one deep adapter: YouTube**.
The old 152-app idea is intentionally not exposed to the AI planner. The runtime profile enables only `youtube.*` capabilities.

## What is implemented

- Voice or text commands in Hindi/Hinglish/English.
- Fast deterministic parsing for common YouTube commands.
- Astra semantic fallback through the Experimental Labs OpenAI-compatible gateway.
- Gemini fallback when Astra is unavailable/quota-disabled, if configured.
- Persistent Astra provider state so confirmed quota/access exhaustion is not retried on every command.
- Semantic browser grounding through Chrome DevTools Protocol + Playwright.
- YouTube page observation and post-action verification.
- 25 canonical YouTube actions from the existing V2 contract:
  open, search, play_video, play_short, next_short, previous_short, pause, resume,
  set_fullscreen, set_theater_mode, set_miniplayer, set_captions, set_playback_speed,
  speed_up, speed_down, seek_forward, seek_backward, seek_timestamp, set_volume,
  volume_up, volume_down, mute, unmute, set_like, replay.

## Important limitation

No automation system can truthfully guarantee every future YouTube UI variant. The adapter verifies actual browser state and returns `DEGRADED`/`FAILED` rather than claiming success when it cannot observe the result.

## First setup

1. Copy `.env.example` to `.env`.
2. Put your **new** Experimental Labs API key in `.env`. Never paste it into chat or source files.
3. Optional: add a Gemini key/model as fallback.
4. Run `SETUP.bat` once.
5. Run `JARVIS.bat`.
6. A dedicated Chrome profile opens with remote debugging enabled. Sign into YouTube once in that profile if you want account actions such as Like.

The dedicated Chrome profile is stored under `%LOCALAPPDATA%\JARVIS\ChromeProfile` so your normal Chrome profile is not modified.

## Text mode

```bat
python -m jarvis.main --text
```

## Voice mode

```bat
python -m jarvis.main --voice
```

## Provider commands

- `/provider`
- `/provider reset astra`
- `/health`
- `/tools`
- `/stop`

## Example commands

- `YouTube kholo`
- `MrBeast search karo`
- `pehli video chalao`
- `pehli short chala`
- `agli short`
- `pause kar`
- `resume`
- `fullscreen on karo`
- `captions off karo`
- `speed 1.5 karo`
- `2 minute 30 second pe jao`
- `volume 40 kar do`
- `mute`
- `video like karo`
- `shuru se chalao`

## Architecture

USER -> Voice/Text -> CommandProcessor -> local parser -> Astra only if needed -> validated canonical intent -> YouTubeAdapter -> YouTubePageObserver -> execute -> verify -> result/TTS

The model never receives permission to invent raw mouse coordinates or arbitrary Python function names.
