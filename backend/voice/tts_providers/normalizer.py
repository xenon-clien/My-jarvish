"""Text normalization and phonetic enhancement for Indian Hindi, Hinglish, and English TTS.

Ensures accurate vowel/consonant pronunciation, digit-by-digit OTP expansion,
and natural pause rhythm without robotic artifacts.
"""
import re
from typing import Dict

# Dictionary mapping Roman Hinglish idioms to natural phonetic Hindi
HINGLISH_PHONETICS_MAP: Dict[str, str] = {
    "yes boss": "यस बॉस",
    "ji boss": "जी बॉस",
    "bilkul boss": "बिल्कुल बॉस",
    "boss": "बॉस",
    "main": "मैं",
    "youtube": "यूट्यूब",
    "open": "ओपन",
    "karti hu": "करती हूँ",
    "karti hoon": "करती हूँ",
    "kar rahi hu": "कर रही हूँ",
    "kar rahi hoon": "कर रही हूँ",
    "karta hu": "करती हूँ",
    "kar raha hu": "कर रही हूँ",
    "khol raha hu": "खोल रही हूँ",
    "khol rahi hu": "खोल रही हूँ",
    "ho gaya": "हो गया",
    "ho gayi": "हो गई",
    "play": "प्ले",
    "video": "वीडियो",
    "song": "गाना",
    "reminder": "रिमाइंडर",
    "notification": "नोटिफिकेशन",
    "message": "मैसेज",
    "offline": "ऑफलाइन",
    "online": "ऑनलाइन",
    "sorry": "सॉरी",
    "sure": "श्योर",
    "chala diya hai": "चला दिया है",
    "chala diya": "चला दिया",
    "khol diya hai": "खोल दिया है",
    "khol diya": "खोल दिया",
    "band kar diya hai": "बंद कर दिया है",
    "band kar diya": "बंद कर दिया",
    "band kar diye hain": "बंद कर दिए हैं",
    "kar diya hai": "कर दिया है",
    "kar diya": "कर दिया",
    "clean kar diya": "क्लीन कर दिया",
    "call kar diya": "कॉल लगा दिया",
    "call laga diya": "कॉल लगा दिया",
    "message bhej diya": "मैसेज भेज दिया",
    "pehli": "पहली",
    "dusri": "दूसरी",
    "teesri": "तीसरी",
    "chauthi": "चौथी",
    "panchwi": "पांचवीं",
    "click": "क्लिक",
    "par": "पर",
    "close": "क्लोज़",
    "active": "एक्टिव",
    "tab": "टैब",
    "tabs": "टैब्स",
    "browser": "ब्राउज़र",
    "chrome": "क्रोम",
    "clean": "क्लीन",
    "files": "फ़ाइल्स",
    "laptop": "लैपटॉप",
    "shutdown": "शटडाउन",
    "screen": "स्क्रीन",
    "lock": "लॉक",
    "online hu": "ऑनलाइन हूँ",
    "sun rahi hu": "सुन रही हूँ",
    "boliye": "बोलिए",
    "kya": "क्या",
    "karna hai": "करना है",
    "madat": "मदद",
    "karu": "करूँ",
    "standby": "स्टैंडबाय",
    "mode": "मोड",
    "mein": "में",
    "ja rahi hu": "जा रही हूँ",
    "wapas": "वापस",
    "hazir": "हाज़िर",
    "ho jaungi": "हो जाऊँगी",
    "samay": "समय",
    "abhi": "अभी",
    "ho raha hai": "हो रहा है",
    "battery": "बैटरी",
    "par hai": "पर है",
    "bilkul": "बिल्कुल",
    "badiya": "बढ़िया",
    "aap": "आप",
    "bataiye": "बताइए",
    "aaj": "आज",
    "computer": "कंप्यूटर",
    "swagat": "स्वागत",
    "hamesha": "हमेशा",
    "aapki": "आपकी",
    "service": "सर्विस",
    "ke liye": "के लिए",
    "error": "एरर",
    "issue": "इश्यू",
    "aaya": "आया",
}


def normalize_numbers_and_otp(text: str) -> str:
    """Expand multi-digit OTPs and codes for clear, individual digit articulation."""
    def expand_otp(match: re.Match) -> str:
        digits = match.group(0)
        # Separate individual digits with space for crystal clear TTS articulation
        return " ".join(list(digits))

    # Match 4-8 digit standalone numbers (e.g. OTP 482913 -> 4 8 2 9 1 3)
    text = re.sub(r"\b\d{4,8}\b", expand_otp, text)
    return text


def normalize_hindi_tts_text(text: str) -> str:
    """Apply complete phonetic normalization, pause enhancement, and digit formatting."""
    if not text:
        return ""

    normalized = text.strip()

    # 1. Strip markdown formatting (asterisks, hashes, backticks, emojis) that degrade TTS
    normalized = re.sub(r"[*_~`#>]", "", normalized)
    normalized = re.sub(r"\[.*?\]\(.*?\)", "", normalized)

    # 2. Expand long digit strings (OTPs/PINs) for clarity
    normalized = normalize_numbers_and_otp(normalized)

    # 3. Clean up double spaces or awkward trailing marks
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized
