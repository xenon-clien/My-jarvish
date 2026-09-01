"""JARVIS 3.0 - Universal Language Normalizer.

Normalizes Hindi, Hinglish, English, and Devanagari text into canonical
semantic structures and extracts parameters with high resilience to speech slips.
"""
import re
from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, Field

# Devanagari phonetic transliteration map
DEVANAGARI_MAP = {
    "यूट्यूब": "youtube",
    "युटुब": "youtube",
    "युट्यूब": "youtube",
    "क्रोम": "chrome",
    "व्हाट्सएप": "whatsapp",
    "व्हाट्सऐप": "whatsapp",
    "वाट्सएप": "whatsapp",
    "शॉर्ट": "short",
    "शॉर्ट्स": "shorts",
    "शॉट": "short",
    "शॉट्स": "shorts",
    "पहला": "first",
    "पहली": "first",
    "दूसरा": "second",
    "दूसरी": "second",
    "तीसरा": "third",
    "तीसरी": "third",
    "चलाओ": "play",
    "चला": "play",
    "खोलो": "open",
    "खोल": "open",
    "बंद": "close",
    "रोको": "pause",
    "पॉज": "pause",
    "चालू": "resume",
    "रिज्यूम": "resume",
    "अगला": "next",
    "पिछला": "prev",
    "आवाज": "volume",
    "बढ़ाओ": "up",
    "कम": "down",
    "मैसेज": "message",
    "कॉल": "call",
    "फोन": "phone",
    "सर्च": "search",
    "लाइक": "like",
    "सब्सक्राइब": "subscribe",
    "कमेंट्स": "comments",
    "रुक": "stop",
    "जाओ": "stop",
    "बस": "stop",
    "कैंसिल": "cancel",
}

# Phonetic speech-to-text corrections
PHONETIC_SLIPS = {
    r"\b(?:pouse|pows|pos|pass|paws|boss)\s+(?:karo|kar|do|video)?\b": "pause",
    r"\b(?:rijum|rijume|rigum|resum|resumed)\b": "resume",
    r"\b(?:fulskrin|fulscrin|full\s+skrin)\b": "fullscreen",
    r"\b(?:sabscraib|sabscribe|subscrive)\b": "subscribe",
    r"\b(?:kament|kaments|coment)\b": "comments",
    r"\b(?:shot|shots|shirt|shirts|shart|sort|sorts|chot|chote)\b": "short",
    r"\b(?:watsapp|whatsap|whatapp|watsap)\b": "whatsapp",
}

# Ordinal dictionary
ORDINALS = {
    "first": 1, "1st": 1, "pehla": 1, "pehli": 1, "1": 1, "one": 1,
    "second": 2, "2nd": 2, "dusra": 2, "doosra": 2, "dusri": 2, "2": 2, "two": 2,
    "third": 3, "3rd": 3, "teesra": 3, "tisra": 3, "teesri": 3, "3": 3, "three": 3,
    "fourth": 4, "4th": 4, "chautha": 4, "chauthi": 4, "4": 4,
    "fifth": 5, "5th": 5, "panchwa": 5, "panchvi": 5, "5": 5,
}


class NormalizedEntities(BaseModel):
    application: Optional[str] = None
    target_contact: Optional[str] = None
    ordinal_index: Optional[int] = None
    search_query: Optional[str] = None
    message_body: Optional[str] = None
    volume_level: Optional[int] = None
    is_short: bool = False


class LanguageNormalizer:
    """Normalizes natural language inputs and extracts parameters."""

    @classmethod
    def normalize_text(cls, raw_text: str) -> str:
        """Convert Devanagari, clean slips, and normalize whitespace."""
        if not raw_text:
            return ""
        text = raw_text.strip()

        # 1. Transliterate Devanagari tokens
        for dev, lat in DEVANAGARI_MAP.items():
            text = text.replace(dev, lat)

        text_lower = text.lower()

        # 2. Repair phonetic STT slips
        for pat, rep in PHONETIC_SLIPS.items():
            text_lower = re.sub(pat, rep, text_lower, flags=re.IGNORECASE)

        # 3. Clean repetitive particles
        cleaned = re.sub(r"\s+", " ", text_lower).strip()
        return cleaned

    @classmethod
    def extract_entities(cls, normalized_text: str) -> NormalizedEntities:
        """Extract canonical entities from normalized text."""
        entities = NormalizedEntities()
        text = normalized_text.lower()

        # 1. Check for Shorts keyword
        if any(w in text for w in ["short", "shorts", "reel", "reels"]):
            entities.is_short = True

        # 2. Detect Application
        if "youtube" in text:
            entities.application = "youtube"
        elif "whatsapp" in text:
            entities.application = "whatsapp"
        elif any(w in text for w in ["chrome", "browser", "google"]):
            entities.application = "browser"
        elif "spotify" in text:
            entities.application = "spotify"

        # 3. Extract Ordinal Index
        for word, idx in ORDINALS.items():
            if re.search(rf"\b{re.escape(word)}\b", text):
                entities.ordinal_index = idx
                break

        # 4. Extract Contact Name (e.g. "Harsh ko message bhejo", "Call Shivam")
        m_contact = re.search(r"\b([a-zA-Z]+)\s+(?:ko|se)\s+(?:message|call|phone|bhejo)\b", text)
        if m_contact:
            c = m_contact.group(1).title()
            if c.lower() not in ["whatsapp", "youtube", "chrome", "video"]:
                entities.target_contact = c
        elif re.search(r"\b(?:call|phone)\s+([a-zA-Z]+)\b", text):
            c_match = re.search(r"\b(?:call|phone)\s+([a-zA-Z]+)\b", text)
            if c_match:
                c = c_match.group(1).title()
                if c.lower() not in ["karo", "lagao", "mila", "whatsapp", "video"]:
                    entities.target_contact = c

        # 5. Extract Message Body
        m_msg = re.search(r"\b(?:message|msg|text)\s*(?:karo|bhejo|likho)?\s*[:,\-]?\s+(.+)$", text)
        if m_msg:
            body = m_msg.group(1).strip()
            # Clean trailing verb particles
            body = re.sub(r"\b(bhej\s+do|bhejo|kar\s+do|karo)\b$", "", body).strip()
            if body and body.lower() not in ["harsh", "shivam"]:
                entities.message_body = body

        # 6. Extract Search Query
        m_search = re.search(r"\b(?:search|dhoondo|find)\s+(?:karo\s+)?(.+?)(?:\s+(?:on|in)\s+youtube|\s+youtube\s+pe)?$", text)
        if m_search:
            q = m_search.group(1).strip()
            q = re.sub(r"\b(karo|kar\s+do|pe|par|on|in|youtube|google)\b", "", q).strip()
            if q:
                entities.search_query = q

        # 7. Extract Volume Level (e.g. "set volume to 50%", "volume 30 karo")
        m_vol = re.search(r"\b(?:volume|aawaz)\s+(?:to\s+)?(\d{1,3})\s*(?:%|percent)?\b", text)
        if m_vol:
            entities.volume_level = min(100, max(0, int(m_vol.group(1))))

        return entities
