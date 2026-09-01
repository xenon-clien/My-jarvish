"""Universal Hindi/Hinglish Semantic Language Engine for YouTube.

Maps unlimited natural phrasing (Roman Hindi, Devanagari, Hinglish, English)
into finite canonical YouTube intents with structured slot extraction,
state-aware desired values, unit parsing, negation, and self-correction.
"""
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from backend.core.logger import get_logger

logger = get_logger("YouTubeNLU")


@dataclass
class YouTubeSemanticResult:
    """Hardened canonical semantic interpretation result for YouTube."""
    canonical_action: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    content_type: str = "auto"
    ordinal: Optional[int] = None
    query: Optional[str] = None
    confidence: float = 0.0
    is_negated: bool = False
    desired_state: Optional[str] = None
    raw_text: str = ""
    normalized_text: str = ""


class YouTubeSemanticEngine:
    """Robust semantic slot and intent parser for YouTube natural language utterances."""

    # Hindi Devanagari to Roman transliteration for YouTube vocabulary
    DEVANAGARI_MAP = {
        "यूट्यूब": "youtube", "शॉर्ट": "short", "शॉर्ट्स": "shorts", "शॉट": "short", "शॉट्स": "shorts",
        "पहला": "pehla", "पहली": "pehli", "पहले": "pehla", "दूसरा": "dusra", "दूसरी": "dusri",
        "तीसरा": "teesra", "तीसरी": "teesri", "चौथा": "chautha", "चौथी": "chauthi",
        "पांचवा": "paanchva", "पांचवी": "paanchvi", "चलाओ": "chalao", "चला": "chala",
        "खोलो": "kholo", "खोल": "khol", "लगाओ": "lagao", "लगा": "laga", "रोको": "roko",
        "रोक": "rok", "पॉज": "pause", "रिज्यूम": "resume", "अगला": "agla", "अगली": "agli",
        "पिछला": "pichla", "पिछली": "pichli", "आगे": "aage", "पीछे": "peeche",
        "सर्च": "search", "ढूंढो": "dhundo", "बढ़ाओ": "badhao", "कम": "kam",
        "आवाज": "aawaz", "म्यूट": "mute", "फुलस्क्रीन": "fullscreen", "सब्सक्राइब": "subscribe",
        "लाइक": "like", "कमेंट्स": "comments", "वीडियो": "video", "चालू": "chalu", "दोबारा": "phir se",
        "स्पीड": "speed", "सबटाइटल": "subtitle", "कैप्शन": "caption"
    }

    # Hindi spoken numbers to integers
    HINDI_NUMBERS = {
        "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5,
        "chhe": 6, "che": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10,
        "pandrah": 15, "bees": 20, "tees": 30, "chaalis": 40, "pachaas": 50, "saath": 60,
        "dedh": 1.5, "dhai": 2.5, "aadha": 0.5
    }

    # Ordinal mappings (1-based semantic index)
    ORDINAL_MAP = {
        1: [r"\b(?:pehla|pehli|pehle|pahla|pahli|first|1st|one|number\s*(?:1|one)|top|sabse\s+pehla|sabse\s+pehli|sabse\s+pehle)\b"],
        2: [r"\b(?:dusra|dusri|doosra|doosri|second|2nd|two|number\s*(?:2|two))\b"],
        3: [r"\b(?:teesra|teesri|tisra|tisri|third|3rd|three|number\s*(?:3|three))\b"],
        4: [r"\b(?:chautha|chauthi|fourth|4th|four|number\s*(?:4|four))\b"],
        5: [r"\b(?:paanchva|paanchvi|panchwa|panchwi|fifth|5th|five|number\s*(?:5|five))\b"],
        6: [r"\b(?:chatha|chathi|sixth|6th|six|number\s*(?:6|six))\b"],
        7: [r"\b(?:saatva|saatvi|seventh|7th|seven|number\s*(?:7|seven))\b"],
        8: [r"\b(?:aathva|aathvi|eighth|8th|eight|number\s*(?:8|eight))\b"],
        9: [r"\b(?:nauva|nauvi|ninth|9th|nine|number\s*(?:9|nine))\b"],
        10: [r"\b(?:dasva|dasvi|tenth|10th|ten|number\s*(?:10|ten))\b"],
    }

    # Conversational filler words
    FILLERS = [
        r"\b(?:yaar|bhai|bhaiya|zara|plz|please|ek\s+kaam\s+karo|mere\s+liye|acha|achha|haan|arey|are|sun|suno)\b",
        r"\b(?:wali|wala|wale|waali|waale|waala)\b",
        r"\b(?:de|do|kar|karo|karna|karke|kariye|dena|chahiye)\b",
        r"\b(?:pe|par|mein|me|se|ko|ka|ki|ke|jo|wo|yeh|ye|woh|na)\b",
        r"\b(?:dikh\s+rahi\s+hai|dikh\s+raha\s+hai|hoti\s+hai|hota\s+hai|hai|hain)\b"
    ]

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """Transliterate Devanagari and normalize common phonetic variations."""
        norm = text.strip()
        for dev, rom in cls.DEVANAGARI_MAP.items():
            norm = norm.replace(dev, rom)
        
        slips = {
            r"\b(?:you\s*tube|utube|u\s*tube|yt)\b": "youtube",
            r"\b(?:shot|shots|shirt|shirts|shart|sort|sorts|chot|chote|choti\s+video|reels?)\b": "short",
            r"\b(?:fulskrin|fulscrin|full\s+skrin|badi\s+screen)\b": "fullscreen",
            r"\b(?:pouse|pows|pos|pass|paws|post)\b": "pause",
            r"\b(?:rijum|rijume|rigum|resum)\b": "resume",
            r"\b(?:sabscraib|subscrive)\b": "subscribe",
        }
        for pat, rep in slips.items():
            norm = re.sub(pat, rep, norm, flags=re.IGNORECASE)
        return norm.lower()

    @classmethod
    def extract_ordinal(cls, text: str) -> Optional[int]:
        """Extract 1-based semantic ordinal from natural Hindi / English utterance."""
        norm = cls.normalize_text(text)
        for ord_val, patterns in cls.ORDINAL_MAP.items():
            for pat in patterns:
                if re.search(pat, norm, flags=re.IGNORECASE):
                    return ord_val
        
        # Generic numeric regex: 'number 7', '7th', '7 wali'
        m = re.search(r"\b(?:number\s*)?(\d+)(?:st|nd|rd|th)?\b", norm)
        if m:
            val = int(m.group(1))
            if 1 <= val <= 50:
                return val
        return None

    @classmethod
    def extract_content_type(cls, text: str, current_page: str = "") -> str:
        """Identify content type: 'short', 'video', 'channel', or contextual 'auto'."""
        norm = cls.normalize_text(text)
        if re.search(r"\b(?:short|shorts|reel|reels|choti\s+video)\b", norm):
            return "short"
        if re.search(r"\b(?:channel|creator|profile)\b", norm):
            return "channel"
        if re.search(r"\b(?:badi\s+video|full\s+video|normal\s+video|gaana|song)\b", norm):
            return "video"
        if re.search(r"\bvideo\b", norm) and not re.search(r"\b(?:short|reel)\b", norm):
            return "video"
        
        if re.search(r"\b(?:pehli|first|dusri|second|teesri|third|pahli)\s+wali\b", norm) or re.search(r"\bfirst\s+wali\b", norm):
            return "short"

        if "short" in current_page.lower():
            return "short"
        return "auto"

    @classmethod
    def check_negation(cls, text: str) -> bool:
        """Check if action is negated ('mat karo', 'nahi karna', 'dont', 'mat rokna')."""
        norm = cls.normalize_text(text)
        neg_patterns = [
            r"\b(?:mat|nahi|na|not|dont|don't|never)\s+(?:karo|kar|karna|chalao|chala|rok|roko|rokna|pause|khol|play|badhao|kam|lagana|lagao)\b",
            r"\b(?:pause|play|next|mute|volume|video|short|subtitle|caption)\s+mat\b",
            r"\bmat\s+(?:karna|karo|chala|rokna|kholna|lagana|badhana)\b",
            r"\bmat\b"
        ]
        return any(re.search(p, norm, flags=re.IGNORECASE) for p in neg_patterns)

    @classmethod
    def resolve_self_correction(cls, text: str) -> str:
        """Resolve self-corrections (e.g. 'second nahi first short' -> 'first short')."""
        norm = cls.normalize_text(text)
        m = re.search(r"(?:.+?)\s+(?:nahi|not|nhi)\s*,?\s*(.+)", norm)
        if m:
            return m.group(1).strip()
        return norm

    @classmethod
    def extract_time_seconds(cls, text: str) -> int:
        """Parse spoken time durations like '10 second', 'ek minute', '2 minute', 'bees second' into seconds."""
        norm = cls.normalize_text(text)
        
        # Check minute patterns
        m_min = re.search(r"\b(?:(\d+)|([a-z]+))\s*(?:minute|min)\b", norm)
        if m_min:
            val_str = m_min.group(1) or m_min.group(2)
            mins = int(val_str) if val_str.isdigit() else cls.HINDI_NUMBERS.get(val_str, 1)
            return int(mins * 60)

        # Check second patterns
        m_sec = re.search(r"\b(?:(\d+)|([a-z]+))\s*(?:second|sec)\b", norm)
        if m_sec:
            val_str = m_sec.group(1) or m_sec.group(2)
            secs = int(val_str) if val_str.isdigit() else cls.HINDI_NUMBERS.get(val_str, 10)
            return int(secs)

        return 10

    @classmethod
    def extract_timestamp(cls, text: str) -> Optional[Tuple[str, int]]:
        """Parse timestamp utterances like '2 minute 30 second', '1:35', 'teen minute'."""
        norm = cls.normalize_text(text)
        
        # Pattern 1: '02:30' or '1:35'
        m_code = re.search(r"\b(\d+):(\d+)\b", norm)
        if m_code:
            mins, secs = int(m_code.group(1)), int(m_code.group(2))
            total_sec = mins * 60 + secs
            return (f"{mins:02d}:{secs:02d}", total_sec)

        # Pattern 2: '2 minute 30 second'
        m_ms = re.search(r"\b(\d+)\s*(?:minute|min)\s*(?:aur\s*)?(\d+)\s*(?:second|sec)?\b", norm)
        if m_ms:
            mins, secs = int(m_ms.group(1)), int(m_ms.group(2) or 0)
            total_sec = mins * 60 + secs
            return (f"{mins:02d}:{secs:02d}", total_sec)

        # Pattern 3: 'teen minute' / '3 min'
        m_single = re.search(r"\b(?:(\d+)|([a-z]+))\s*(?:minute|min)\s*(?:pe|par|jump|seek|jao)\b", norm)
        if m_single:
            val_str = m_single.group(1) or m_single.group(2)
            mins = int(val_str) if val_str.isdigit() else cls.HINDI_NUMBERS.get(val_str, 1)
            total_sec = int(mins * 60)
            return (f"{int(mins):02d}:00", total_sec)

        return None

    @classmethod
    def parse(cls, raw_text: str, current_page: str = "", active_app: str = "") -> YouTubeSemanticResult:
        """Parse natural utterance into canonical hardened YouTube intent and arguments."""
        norm_raw = cls.normalize_text(raw_text)
        
        # 1. Handle Self-Correction first
        corrected_text = cls.resolve_self_correction(norm_raw)
        
        # 2. Check Negation
        is_negated = cls.check_negation(corrected_text)
        if is_negated:
            return YouTubeSemanticResult(
                canonical_action="youtube.none_negated",
                confidence=0.99,
                is_negated=True,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        content_type = cls.extract_content_type(corrected_text, current_page=current_page)
        ordinal = cls.extract_ordinal(corrected_text)

        # ── 1. Next Short vs Ordinal 2 ──────────────────────────────────────
        if re.search(r"\b(?:next\s+short|agla\s+short|agli\s+short|niche\s+scroll|scroll\s+down|aage\s+wali\s+short|iske\s+baad\s+wali\s+short)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.next_short",
                content_type="short",
                confidence=0.98,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:next|agla|agli|aage\s+wala|iske\s+baad|doosri\s+wali\s+pe)\b", corrected_text):
            if content_type == "short" or "short" in current_page.lower():
                return YouTubeSemanticResult(
                    canonical_action="youtube.next_short",
                    content_type="short",
                    confidence=0.96,
                    raw_text=raw_text,
                    normalized_text=corrected_text
                )
            elif re.search(r"\b(?:next\s+video|agla\s+video|next\s+song|agla\s+gaana)\b", corrected_text):
                return YouTubeSemanticResult(
                    canonical_action="youtube.play_video",
                    arguments={"section": "next"},
                    content_type="video",
                    confidence=0.94,
                    raw_text=raw_text,
                    normalized_text=corrected_text
                )

        # ── 2. Previous Short / Relative Navigation ─────────────────────────
        if re.search(r"\b(?:previous\s+short|prev\s+short|pichla\s+short|pichli\s+short|pichhla\s+short|upar\s+scroll|scroll\s+up|peeche\s+wali\s+short)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.previous_short",
                content_type="short",
                confidence=0.98,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:previous|prev|pichla|pichli|piche|peeche\s+wala)\b", corrected_text):
            if content_type == "short" or "short" in current_page.lower():
                return YouTubeSemanticResult(
                    canonical_action="youtube.previous_short",
                    content_type="short",
                    confidence=0.96,
                    raw_text=raw_text,
                    normalized_text=corrected_text
                )

        # ── 3. Play Short (Optional ordinal defaults to 1) ───────────────────
        if content_type == "short" and ordinal is not None:
            return YouTubeSemanticResult(
                canonical_action="youtube.play_short",
                arguments={"ordinal": ordinal, "index": ordinal},
                content_type="short",
                ordinal=ordinal,
                confidence=0.98,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        elif content_type == "short" and re.search(r"\b(?:chala|play|laga|khol|open|launch|start|dikha)\w*\b", corrected_text):
            ord_target = ordinal or 1
            return YouTubeSemanticResult(
                canonical_action="youtube.play_short",
                arguments={"ordinal": ord_target, "index": ord_target},
                content_type="short",
                ordinal=ord_target,
                confidence=0.95,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 4. Fullscreen State-Aware (Desired State: ON vs OFF) ─────────────
        if re.search(r"\b(?:fullscreen\s+(?:hatao|exit|band|close|hata)|exit\s+fullscreen|chhota\s+karo)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.set_fullscreen",
                arguments={"enabled": False},
                desired_state="OFF",
                confidence=0.98,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:fullscreen|bada\s+karo|large\s+screen|screen\s+badi)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.set_fullscreen",
                arguments={"enabled": True},
                desired_state="ON",
                confidence=0.98,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 5. Captions State-Aware (Desired State: ON vs OFF) ───────────────
        if re.search(r"\b(?:captions?\s+(?:off|band|hatao)|subtitles?\s+(?:off|band|hatao)|caption\s+band)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.set_captions",
                arguments={"enabled": False},
                desired_state="OFF",
                confidence=0.98,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:captions?|subtitles?|subtitle\s+chalu|caption\s+on)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.set_captions",
                arguments={"enabled": True},
                desired_state="ON",
                confidence=0.98,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 6. Playback Speed Target Value (e.g. 1.5x, 2x, normal) ──────────
        m_speed = re.search(r"\b(?:(\d+(?:\.\d+)?)\s*x|dedh\s*(?:guna|x)|dhai\s*(?:guna|x)|normal\s+speed)\b", corrected_text)
        if m_speed:
            if "dedh" in corrected_text:
                target_rate = 1.5
            elif "dhai" in corrected_text:
                target_rate = 2.5
            elif "normal" in corrected_text:
                target_rate = 1.0
            else:
                target_rate = float(m_speed.group(1))
            return YouTubeSemanticResult(
                canonical_action="youtube.set_playback_speed",
                arguments={"rate": target_rate},
                confidence=0.97,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:speed\s+badhao|fast\s+karo|tez\s+chalao)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.speed_up",
                arguments={"step": 0.25},
                confidence=0.95,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:speed\s+kam|slow\s+karo|dheere\s+chalao)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.speed_down",
                arguments={"step": 0.25},
                confidence=0.95,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 7. Timestamp Seeking (e.g. '2 minute 30 second pe le jao') ───────
        ts_data = cls.extract_timestamp(corrected_text)
        if ts_data:
            ts_str, total_sec = ts_data
            return YouTubeSemanticResult(
                canonical_action="youtube.seek_timestamp",
                arguments={"timestamp": ts_str, "seconds": total_sec},
                confidence=0.97,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 8. Relative Seek Forward / Backward (e.g. '10 second aage') ──────
        if re.search(r"\b(?:aage|forward|skip)\b", corrected_text) and not re.search(r"\b(?:short|video)\b", corrected_text):
            secs = cls.extract_time_seconds(corrected_text)
            return YouTubeSemanticResult(
                canonical_action="youtube.seek_forward",
                arguments={"seconds": secs},
                confidence=0.96,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:peeche|rewind|backward)\b", corrected_text):
            secs = cls.extract_time_seconds(corrected_text)
            return YouTubeSemanticResult(
                canonical_action="youtube.seek_backward",
                arguments={"seconds": secs},
                confidence=0.96,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 9. Pause & Resume ───────────────────────────────────────────────
        if re.search(r"\b(?:pause|rok\s+do|roko|rok|thoda\s+rok|hold|stop\s+video|video\s+rok|video\s+roko|abhi\s+rok)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.pause",
                desired_state="PAUSED",
                confidence=0.97,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:resume|unpause|continue|wapas\s+chalao|phir\s+se\s+chalao|video\s+chalao|chalu\s+karo|chalu|chala\s+do)\b", corrected_text) and not re.search(r"\b(?:search|dhundo)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.resume",
                desired_state="PLAYING",
                confidence=0.96,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 10. Volume & Mute ───────────────────────────────────────────────
        if re.search(r"\b(?:mute|aawaz\s+band|sound\s+off)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.mute",
                desired_state="MUTED",
                confidence=0.96,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:unmute|aawaz\s+kholo|sound\s+on)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.unmute",
                desired_state="UNMUTED",
                confidence=0.96,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:volume\s+(?:up|badhao|badha)|aawaz\s+badhao|sound\s+up)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.volume_up",
                arguments={"step": 10},
                confidence=0.95,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:volume\s+(?:down|kam)|aawaz\s+kam|sound\s+down)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.volume_down",
                arguments={"step": 10},
                confidence=0.95,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 11. Social / Replay ─────────────────────────────────────────────
        if re.search(r"\b(?:like\s+karo|like\s+thok|like\s+this|video\s+like)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.like",
                confidence=0.96,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:replay|shuru\s+se\s+chalao|start\s+again)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.replay",
                confidence=0.96,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 12. Search & Play Video Entity ──────────────────────────────────
        cleaned_query = corrected_text
        for filler_pat in cls.FILLERS:
            cleaned_query = re.sub(filler_pat, " ", cleaned_query, flags=re.IGNORECASE)
        cleaned_query = re.sub(r"\b(?:youtube|search|dhundo|dhoondo|khojo|find|chalao|play|laga|kholo|open)\b", " ", cleaned_query, flags=re.IGNORECASE)
        cleaned_query = " ".join(cleaned_query.split()).strip()

        if re.search(r"\b(?:search|dhundo|dhoondo|khojo|find|dikhao)\b", corrected_text) and cleaned_query:
            return YouTubeSemanticResult(
                canonical_action="youtube.search",
                arguments={"query": cleaned_query},
                query=cleaned_query,
                confidence=0.94,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        if cleaned_query and len(cleaned_query) >= 2:
            return YouTubeSemanticResult(
                canonical_action="youtube.play_video",
                arguments={"query": cleaned_query, "ordinal": ordinal or 1},
                query=cleaned_query,
                ordinal=ordinal or 1,
                content_type="video",
                confidence=0.93,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 13. Plain YouTube Open ──────────────────────────────────────────
        if re.search(r"\b(?:youtube|kholo|open)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.open",
                arguments={},
                confidence=0.95,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        return YouTubeSemanticResult(
            canonical_action="youtube.unknown",
            confidence=0.30,
            raw_text=raw_text,
            normalized_text=corrected_text
        )


# Global singleton
youtube_nlu = YouTubeSemanticEngine()
