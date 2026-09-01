"""Language Normalizer for Hindi, English, and Hinglish speech understanding."""
import re
from typing import Tuple


class LanguageNormalizer:
    """Normalizes natural user transcripts, removes casual fillers, repairs STT artifacts, and converts Hindi numbers."""

    # STT phonetic corrections & common speech-to-text slips
    STT_CORRECTIONS = {
        r"\bkal\s+lagao\b": "call lagao",
        r"\bkal\s+karo\b": "call karo",
        r"\bphon\b": "phone",
        r"\bwhatapp\b": "whatsapp",
        r"\bwtsap\b": "whatsapp",
        r"\bwhtsapp\b": "whatsapp",
        r"\byutube\b": "youtube",
        r"\byoutub\b": "youtube",
        r"\byou\s+tube\b": "youtube",
        r"\byt\b": "youtube",
        r"\bchrm\b": "chrome",
        r"\bgogle\b": "google",
        r"\bmesage\b": "message",
        r"\bmsg\b": "message",
        r"\bm1nim1se\b": "minimize",
        r"\bminimise\b": "minimize",
        r"\bmutee\b": "mute",
        r"\bunmutee\b": "unmute",
        r"\b(?:pouse|pows|pos|paws)\b": "pause",
        r"\b(?:rijum|rijume|rigum|resum|resumed)\b": "resume",
        r"\b(?:fulskrin|fulscrin|full\s+skrin)\b": "fullscreen",
        r"\b(?:sabscraib|sabscribe|subscrive)\b": "subscribe",
        r"\b(?:kament|kaments|coment)\b": "comments",
    }

    # Number Words in Hindi/Hinglish to standard Arabic digits
    HINDI_NUMBER_WORDS = {
        r"\bpehli\b": "1st",
        r"\bpehla\b": "1st",
        r"\bdusri\b": "2nd",
        r"\bdusra\b": "2nd",
        r"\bdoosri\b": "2nd",
        r"\bdoosra\b": "2nd",
        r"\bteesri\b": "3rd",
        r"\bteesra\b": "3rd",
        r"\btisri\b": "3rd",
        r"\btisra\b": "3rd",
        r"\bchauthi\b": "4th",
        r"\bchautha\b": "4th",
        r"\bpanchvi\b": "5th",
        r"\bpanchva\b": "5th",
        r"\bek\b": "1",
        r"\bteen\b": "3",
        r"\bchar\b": "4",
        r"\bpanch\b": "5",
        r"\bchhe\b": "6",
        r"\bsaat\b": "7",
        r"\baath\b": "8",
        r"\bnau\b": "9",
        r"\bdas\b": "10",
        r"\bdus\b": "10",
        r"\bgyarah\b": "11",
        r"\bbarah\b": "12",
        r"\bpandrah\b": "15",
        r"\bbees\b": "20",
        r"\btees\b": "30",
        r"\bchalis\b": "40",
        r"\bpachas\b": "50",
    }

    # Casual Hinglish colloquialisms and verb standardizations
    VERB_NORMALIZATIONS = {
        r"\bchla\b": "chalao",
        r"\bchala\b": "chalao",
        r"\bchlao\b": "chalao",
        r"\bchala\s+de\b": "chalao",
        r"\bchala\s+do\b": "chalao",
        r"\bchala\s+dena\b": "chalao",
        r"\blaga\s+de\b": "lagao",
        r"\blaga\s+do\b": "lagao",
        r"\blaga\s+na\b": "lagao",
        r"\blaga\b": "lagao",
        r"\bkhol\s+de\b": "kholo",
        r"\bkhol\s+do\b": "kholo",
        r"\bkhol\s+na\b": "kholo",
        r"\bkhol\b": "kholo",
        r"\bopen\s+kar\b": "open karo",
        r"\bopen\s+kr\b": "open karo",
        r"\bkr\b": "karo",
        r"\bkar\b": "karo",
        r"\bkrdo\b": "kar do",
        r"\bkrna\b": "karna",
        r"\bbhej\s+de\b": "bhejo",
        r"\bbhej\s+do\b": "bhejo",
        r"\bbhej\b": "bhejo",
        r"\bdhundh\b": "dhoondo",
        r"\bdhundho\b": "dhoondo",
        r"\bdhoond\b": "dhoondo",
        r"\bdekho\b": "dhoondo",
        r"\bpata\s+kar\b": "dhoondo",
        r"\brok\s+de\b": "pause karo",
        r"\brok\s+do\b": "pause karo",
        r"\broko\b": "pause karo",
        r"\brok\b": "pause karo",
        r"\bthoda\s+rok\b": "pause karo",
        r"\bband\s+kar\b": "close karo",
        r"\bband\s+karo\b": "close karo",
        r"\bband\s+kr\b": "close karo",
        r"\bhatao\b": "close karo",
        r"\bhata\s+de\b": "close karo",
        r"\bunpause\s+karo\b": "resume karo",
        r"\bunpause\b": "resume",
        r"\btez\s+karo\b": "speed badhao",
        r"\bdheere\s+karo\b": "speed kam karo",
        r"\bbada\s+karo\b": "fullscreen karo",
    }

    # Conversational non-essential filler words (only removed when not part of an entity or message)
    FILLERS = [
        r"^(?:bhai|bro|yaar|zara|zra|are|arre|suno|please|plz|oie|oyee|hey|hello)\s+",
        r"\s+(?:na|yaar|bhai|bro|plz|please|zara|zra)$",
        r"\b(?:zara|zra)\b",
    ]

    @classmethod
    def normalize(cls, text: str) -> Tuple[str, str]:
        """Normalize raw transcript, remove filler tokens, convert numbers, and detect language."""
        if not text:
            return "", "english"

        cleaned = text.strip()

        # Step 1: Detect primary language
        language = cls._detect_language(cleaned)

        # Step 2: Apply STT phonetic repairs
        for pattern, replacement in cls.STT_CORRECTIONS.items():
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

        # Step 3: Remove conversational filler prefixes and suffixes
        for filler in cls.FILLERS:
            cleaned = re.sub(filler, " ", cleaned, flags=re.IGNORECASE).strip()

        # Step 4: Normalize colloquial Hinglish verbs
        for pattern, replacement in cls.VERB_NORMALIZATIONS.items():
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

        # Step 5: Normalize number words for durations and ordinals
        for pattern, replacement in cls.HINDI_NUMBER_WORDS.items():
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

        # Step 6: Collapse multiple spaces
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned, language

    @staticmethod
    def _detect_language(text: str) -> str:
        """Detect whether input is pure Hindi, English, or mixed Hinglish."""
        # Devanagari Unicode range: \u0900-\u097F
        if re.search(r"[\u0900-\u097F]", text):
            return "hindi"

        hindi_markers = [
            "karo", "kholo", "chalao", "lagao", "bhejo", "dhoondo", "ka", "ki", "ke",
            "ko", "mein", "pe", "par", "hai", "yeh", "woh", "isko", "usko", "kya",
            "kahan", "bhai", "yaar", "aur", "se", "na", "ab", "wala", "wali"
        ]
        words = text.lower().split()
        hindi_count = sum(1 for w in words if w in hindi_markers)

        if hindi_count >= 1:
            return "hinglish"
        return "english"
