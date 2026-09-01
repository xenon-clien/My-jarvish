"""Universal Hindi/Hinglish Semantic Language Engine for YouTube.

Maps unlimited natural phrasing (Roman Hindi, Devanagari, Hinglish, English)
into finite canonical YouTube intents with structured argument extraction,
contextual disambiguation, negation handling, and self-correction resolution.
"""
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from backend.core.logger import get_logger

logger = get_logger("YouTubeNLU")


@dataclass
class YouTubeSemanticResult:
    """Canonical semantic interpretation result for YouTube."""
    canonical_action: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    content_type: str = "auto"
    ordinal: Optional[int] = None
    query: Optional[str] = None
    confidence: float = 0.0
    is_negated: bool = False
    raw_text: str = ""
    normalized_text: str = ""


class YouTubeSemanticEngine:
    """Robust semantic component parser for YouTube natural language utterances."""

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
        "लाइक": "like", "कमेंट्स": "comments", "वीडियो": "video", "चालू": "chalu", "दोबारा": "phir se"
    }

    # Filler words to ignore in intent parsing without stripping entities
    FILLERS = [
        r"\b(?:yaar|bhai|bhaiya|zara|plz|please|ek\s+kaam\s+karo|mere\s+liye|acha|achha|haan|arey|are|sun|suno)\b",
        r"\b(?:wali|wala|wale|waali|waale|waala)\b",
        r"\b(?:de|do|kar|karo|karna|karke|kariye|dena|chahiye)\b",
        r"\b(?:pe|par|mein|me|se|ko|ka|ki|ke|jo|wo|yeh|ye|woh)\b",
        r"\b(?:dikh\s+rahi\s+hai|dikh\s+raha\s+hai|hoti\s+hai|hota\s+hai|hai|hain)\b"
    ]

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

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """Transliterate Devanagari and normalize common phonetic variations."""
        norm = text.strip()
        for dev, rom in cls.DEVANAGARI_MAP.items():
            norm = norm.replace(dev, rom)
        
        # Phonetic corrections for common STT slips
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
        
        # Generic numeric regex: "number 7", "7th", "7 wali"
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
        
        # If ordinal mentioned without 'video' (e.g. 'pehli wali', 'first wali open kar'), default to short
        if re.search(r"\b(?:pehli|first|dusri|second|teesri|third|pahli)\s+wali\b", norm) or re.search(r"\bfirst\s+wali\b", norm):
            return "short"

        # Fallback to current page context
        if "short" in current_page.lower():
            return "short"
        return "auto"

    @classmethod
    def check_negation(cls, text: str) -> bool:
        """Check if action is negated ('mat karo', 'nahi karna', 'dont', 'mat rokna')."""
        norm = cls.normalize_text(text)
        neg_patterns = [
            r"\b(?:mat|nahi|na|not|dont|don't|never)\s+(?:karo|kar|karna|chalao|chala|rok|roko|rokna|pause|khol|play|badhao|kam)\b",
            r"\b(?:pause|play|next|mute|volume|video|short)\s+mat\b",
            r"\bmat\s+(?:karna|karo|chala|rokna|kholna|lagana)\b",
            r"\bmat\b"
        ]
        return any(re.search(p, norm, flags=re.IGNORECASE) for p in neg_patterns)

    @classmethod
    def resolve_self_correction(cls, text: str) -> str:
        """Resolve self-corrections (e.g. 'second nahi first short' -> 'first short')."""
        norm = cls.normalize_text(text)
        # Match pattern: '<X> nahi <Y>' -> return '<Y>'
        m = re.search(r"(?:.+?)\s+(?:nahi|not|nhi)\s*,?\s*(.+)", norm)
        if m:
            return m.group(1).strip()
        return norm

    @classmethod
    def parse(cls, raw_text: str, current_page: str = "", active_app: str = "") -> YouTubeSemanticResult:
        """Parse natural utterance into canonical YouTube intent and arguments."""
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

        # ── Fast Semantic Action Classification ─────────────────────────────
        
        # A. Next Short / Next Video
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

        # B. Previous Short / Prev Video
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

        # C. Play Short (e.g. 'pehli short chalao', 'first short laga do', '3rd short', 'pehli wali laga')
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
        elif content_type == "short" and re.search(r"\b(?:chala|play|laga|khol|open|launch)\b", corrected_text):
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

        # D. Pause
        if re.search(r"\b(?:pause|rok\s+do|roko|rok|thoda\s+rok|hold|stop\s+video|video\s+rok|video\s+roko|abhi\s+rok)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.pause",
                confidence=0.97,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # E. Resume / Play
        if re.search(r"\b(?:resume|unpause|continue|wapas\s+chalao|phir\s+se\s+chalao|video\s+chalao|chalu\s+karo|chalu|chala\s+do)\b", corrected_text) and not re.search(r"\b(?:search|dhundo)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.resume",
                confidence=0.96,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # F. Fullscreen
        if re.search(r"\b(?:fullscreen|bada\s+karo|large\s+screen|screen\s+badi)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.fullscreen",
                confidence=0.97,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # G. Seek Forward / Backward
        m_fwd = re.search(r"\b(?:(\d+)\s*(?:sec|seconds?)\s*aage|aage\s+badhao|fast\s+forward|skip\s*(\d+)?|thoda\s+aage|aage\s+karo)\b", corrected_text)
        if m_fwd:
            secs = int(m_fwd.group(1) or m_fwd.group(2) or 10)
            return YouTubeSemanticResult(
                canonical_action="youtube.seek_forward",
                arguments={"seconds": secs},
                confidence=0.95,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        m_bwd = re.search(r"\b(?:(\d+)\s*(?:sec|seconds?)\s*peeche|peeche\s+karo|rewind|thoda\s+peeche)\b", corrected_text)
        if m_bwd:
            secs = int(m_bwd.group(1) or 10)
            return YouTubeSemanticResult(
                canonical_action="youtube.seek_backward",
                arguments={"seconds": secs},
                confidence=0.95,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # H. Mute / Unmute
        if re.search(r"\b(?:mute|aawaz\s+band|sound\s+off)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.mute",
                confidence=0.96,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:unmute|aawaz\s+kholo|sound\s+on)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.unmute",
                confidence=0.96,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # I. Volume Up / Down
        if re.search(r"\b(?:volume\s+(?:up|badhao|badha)|aawaz\s+badhao|sound\s+up)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.volume_up",
                confidence=0.95,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:volume\s+(?:down|kam)|aawaz\s+kam|sound\s+down)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.volume_down",
                confidence=0.95,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # J. Like / Captions / Speed
        if re.search(r"\b(?:like\s+karo|like\s+thok|like\s+this|video\s+like)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.like",
                confidence=0.96,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:captions?|subtitles?)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.captions",
                confidence=0.95,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:speed\s+badhao|fast\s+karo|tez\s+chalao)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.speed_up",
                confidence=0.95,
                raw_text=raw_text,
                normalized_text=corrected_text
            )
        if re.search(r"\b(?:speed\s+kam|slow\s+karo|dheere\s+chalao)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.speed_down",
                confidence=0.95,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # K. Search or Play Video Query
        cleaned_query = corrected_text
        for filler_pat in cls.FILLERS:
            cleaned_query = re.sub(filler_pat, " ", cleaned_query, flags=re.IGNORECASE)
        cleaned_query = re.sub(r"\b(?:youtube|search|dhundo|dhoondo|khojo|find|chalao|play|laga|kholo|open)\b", " ", cleaned_query, flags=re.IGNORECASE)
        cleaned_query = " ".join(cleaned_query.split()).strip()

        # Check explicit search intent
        if re.search(r"\b(?:search|dhundo|dhoondo|khojo|find|dikhao)\b", corrected_text) and cleaned_query:
            return YouTubeSemanticResult(
                canonical_action="youtube.search",
                arguments={"query": cleaned_query},
                query=cleaned_query,
                confidence=0.94,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # Check search & play video query (e.g. 'YouTube pe CarryMinati chalao', 'Aarush Laila song play karo')
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

        # L. Plain YouTube Open (e.g. 'YouTube kholo', 'open youtube')
        if re.search(r"\b(?:youtube|kholo|open)\b", corrected_text):
            return YouTubeSemanticResult(
                canonical_action="youtube.open",
                arguments={"query": ""},
                confidence=0.95,
                raw_text=raw_text,
                normalized_text=corrected_text
            )

        # Low confidence fallback
        return YouTubeSemanticResult(
            canonical_action="youtube.unknown",
            confidence=0.30,
            raw_text=raw_text,
            normalized_text=corrected_text
        )


# Global singleton
youtube_nlu = YouTubeSemanticEngine()
