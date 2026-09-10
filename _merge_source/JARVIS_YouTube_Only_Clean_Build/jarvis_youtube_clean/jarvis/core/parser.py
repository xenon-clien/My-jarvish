from __future__ import annotations

import re
from jarvis.core.models import Intent

ORDINAL_WORDS = {
    "first": 1, "1st": 1, "pehli": 1, "pehla": 1, "pahli": 1, "पहली": 1, "पहला": 1,
    "second": 2, "2nd": 2, "dusri": 2, "dusra": 2, "doosri": 2, "दूसरी": 2, "दूसरा": 2,
    "third": 3, "3rd": 3, "teesri": 3, "teesra": 3, "तीसरी": 3, "तीसरा": 3,
    "fourth": 4, "4th": 4, "chauthi": 4, "चौथी": 4,
    "fifth": 5, "5th": 5, "paanchvi": 5, "पांचवी": 5,
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _ordinal(text: str, default: int = 1) -> int:
    t = _norm(text)
    for k, v in ORDINAL_WORDS.items():
        if re.search(rf"(?<!\w){re.escape(k)}(?!\w)", t):
            return v
    m = re.search(r"\b(\d+)(?:st|nd|rd|th)?\b", t)
    if m:
        n = int(m.group(1))
        if n >= 1:
            return n
    return default


def _bool_from_text(t: str, default: bool = True) -> bool:
    negatives = ["off", "band", "disable", "hata", "remove", "बंद", "हटा"]
    return not any(x in t for x in negatives)


def _seconds_from_timestamp(t: str) -> float | None:
    # 2:30 or 01:02:03
    m = re.search(r"\b(?:(\d+):)?(\d{1,2}):(\d{2})\b", t)
    if m:
        h = int(m.group(1) or 0)
        return h * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    total = 0
    found = False
    hm = re.search(r"(\d+(?:\.\d+)?)\s*(?:hour|hours|hr|ghanta|घंटा)", t)
    mm = re.search(r"(\d+(?:\.\d+)?)\s*(?:minute|minutes|min|mins|मिनट)", t)
    sm = re.search(r"(\d+(?:\.\d+)?)\s*(?:second|seconds|sec|secs|सेकंड)", t)
    if hm:
        total += float(hm.group(1)) * 3600; found = True
    if mm:
        total += float(mm.group(1)) * 60; found = True
    if sm:
        total += float(sm.group(1)); found = True
    return total if found else None


class FastParser:
    """High-confidence parser for common commands. Returns None when Astra should decide."""

    def parse(self, text: str, context: dict | None = None) -> Intent | None:
        t = _norm(text)
        context = context or {}

        # Explicit non-YouTube apps should not be stolen by this parser.
        if any(x in t for x in ["whatsapp", "spotify", "telegram", "vscode", "vs code", "file explorer"]):
            return None

        if t.startswith("/health") or t.startswith("/provider") or t.startswith("/tools") or t.startswith("/stop"):
            return None

        if "youtube" in t and any(x in t for x in ["khol", "open", "launch", "चालू", "खोल"]):
            return Intent("youtube", "open", source="local")

        # Search keeps the query after stripping common framing.
        if any(x in t for x in ["search", "dhundo", "dhoondo", "khojo", "ढूंढ", "खोज"]):
            q = re.sub(r"\byoutube\b", "", t)
            q = re.sub(r"\b(pe|par|per)\b", " ", q)
            q = re.sub(r"\b(search(?: karo)?|dhundo|dhoondo|khojo|ढूंढो?|खोजो?)\b", " ", q)
            q = re.sub(r"\s+", " ", q).strip(" .,-")
            if q:
                return Intent("youtube", "search", {"query": q}, source="local")

        if "short" in t or "शॉर्ट" in t:
            if any(x in t for x in ["next", "agla", "agli", "अगला", "अगली"]):
                return Intent("youtube", "next_short", source="local")
            if any(x in t for x in ["previous", "prev", "pichla", "pichli", "पिछला", "पिछली"]):
                return Intent("youtube", "previous_short", source="local")
            if any(x in t for x in ["play", "chala", "laga", "चलाओ", "चला", "लगा"]):
                return Intent("youtube", "play_short", {"ordinal": _ordinal(t)}, source="local")

        if "video" in t and any(x in t for x in ["play", "chala", "laga", "चलाओ", "चला", "लगा"]):
            return Intent("youtube", "play_video", {"ordinal": _ordinal(t)}, source="local")

        if any(x in t for x in ["pause", "rok do", "roko", "रोक"]):
            return Intent("youtube", "pause", source="local")
        if any(x in t for x in ["resume", "continue", "phir chala", "dobara chala", "चलते रहो"]):
            return Intent("youtube", "resume", source="local")

        if "fullscreen" in t or "full screen" in t:
            return Intent("youtube", "set_fullscreen", {"enabled": _bool_from_text(t)}, source="local")
        if "theater" in t or "theatre" in t:
            return Intent("youtube", "set_theater_mode", {"enabled": _bool_from_text(t)}, source="local")
        if "miniplayer" in t or "mini player" in t:
            return Intent("youtube", "set_miniplayer", {"enabled": _bool_from_text(t)}, source="local")
        if any(x in t for x in ["caption", "captions", "subtitle", "subtitles"]):
            return Intent("youtube", "set_captions", {"enabled": _bool_from_text(t)}, source="local")

        if "speed" in t:
            m = re.search(r"(?:speed\s*)?(0\.25|0\.5|0\.75|1(?:\.0)?|1\.25|1\.5|1\.75|2(?:\.0)?)", t)
            if m:
                return Intent("youtube", "set_playback_speed", {"rate": float(m.group(1))}, source="local")
            if any(x in t for x in ["badhao", "increase", "faster", "tez", "बढ़ाओ", "तेज"]):
                return Intent("youtube", "speed_up", {"step": 0.25}, source="local")
            if any(x in t for x in ["kam", "decrease", "slower", "slow", "घटाओ"]):
                return Intent("youtube", "speed_down", {"step": 0.25}, source="local")

        ts = _seconds_from_timestamp(t)
        if ts is not None and any(x in t for x in ["jao", "go to", "seek", "pe ja", "पर जाओ"]):
            return Intent("youtube", "seek_timestamp", {"seconds": ts}, source="local")

        if any(x in t for x in ["forward", "aage", "आगे"]):
            m = re.search(r"(\d+)\s*(?:second|sec|seconds|सेकंड)?", t)
            return Intent("youtube", "seek_forward", {"seconds": int(m.group(1)) if m else 10}, source="local")
        if any(x in t for x in ["backward", "peeche", "piche", "पीछे"]):
            m = re.search(r"(\d+)\s*(?:second|sec|seconds|सेकंड)?", t)
            return Intent("youtube", "seek_backward", {"seconds": int(m.group(1)) if m else 10}, source="local")

        if "mute" in t or "aawaz band" in t or "sound off" in t or "आवाज़ बंद" in t:
            if "unmute" in t:
                return Intent("youtube", "unmute", source="local")
            return Intent("youtube", "mute", source="local")
        if "unmute" in t or "sound on" in t or "aawaz kholo" in t:
            return Intent("youtube", "unmute", source="local")

        if "volume" in t or "aawaz" in t or "sound" in t:
            m = re.search(r"\b(100|\d{1,2})\s*%?", t)
            if m:
                return Intent("youtube", "set_volume", {"level": int(m.group(1))}, source="local")
            if any(x in t for x in ["badhao", "increase", "up", "बढ़ाओ"]):
                return Intent("youtube", "volume_up", {"step": 10}, source="local")
            if any(x in t for x in ["kam", "decrease", "down", "घटाओ"]):
                return Intent("youtube", "volume_down", {"step": 10}, source="local")

        if "like" in t:
            return Intent("youtube", "set_like", {"enabled": _bool_from_text(t)}, source="local")
        if any(x in t for x in ["replay", "shuru se", "start again", "शुरू से"]):
            return Intent("youtube", "replay", source="local")

        # Safe context followups only when we know YouTube is current.
        if context.get("application") == "youtube":
            if t in {"next", "agli wali", "agla", "अगली वाली"} and context.get("page_type") == "SHORTS":
                return Intent("youtube", "next_short", source="context")
            if t in {"previous", "pichli wali", "pichla", "पिछली वाली"} and context.get("page_type") == "SHORTS":
                return Intent("youtube", "previous_short", source="context")

        return None
