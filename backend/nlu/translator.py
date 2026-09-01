"""Universal Human-Language Semantic Translator for JARVIS AI.

Translates any raw input (Pure Hindi, Devanagari, Regional Dialects, Hinglish, English)
into a canonical semantic representation that can be executed deterministically on the first try.
"""
import re
from typing import Tuple, Optional, Dict, Any
from backend.core.logger import get_logger

logger = get_logger("UniversalTranslator")


class UniversalLanguageTranslator:
    """Real-time Multi-Lingual Semantic Translation Engine."""

    # 1. Comprehensive Devanagari & Dialectal Dictionary
    DEVANAGARI_TRANSLATIONS = {
        # Media & Playback
        "शॉर्ट्स": "shorts", "शॉर्ट": "short", "शॉट": "short", "शॉट्स": "shorts",
        "वीडियो": "video", "विडियो": "video", "गाना": "song", "गीत": "song", "म्यूजिक": "music",
        "चलाओ": "play", "चला": "play", "बजाओ": "play", "बजा": "play", "लगाओ": "play", "लगा": "play",
        "रोको": "pause", "रोक": "pause", "पॉज": "pause", "बंद": "pause", "थम": "pause",
        "चालू": "resume", "रिज्यूम": "resume", "वापस": "resume", "फिर": "again",
        "आगे": "forward", "बढ़ाओ": "increase", "बढ़ा": "increase", "तेज": "fast",
        "पीछे": "backward", "घटाओ": "decrease", "धीमा": "slow", "कम": "decrease",
        "आवाज": "volume", "ध्वनि": "volume", "म्यूट": "mute", "अनम्यूट": "unmute",
        "बड़ा": "fullscreen", "बड़ी": "fullscreen", "फुलस्क्रीन": "fullscreen",
        "छोटा": "miniplayer", "छोटी": "miniplayer", "मिनी": "miniplayer",
        "सबटाइटल": "subtitles", "कैप्शन": "captions",

        # Ordinals & Numbers
        "पहला": "1st", "पहली": "1st", "प्रथम": "1st", "एक": "1",
        "दूसरा": "2nd", "दूसरी": "2nd", "दो": "2nd",
        "तीसरा": "3rd", "तीसरी": "3rd", "तीन": "3rd",
        "चौथा": "4th", "चौथी": "4th", "चार": "4th",
        "पांचवां": "5th", "पांचवीं": "5th", "पांच": "5th",
        "दायां": "right", "दाएं": "right", "बायां": "left", "बाएं": "left",
        "ऊपर": "up", "नीचे": "down",

        # Actions & Verbs
        "क्लिक": "click", "दबाओ": "click", "दबा": "click", "खोलो": "open", "खोल": "open",
        "स्क्रॉल": "scroll", "सर्च": "search", "ढूंढो": "search", "खोजो": "search",
        "लाइक": "like", "पसंद": "like", "डिसलाइक": "dislike", "शेयर": "share", "भेजो": "send",
        "सब्सक्राइब": "subscribe", "टिप्पणी": "comments", "कमेंट": "comments", "कमेंट्स": "comments",
        "काटो": "close", "हटाओ": "close", "समाप्त": "end",
    }

    # 2. Regional & Colloquial Phrasing Translation Patterns
    IDIOMATIC_TRANSLATIONS = [
        # Compound phrases
        (r"\b(?:scroll\s+karo?\s+(?:aur|and|fir|then|ke\s+baad)\s+(?:pehla|1st|first)\s+(?:short|shorts?))\b", "scroll down and click 1st short"),
        (r"\b(?:scroll\s+karo?\s+(?:aur|and|fir|then|ke\s+baad)\s+(?:pehli|1st|first)\s+(?:video|vid))\b", "scroll down and click 1st video"),
        
        # Shorts execution
        (r"\b(?:agla|next)\s+(?:short|shorts?|shot)\s*(?:dikhao|chalao|laga)?\b", "agla short dikhao"),
        (r"\b(?:pichla|prev|previous)\s+(?:short|shorts?|shot)\s*(?:dikhao|chalao|laga)?\b", "pichla short dikhao"),
        (r"\b(?:pehla|pehli|first|1st)\s+(?:short|shorts|shot|shirt|sort|chot)\s*(?:pe\s+click|chalao|kholo|play|laga|dekho)?\b", "click 1st short"),
        (r"\b(?:dusra|dusri|second|2nd)\s+(?:short|shorts|shot|shirt|sort|chot)\s*(?:pe\s+click|chalao|kholo|play|laga|dekho)?\b", "click 2nd short"),
        (r"\b(?:teesra|teesri|third|3rd)\s+(?:short|shorts|shot|shirt|sort|chot)\s*(?:pe\s+click|chalao|kholo|play|laga|dekho)?\b", "click 3rd short"),
        (r"\b(?:chautha|chauthi|fourth|4th)\s+(?:short|shorts|shot|shirt|sort|chot)\s*(?:pe\s+click|chalao|kholo|play|laga|dekho)?\b", "click 4th short"),
        (r"\b(?:panchwa|panchvi|fifth|5th)\s+(?:short|shorts|shot|shirt|sort|chot)\s*(?:pe\s+click|chalao|kholo|play|laga|dekho)?\b", "click 5th short"),
        (r"\b(?:short|shorts|shot|shirt)\s+(?:chalao|kholo|play|laga|on\s+karo|dikhao|shuru\s+karo)\b", "click 1st short"),

        # Video thumbnail execution
        (r"\b(?:pehli|pehla|first|1st)\s+video\s*(?:pe\s+click|chalao|kholo|play|laga|dekho)\b", "click 1st video"),
        (r"\b(?:dusri|dusra|second|2nd)\s+video\s*(?:pe\s+click|chalao|kholo|play|laga|dekho)\b", "click 2nd video"),
        (r"\b(?:teesri|teesra|third|3rd)\s+video\s*(?:pe\s+click|chalao|kholo|play|laga|dekho)\b", "click 3rd video"),
        (r"\b(?:chauthi|chautha|fourth|4th)\s+video\s*(?:pe\s+click|chalao|kholo|play|laga|dekho)\b", "click 4th video"),

        # Navigation & Scrolling
        (r"\b(?:neeche|niche|thoda\s+neeche|thoda\s+niche|down)\s+scroll\b", "scroll down"),
        (r"\bscroll\s+(?:karo|kar|do|karna)\b", "scroll down"),
        (r"\b(?:upar|top|up|thoda\s+upar)\s+scroll\b", "scroll up"),

        # Playback controls
        (r"\b(?:video\s+rok\s+do|rok\s+do|video\s+pause|pause\s+karo|thoda\s+rok)\b", "pause video"),
        (r"\b(?:video\s+chala\s+do|chala\s+do|video\s+chalao|unpause\s+karo|resume\s+karo)\b", "resume video"),
        (r"\b(?:aage\s+badhao|aage\s+karo|aage\s+chalao|10\s*sec\s*aage|forward\s+karo)\b", "forward 10 seconds"),
        (r"\b(?:peeche\s+badhao|peeche\s+karo|10\s*sec\s*peeche|rewind\s+karo)\b", "rewind 10 seconds"),
        (r"\b(?:aawaz\s+badhao|sound\s+badhao|volume\s+badhao|tez\s+karo)\b", "volume up"),
        (r"\b(?:aawaz\s+kam|sound\s+kam|volume\s+kam|dheere\s+karo)\b", "volume down"),
        (r"\b(?:fullscreen\s+karo|badi\s+screen\s+karo|full\s+screen)\b", "fullscreen"),
        (r"\b(?:chhota\s+karo|chhoti\s+screen|miniplayer\s+karo)\b", "miniplayer"),
    ]

    @classmethod
    def translate_to_canonical(cls, raw_text: str) -> Tuple[str, str]:
        """Translate raw user input in any language/script into canonical command representation."""
        if not raw_text or not raw_text.strip():
            return "", "en"

        text = raw_text.strip()

        # Step 1: Detect script
        has_devanagari = bool(re.search(r"[\u0900-\u097F]", text))
        src_lang = "hi" if has_devanagari else "hinglish"

        # Step 2: Convert Devanagari words to Hinglish keywords
        if has_devanagari:
            for dev, rom in cls.DEVANAGARI_TRANSLATIONS.items():
                text = text.replace(dev, rom)

        # Step 3: Lowercase & normalize spaces
        norm = re.sub(r"\s+", " ", text.lower()).strip()

        # Step 4: Apply Idiomatic Translation Patterns
        for pat, rep in cls.IDIOMATIC_TRANSLATIONS:
            if re.search(pat, norm, flags=re.IGNORECASE):
                norm = re.sub(pat, rep, norm, flags=re.IGNORECASE)
                break

        logger.debug(f"Universal Translation: '{raw_text}' -> '{norm}' (src: {src_lang})")
        return norm, src_lang
