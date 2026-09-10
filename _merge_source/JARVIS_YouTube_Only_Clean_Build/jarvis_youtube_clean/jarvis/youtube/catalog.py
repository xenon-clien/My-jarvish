from __future__ import annotations

ACTIONS: dict[str, dict] = {
    "open": {"args": {}},
    "search": {"args": {"query": "string"}},
    "play_video": {"args": {"query": "string?", "ordinal": "integer?"}},
    "play_short": {"args": {"ordinal": "integer?"}},
    "next_short": {"args": {}},
    "previous_short": {"args": {}},
    "pause": {"args": {}},
    "resume": {"args": {}},
    "set_fullscreen": {"args": {"enabled": "boolean"}},
    "set_theater_mode": {"args": {"enabled": "boolean"}},
    "set_miniplayer": {"args": {"enabled": "boolean"}},
    "set_captions": {"args": {"enabled": "boolean"}},
    "set_playback_speed": {"args": {"rate": "number"}},
    "speed_up": {"args": {"step": "number?"}},
    "speed_down": {"args": {"step": "number?"}},
    "seek_forward": {"args": {"seconds": "number?"}},
    "seek_backward": {"args": {"seconds": "number?"}},
    "seek_timestamp": {"args": {"seconds": "number"}},
    "set_volume": {"args": {"level": "integer"}},
    "volume_up": {"args": {"step": "integer?"}},
    "volume_down": {"args": {"step": "integer?"}},
    "mute": {"args": {}},
    "unmute": {"args": {}},
    "set_like": {"args": {"enabled": "boolean?"}},
    "replay": {"args": {}},
}


def canonical_names() -> list[str]:
    return [f"youtube.{name}" for name in ACTIONS]
