"""Universal Hindi/Hinglish Semantic Language Engine for YouTube (Contract v2.0).

Maps unlimited natural phrasing (Roman Hindi, Devanagari, Hinglish, English)
into canonical YouTube V2 intents with structured semantic slot extraction,
state-aware desired values, unit parsing, negation, and self-correction.
"""
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from backend.core.logger import get_logger

logger = get_logger("YouTubeNLU")


@dataclass
class YouTubeSemanticResult:
    """Canonical V2 semantic interpretation result for YouTube."""
    canonical_action: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    content_type: str = "auto"
    ordinal: Optional[int] = None
    query: Optional[str] = None
    direction: Optional[str] = None
    seconds: Optional[int] = None
    playback_rate: Optional[float] = None
    volume_step: Optional[int] = None
    desired_state: Optional[str] = None
    reference: Optional[str] = None
    confidence: float = 0.0
    is_negated: bool = False
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
        "स्पीड": "speed", "सबटाइटल": "subtitle", "कैप्शन": "caption", "थिएटर": "theater",
        "सिनेमा": "cinema", "मिनीप्लेयर": "miniplayer"
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
            r"\b(?:theatre|cinema\s+mode)\b": "theater mode",
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
            r"\b(?:mat|nahi|na|not|dont|don't|never)\s+(?:karo|kar|karna|chalao|chala|rok|roko|rokna|pause|khol|play|badhao|kam|lagana|lagao|like)\b",
            r"\b(?:pause|play|next|mute|volume|video|short|subtitle|caption|like)\s+mat\b",
            r"\bmat\s+(?:karna|karo|chala|rokna|kholna|lagana|badhana|karna)\b",
            r"\bmat\b"
        ]
        return any(re.search(p, norm, flags=re.IGNORECASE) for p in neg_patterns)

    @classmethod
    def resolve_self_correction(cls, text: str) -> str:
        """Resolve self-corrections (e.g. 'second nahi first short' -> 'first short')."""
        norm = cls.normalize_text(text)
        # Skip conversational questions asking 'why' or 'how'
        if re.search(r"\b(?:kyu|kyun|ku|why|kaise|kya|kese)\b", norm):
            return norm
        m = re.search(r"(?:.+?)\s+(?:nahi|not|nhi)\s*,?\s*(.+)", norm)
        if m:
            return m.group(1).strip()
        return norm

    @classmethod
    def extract_time_seconds(cls, text: str) -> int:
        """Parse spoken time durations like '10 second', 'ek minute', '2 minute', 'bees second' into seconds."""
        norm = cls.normalize_text(text)
        m_min = re.search(r"\b(?:(\d+)|([a-z]+))\s*(?:minute|min)\b", norm)
        if m_min:
            val_str = m_min.group(1) or m_min.group(2)
            mins = int(val_str) if val_str.isdigit() else cls.HINDI_NUMBERS.get(val_str, 1)
            return int(mins * 60)

        m_sec = re.search(r"\b(?:(\d+)|([a-z]+))\s*(?:second|sec)\b", norm)
        if m_sec:
            val_str = m_sec.group(1) or m_sec.group(2)
            secs = int(val_str) if val_str.isdigit() else cls.HINDI_NUMBERS.get(val_str, 10)
            return int(secs)

        return 10

    @classmethod
    def extract_timestamp(cls, text: str) -> Optional[Tuple[str, int]]:
        """Parse timestamp utterances like '2 minute 30 second', '1:35', 'teen minute' into (raw_str, total_sec)."""
        norm = cls.normalize_text(text)
        
        # 1. Digital notation: HH:MM:SS or MM:SS
        m_code = re.search(r"\b(?:(\d+):)?(\d{1,2}):(\d{2})\b", norm)
        if m_code:
            h = int(m_code.group(1) or 0)
            mins = int(m_code.group(2))
            secs = int(m_code.group(3))
            total_sec = h * 3600 + mins * 60 + secs
            label = f"{h:02d}:{mins:02d}:{secs:02d}" if h else f"{mins:02d}:{secs:02d}"
            return (label, total_sec)

        # 2. Hindi/English compound duration: e.g. "2 minute 30 second", "1 hr 20 mins"
        m_ms = re.search(r"\b(\d+)\s*(?:minute|min)\s*(?:aur\s*)?(\d+)\s*(?:second|sec)?\b", norm)
        if m_ms:
            mins, secs = int(m_ms.group(1)), int(m_ms.group(2) or 0)
            total_sec = mins * 60 + secs
            return (f"{mins:02d}:{secs:02d}", total_sec)

        total = 0
        found = False
        hm = re.search(r"(\d+(?:\.\d+)?)\s*(?:hour|hours|hr|ghanta|घंटा)", norm)
        mm = re.search(r"(\d+(?:\.\d+)?)\s*(?:minute|minutes|min|mins|मिनट)", norm)
        sm = re.search(r"(\d+(?:\.\d+)?)\s*(?:second|seconds|sec|secs|सेकंड)", norm)
        if hm:
            total += int(float(hm.group(1)) * 3600)
            found = True
        if mm:
            total += int(float(mm.group(1)) * 60)
            found = True
        if sm:
            total += int(float(sm.group(1)))
            found = True
        if found and total > 0:
            return (f"{total}s", total)

        m_single = re.search(r"\b(?:(\d+)|([a-z]+))\s*(?:minute|min)\s*(?:pe|par|jump|seek|jao)\b", norm)
        if m_single:
            val_str = m_single.group(1) or m_single.group(2)
            mins = int(val_str) if val_str.isdigit() else cls.HINDI_NUMBERS.get(val_str, 1)
            total_sec = int(mins * 60)
            return (f"{int(mins):02d}:00", total_sec)

        return None

    @classmethod
    def parse(cls, raw_text: str, current_page: str = "", active_app: str = "") -> YouTubeSemanticResult:
        """Parse natural utterance into canonical hardened YouTube V2 intent and arguments."""
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
        if re.search(r"\b(?:next\s+short|agla\s+short|agli\s+short|short\s+niche\s+scroll|aage\s+wali\s+short|iske\s+baad\s+wali\s+short)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.next_short",
                content_type="short",
                direction="down",
                desired_state="NAVIGATED_NEXT_SHORT",
                confidence=0.98,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:next|agla|agli|aage\s+wala|iske\s+baad|doosri\s+wali\s+pe)\b", corrected_text):
            if content_type == "short" or "short" in current_page.lower():
                return YouTubeSemanticResult(
                    canonical_action="youtube.next_short",
                    content_type="short",
                    direction="down",
                    desired_state="NAVIGATED_NEXT_SHORT",
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
        if re.search(r"\b(?:previous\s+short|prev\s+short|pichla\s+short|pichli\s+short|pichhla\s+short|short\s+upar\s+scroll|peeche\s+wali\s+short)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.previous_short",
                content_type="short",
                direction="up",
                desired_state="NAVIGATED_PREV_SHORT",
                confidence=0.98,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:previous|prev|pichla|pichli|piche|peeche\s+wala)\b", corrected_text):
            if content_type == "short" or "short" in current_page.lower():
                return YouTubeSemanticResult(
                    canonical_action="youtube.previous_short",
                    content_type="short",
                    direction="up",
                    desired_state="NAVIGATED_PREV_SHORT",
                    confidence=0.96,
                    raw_text=raw_text,
                    normalized_text=corrected_text
                )

        # ── 2b. Universal YouTube Page / Feed Scrolling ──────────────────────
        if re.search(r"\b(?:scroll\s+(?:up|upar)|upar\s+scroll|page\s+(?:up|upar)|thoda\s+upar|upar\s+karo|^page\s*up$)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.scroll",
                arguments={"direction": "up", "amount": 500},
                direction="up",
                desired_state="PAGE_SCROLLED",
                confidence=0.98,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:scroll\s+(?:down|neeche|niche)|neeche\s+scroll|niche\s+scroll|page\s+(?:down|neeche|niche)|thoda\s+(?:neeche|niche)|neeche\s+karo|niche\s+karo|scroll\s+karo|scroll\s+kar\s+do|scroll\s+kardo|thoda\s+scroll|aur\s+scroll|^scroll$)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.scroll",
                arguments={"direction": "down", "amount": 500},
                direction="down",
                desired_state="PAGE_SCROLLED",
                confidence=0.98,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 3. Play Short (Optional ordinal defaults to 1) ───────────────────
        if content_type == "short" and ordinal is not None:
            return YouTubeSemanticResult(
                canonical_action="youtube.play_short",
                arguments={"ordinal": ordinal},
                content_type="short",
                ordinal=ordinal,
                desired_state="SHORT_PLAYING",
                confidence=0.98,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        elif content_type == "short" and re.search(r"\b(?:chala|play|laga|khol|open|launch|start|dikha)\w*\b", corrected_text):
            ord_target = ordinal or 1
            return YouTubeSemanticResult(
                canonical_action="youtube.play_short",
                arguments={"ordinal": ord_target},
                content_type="short",
                ordinal=ord_target,
                desired_state="SHORT_PLAYING",
                confidence=0.95,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 3b. Play Video by Ordinal (e.g. "play first video", "pehla video chalao", "2nd video play karo") ───
        if ordinal is not None and re.search(r"\b(?:video|gaana|song|card|result|item|waala|wali|wala)\b", corrected_text):
            rem = corrected_text
            for ord_pat in [
                r"\b(?:pehla|pehli|pehle|pahla|pahli|first|1st|one|number\s*(?:1|one)|top|sabse\s+pehla)\b",
                r"\b(?:dusra|dusri|doosra|doosri|second|2nd|two|number\s*(?:2|two))\b",
                r"\b(?:teesra|teesri|tisra|tisri|third|3rd|three|number\s*(?:3|three))\b",
                r"\b(?:chautha|chauthi|fourth|4th|four|number\s*(?:4|four))\b",
                r"\b(?:paanchva|paanchvi|fifth|5th|five|number\s*(?:5|five))\b",
                r"\b(?:video|song|gaana|chalao|play|laga|kholo|open|launch|start|dikha)\b"
            ]:
                rem = re.sub(ord_pat, " ", rem, flags=re.IGNORECASE)
            for f in cls.FILLERS:
                rem = re.sub(f, " ", rem, flags=re.IGNORECASE)
            rem = " ".join(rem.split()).strip()

            if not rem or len(rem) < 2:
                return YouTubeSemanticResult(
                    canonical_action="youtube.play_video",
                    arguments={"ordinal": ordinal},
                    content_type="video",
                    ordinal=ordinal,
                    query="",
                    desired_state="VIDEO_PLAYING",
                    confidence=0.98,
                    raw_text=raw_text,
                    normalized_text=corrected_text
                )

        # ── 4. Fullscreen State-Aware (Desired State: ON vs OFF) ─────────────
        if re.search(r"\b(?:fullscreen\s+(?:hatao|exit|band|close|hata)|exit\s+fullscreen|chhota\s+karo)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.set_fullscreen",
                arguments={"enabled": False},
                desired_state="FULLSCREEN_OFF",
                confidence=0.98,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:fullscreen|bada\s+karo|large\s+screen|screen\s+badi)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.set_fullscreen",
                arguments={"enabled": True},
                desired_state="FULLSCREEN_ON",
                confidence=0.98,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 5. Theater Mode (Restored V1 Capability) ────────────────────────
        if re.search(r"\b(?:theater\s+(?:mode\s+)?(?:band|hatao|close)|cinema\s+mode\s+band)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.set_theater_mode",
                arguments={"enabled": False},
                desired_state="THEATER_OFF",
                confidence=0.98,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:theater\s+mode|cinema\s+mode|theatre\s+mode)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.set_theater_mode",
                arguments={"enabled": True},
                desired_state="THEATER_ON",
                confidence=0.98,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 6. Miniplayer Mode ──────────────────────────────────────────────
        if re.search(r"\b(?:miniplayer\s+(?:band|hatao|close))\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.set_miniplayer",
                arguments={"enabled": False},
                desired_state="MINIPLAYER_OFF",
                confidence=0.98,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:miniplayer|chhoti\s+screen|mini\s+player)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.set_miniplayer",
                arguments={"enabled": True},
                desired_state="MINIPLAYER_ON",
                confidence=0.98,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 7. Captions State-Aware (Desired State: ON vs OFF) ───────────────
        if re.search(r"\b(?:captions?\s+(?:off|band|hatao)|subtitles?\s+(?:off|band|hatao)|caption\s+band)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.set_captions",
                arguments={"enabled": False},
                desired_state="CAPTIONS_OFF",
                confidence=0.98,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:captions?|subtitles?|subtitle\s+chalu|caption\s+on)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.set_captions",
                arguments={"enabled": True},
                desired_state="CAPTIONS_ON",
                confidence=0.98,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 8. Playback Speed Target Value (e.g. 1.5x, 2x, normal) ──────────
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
                playback_rate=target_rate,
                desired_state="SPEED_SET",
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

        # ── 9. Relative Seek Forward / Backward ────────────────────────────
        is_media_level = bool(re.search(r"\b(?:volume|awaj|awaaz|sound|speed|raftar)\b", corrected_text))
        is_seek_fwd = not is_media_level and bool(
            re.search(r"\b(?:bhagao|fast\s*forward|aage\s*karo|forward\s*karo|skip\s*karo|aage\s*badhao)\b", corrected_text) or
            (re.search(r"\b(?:aage|forward|skip)\b", corrected_text) and not re.search(r"\b(?:next|agla|pehla|doosra|teesra)\s+(?:short|video)\b", corrected_text))
        )
        if is_seek_fwd:
            secs = cls.extract_time_seconds(corrected_text)
            return YouTubeSemanticResult(
                canonical_action="youtube.seek_forward",
                arguments={"seconds": secs},
                seconds=secs,
                direction="forward",
                desired_state="SEEKED_FORWARD",
                confidence=0.96,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        is_seek_bwd = not is_media_level and bool(
            re.search(r"\b(?:peeche|rewind|backward|piche|peechhe)\b", corrected_text) and
            not re.search(r"\b(?:previous|pichla|prev)\s+(?:short|video)\b", corrected_text)
        )
        if is_seek_bwd:
            secs = cls.extract_time_seconds(corrected_text)
            return YouTubeSemanticResult(
                canonical_action="youtube.seek_backward",
                arguments={"seconds": secs},
                seconds=secs,
                direction="backward",
                desired_state="SEEKED_BACKWARD",
                confidence=0.96,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 10. Timestamp Seeking (Normalized seconds) ────────────────────────
        ts_data = cls.extract_timestamp(corrected_text)
        if ts_data:
            ts_str, total_sec = ts_data
            return YouTubeSemanticResult(
                canonical_action="youtube.seek_timestamp",
                arguments={"seconds": total_sec, "raw_timestamp": ts_str},
                seconds=total_sec,
                desired_state="SEEKED_TO_TIMESTAMP",
                confidence=0.97,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 11. Pause & Resume ──────────────────────────────────────────────
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

        # ── 12. Volume Direct Set vs Step ───────────────────────────────────
        m_vset = re.search(r"\b(?:volume|sound|aawaz)\s*(\d+)(?:\s*percent|%)?\b|\bset\s+volume\s+(\d+)\b", corrected_text)
        if m_vset:
            v_val = int(m_vset.group(1) or m_vset.group(2))
            return YouTubeSemanticResult(
                canonical_action="youtube.set_volume",
                arguments={"level": v_val},
                desired_state="VOLUME_LEVEL_SET",
                confidence=0.97,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        if re.search(r"\b(?:volume\s+(?:up|badhao|badha)|aawaz\s+badhao|sound\s+up)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.volume_up",
                arguments={"step": 10},
                volume_step=10,
                confidence=0.95,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:volume\s+(?:down|kam)|aawaz\s+kam|sound\s+down)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.volume_down",
                arguments={"step": 10},
                volume_step=-10,
                confidence=0.95,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
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

        # ── 13. Idempotent Like / Unlike ────────────────────────────────────
        if re.search(r"\b(?:like\s+(?:hatao|remove|unlike))\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.set_like",
                arguments={"enabled": False},
                desired_state="UNLIKED",
                confidence=0.96,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:like\s+karo|like\s+thok|like\s+this|video\s+like|like)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.set_like",
                arguments={"enabled": True},
                desired_state="LIKED",
                confidence=0.96,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 14. Replay ──────────────────────────────────────────────────────
        if re.search(r"\b(?:replay|shuru\s+se\s+chalao|start\s+again)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.replay",
                desired_state="REPLAYED",
                confidence=0.96,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 15. Plain YouTube Open ──────────────────────────────────────────
        if re.search(r"\b(?:youtube|utube)\b", corrected_text) and re.search(r"\b(?:kholo|khol|open|launch|start|chalu)\b", corrected_text) and not re.search(r"\b(?:search|dhundo|dhoondo)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.open",
                arguments={},
                desired_state="NAVIGATED_HOME",
                confidence=0.98,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 15b. Perception Diagnostics ("screen pe kya dikh raha hai", "abhi youtube pe kon do videos dikh rahi hai", etc.) ──
        if re.search(r"^\s*(?:shorts?)\s*$", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.observe",
                arguments={"target": "shorts", "max_items": 5},
                confidence=0.98,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        has_imperative_action = bool(re.search(r"\b(?:play\s+karo|chalao|lagao|bajao|search\s+karo|dhundo|dhoondo|khojo|pause\s+karo|roko|band\s+karo|kholo)\b", corrected_text))
        has_inquiry = bool(re.search(r"\b(?:kya|kaun|kon|kaunsa|konsa|kaunsi|konsi|kaunse|konse|koun|kounsi|batao|dikhao|dikh|list|name|naam|which|what|show|tell)\b", corrected_text))
        has_visible_verb = bool(re.search(r"\b(?:dikh\s+rah[aie]|dikh\s+rahe|dikha\s+rah[aie]|dikhta|dikhti|chal\s+rah[aie]|chal\s+rahe|open\s+hai|chal\s+raha|play\s+ho\s+rah[aie]|hain|hai|visible|showing)\b", corrected_text))
        has_media_target = bool(re.search(r"\b(?:video|videos|short|shorts|gaana|screen|page|feed|result|results|youtube|utube)\b", corrected_text))

        is_diagnostic = not has_imperative_action and (
            (has_inquiry and (has_visible_verb or has_media_target)) or
            bool(re.search(r"\b(?:screen\s+pe\s+kya|kya\s+chal\s+raha|kya\s+play\s+ho\s+raha|youtube\s+pe\s+kya)\b", corrected_text))
        )

        if is_diagnostic:
            diag_count = 5
            count_match = re.search(r"\b(?:(\d+)|ek|do|teen|char|chaar|paanch|chhe|saat|aath|nau|das)\s+(?:video|videos|short|shorts|card|cards)\b", corrected_text)
            if not count_match:
                count_match = re.search(r"\b(?:video|videos|short|shorts|card|cards)\s+(?:(\d+)|ek|do|teen|char|chaar|paanch|chhe|saat|aath|nau|das)\b", corrected_text)
            if count_match:
                tokens = count_match.group(0).split()
                for tok in tokens:
                    if tok.isdigit():
                        diag_count = int(tok)
                        break
                    elif tok in cls.HINDI_NUMBERS:
                        diag_count = int(cls.HINDI_NUMBERS[tok])
                        break

            diag_args = {"max_items": diag_count}
            if re.search(r"\b(?:short|shorts)\b", corrected_text):
                diag_args["target"] = "shorts"
            elif re.search(r"\b(?:video|videos)\b", corrected_text):
                diag_args["target"] = "videos"

            return YouTubeSemanticResult(
                canonical_action="youtube.observe",
                arguments=diag_args,
                confidence=0.98,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 16. Pure Ordinal Video Playback (e.g. "play first", "pehla chalao", "first play karo") ──
        # If ordinal is specified without a real search query (only play verbs / video nouns)
        if ordinal is not None and not re.search(r"\b(?:search|dhundo|dhoondo|khojo)\b", corrected_text):
            # Check if utterance only contains ordinal words, play verbs, and filler/media nouns
            text_without_ordinal = corrected_text
            for filler_pat in cls.FILLERS:
                text_without_ordinal = re.sub(filler_pat, " ", text_without_ordinal, flags=re.IGNORECASE)
            for ord_val, patterns in cls.ORDINAL_MAP.items():
                for pat in patterns:
                    text_without_ordinal = re.sub(pat, " ", text_without_ordinal, flags=re.IGNORECASE)
            text_without_ordinal = re.sub(r"\b(?:play|chalao|chala|laga|lagao|khol|kholo|open|start|dikhao|bajao|video|videos|gaana|song|item|result|number|\d+)\b", " ", text_without_ordinal, flags=re.IGNORECASE)
            remaining_words = text_without_ordinal.strip().split()

            if not remaining_words:
                # Pure ordinal selection from visible screen cards!
                return YouTubeSemanticResult(
                    canonical_action="youtube.play_video",
                    arguments={"ordinal": ordinal, "query": ""},
                    query="",
                    ordinal=ordinal,
                    content_type="video",
                    desired_state="VIDEO_PLAYING",
                    confidence=0.97,
                    raw_text=raw_text,
                    normalized_text=corrected_text
                )

        # ── 17. Search on YouTube (Strip UI vocabulary: search bar, search box, etc.) ──
        cleaned_query = corrected_text
        # Strip UI vocabulary first so "search bar" / "search box" doesn't become query words
        cleaned_query = re.sub(r"\b(?:search\s+bar|search\s+box|searchbar|searchbox|bar|box)\b", " ", cleaned_query, flags=re.IGNORECASE)
        for filler_pat in cls.FILLERS:
            cleaned_query = re.sub(filler_pat, " ", cleaned_query, flags=re.IGNORECASE)
        cleaned_query = re.sub(r"\b(?:youtube|search|dhundo|dhoondo|khojo|find|dikhao|chalao|play|laga|kholo|open|bajao|type|dalo|daalo|likho|likh|enter)\b", " ", cleaned_query, flags=re.IGNORECASE)
        # Also remove ordinal words from search query if any
        if ordinal is not None:
            for ord_val, patterns in cls.ORDINAL_MAP.items():
                for pat in patterns:
                    cleaned_query = re.sub(pat, " ", cleaned_query, flags=re.IGNORECASE)
        cleaned_query = " ".join(cleaned_query.split()).strip()

        if re.search(r"\b(?:search|dhundo|dhoondo|khojo|find|dikhao|type|dalo|daalo|likho|likh|enter)\b", corrected_text) and cleaned_query:
            return YouTubeSemanticResult(
                canonical_action="youtube.search",
                arguments={"query": cleaned_query},
                query=cleaned_query,
                desired_state="SEARCH_RESULTS_DISPLAYED",
                confidence=0.94,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 18. Conversational / Diagnostic Inquiries (Do NOT play videos) ───
        if re.search(r"\b(?:kyu|kyun|ku|why|kaise|how|kya|problem|issue|dikkat|kharab|freeze|atak|chalta|chal\s+raha|chal\s+rahi|sun|suno|kuch|nahi|nhi)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.unknown",
                confidence=0.0,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 19. Play Video by Search Entity ─────────────────────────────────
        # Must have an explicit play verb (chalao, play, laga, bajao, start)
        # OR explicit media noun (video, gaana, song, track) with query
        has_play_verb = bool(re.search(r"\b(?:chalao|chala|laga|lagao|play|bajao|start|sunao)\b", corrected_text))
        has_media_noun = bool(re.search(r"\b(?:video|gaana|gaane|song|songs|track|music|vlog|trailer|movie|film)\b", corrected_text))

        if (has_play_verb or has_media_noun) and cleaned_query and len(cleaned_query) >= 2:
            return YouTubeSemanticResult(
                canonical_action="youtube.play_video",
                arguments={"query": cleaned_query, "ordinal": ordinal or 1},
                query=cleaned_query,
                ordinal=ordinal or 1,
                content_type="video",
                desired_state="VIDEO_PLAYING",
                confidence=0.93,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # ── 20. Plain YouTube Mention ───────────────────────────────────────
        if re.search(r"^\s*(?:youtube|utube|yt)\s*$", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.open",
                arguments={},
                desired_state="NAVIGATED_HOME",
                confidence=0.95,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        return YouTubeSemanticResult(
            canonical_action="youtube.unknown",
            confidence=0.0,
            raw_text=raw_text,
            normalized_text=corrected_text
        )


# Global singleton
youtube_nlu = YouTubeSemanticEngine()
