"""Semantic Intent Engine for JARVIS AI.

Maps normalized natural language transcripts into universal structured intents,
computes candidate scores, handles contextual disambiguation, and splits multi-intents.
"""
import re
from typing import List, Optional, Tuple
from backend.core.logger import get_logger
from backend.nlu.entities import EntityResolver
from backend.nlu.models import (
    CandidateInterpretation,
    ExtractedEntities,
    SemanticParseResult,
    UniversalIntent,
)
from backend.nlu.normalizer import LanguageNormalizer
from backend.skills.context import app_state_manager

logger = get_logger("SemanticIntentEngine")


class SemanticIntentEngine:
    """Universal application-agnostic semantic intent understanding engine."""

    # Semantic Intent Signatures: Universal intent semantic clusters
    INTENT_SEMANTIC_PATTERNS = {
        # ── Communication ───────────────────────────────────────────────────
        UniversalIntent.CALL_CONTACT: [
            r"\b(?:voice\s+call|call|phone|baat|mila)\b",
            r"\b(?:call\s+karo|call\s+lagao|phone\s+karo|phone\s+laga|phone\s+mila|baat\s+kara|call\s+maar)\b",
        ],
        UniversalIntent.VIDEO_CALL: [
            r"\b(?:video\s+call|video\s+calling)\b",
        ],
        UniversalIntent.END_CALL: [
            r"\b(?:call\s+cut|end\s+call|hang\s+up|disconnect|call\s+band)\b",
        ],
        UniversalIntent.MUTE_CALL: [
            r"\b(?:call\s+mute|call\s+unmute|mute\s+call|unmute\s+call|call\s+mic)\b",
        ],
        UniversalIntent.SEND_MESSAGE: [
            r"\b(?:message|msg|text|bolo|likho|send\s+message)\b",
        ],
        UniversalIntent.DELETE_MESSAGE: [
            r"\b(?:unsend|delete\s+message|draft\s+clear|clear\s+draft)\b",
        ],
        UniversalIntent.STATUS_VIEW: [
            r"\b(?:status\s+dekho|whatsapp\s+status|status\s+kholo|view\s+status)\b",
        ],

        # ── App Lifecycle ────────────────────────────────────────────────────
        UniversalIntent.OPEN_APP: [
            r"\b(?:open|kholo|start|launch|on\s+kar|le\s+chalo|khol|khol\s+de|khol\s+do|laga\s+de|laga\s+do|lagao|laga|chala\s+de|chalao)\b",
        ],
        UniversalIntent.CLOSE_APP: [
            r"\b(?:close|band\s+karo|hatao|exit|quit|band\s+kar)\b",
        ],
        UniversalIntent.MINIMIZE: [
            r"\b(?:minimize|chhota\s+karo|hide\s+window)\b",
        ],
        UniversalIntent.MAXIMIZE: [
            r"\b(?:maximize|maximize\s+window)\b",
        ],
        UniversalIntent.CLEAN_JUNK: [
            r"\b(?:faltu\s+tabs|clean\s+tabs|cleanup|clean\s+apps|idle\s+apps|faltu\s+tabs\s+band\s+karo|faltu\s+tabs\s+band|faltu)\b",
        ],

        # ── Media Playback ───────────────────────────────────────────────────
        UniversalIntent.PAUSE: [
            r"\b(?:pause|rok\s+do|rok|thoda\s+rok|pause\s+karo|stop\s+the\s+video|stop\s+video|stop|pause\s+video|video\s+pause|isko\s+rok)\b",
        ],
        UniversalIntent.RESUME: [
            r"\b(?:resume|unpause|resume\s+video|video\s+resume|continue\s+video|chala\s+do|wapas\s+chalao|phir\s+se\s+chalao|video\s+chalao)\b",
        ],
        UniversalIntent.PLAY: [
            r"\b(?:play|chalao|baja|laga|start\s+video|play\s+karo|gaana\s+chalao)\b",
        ],
        UniversalIntent.NEXT_MEDIA: [
            r"\b(?:next\s+video|agla\s+video|next\s+song|next\s+gaana|agla\s+laga|next\s+chala|agla\s+wala|agli\s+video|agla\s+video\s+chalao|agla\s+chalao)\b",
        ],
        UniversalIntent.PREVIOUS_MEDIA: [
            r"\b(?:previous\s+video|pichla\s+video|prev\s+video|pichla\s+gaana|pichla\s+laga|piche\s+chala)\b",
        ],
        UniversalIntent.SEEK_FORWARD: [
            r"\b(?:aage\s+badhao|aage\s+badha|aage\s+karo|forward|seek\s+forward|fast\s+forward|aage\s+chalao|aage\s+le\s+jao|(?:\d+)\s*(?:sec|seconds?)\s*aage|skip\s+(?:\d+)|aage\s+kar|thoda\s+aage|fast\s+forward\s+(?:\d+)\s*sec|(?:\d+)\s*seconds?\s*forward)\b",
        ],
        UniversalIntent.SEEK_BACKWARD: [
            r"\b(?:peeche\s+karo|rewind|seek\s+backward|backward|backwards|peeche\s+le|peeche\s+badhao|(?:\d+)\s*(?:sec|seconds?)\s*peeche|rewind\s+(?:\d+)|peeche\s+kar|thoda\s+peeche|(?:\d+)s\s*rewind|(?:\d+)\s*seconds?\s*backward)\b",
        ],
        UniversalIntent.SEEK_TIMESTAMP: [
            r"\b(?:(\d+)\s*(?:minute|min)\s*(?:(\d+)\s*(?:second|sec))?|(\d+:\d+)|\b(\d+)\s*(?:minute|min|second|sec)\s*(?:par|pe|se|jump|seek|le\s+jao)|iss\s+time\s+pe|exact\s+time|timestamp|time\s+par)\b",
        ],
        UniversalIntent.SPEED_UP: [
            r"\b(?:speed\s+badhao|fast\s+karo|playback\s+speed\s+badhao|speed\s+up|tez\s+chalao|faster)\b",
        ],
        UniversalIntent.SPEED_DOWN: [
            r"\b(?:speed\s+kam|slow\s+karo|playback\s+speed\s+kam|speed\s+down|dheere\s+chalao|slower)\b",
        ],
        UniversalIntent.FULLSCREEN: [
            r"\b(?:fullscreen|full\s+screen|bada\s+karo|large\s+screen|screen\s+badi\s+karo)\b",
        ],
        UniversalIntent.THEATER_MODE: [
            r"\b(?:theater\s+mode|theatre\s+mode|cinema\s+mode)\b",
        ],
        UniversalIntent.MINIPLAYER: [
            r"\b(?:miniplayer|mini\s+player|chhota\s+player|chhoti\s+screen|chhota\s+karo|chhoti\s+karo)\b",
        ],
        UniversalIntent.CAPTIONS: [
            r"\b(?:captions|subtitles|subtitle|caption|subtitles\s+on|subtitles\s+off)\b",
        ],
        UniversalIntent.REPLAY: [
            r"\b(?:replay|restart\s+video|shuru\s+se\s+chalao|start\s+again|fir\s+se\s+laga)\b",
        ],
        UniversalIntent.NEXT_SHORT: [
            r"\b(?:next\s+short|agla\s+short|niche\s+short|scroll\s+short|agla\s+short\s+dikhao|agla\s+short\s+chalao)\b",
        ],
        UniversalIntent.PREV_SHORT: [
            r"\b(?:pichla\s+short|prev\s+short|upar\s+short|pichla\s+short\s+dikhao|pichla\s+short\s+chalao)\b",
        ],
        UniversalIntent.VOLUME_UP: [
            r"\b(?:volume\s+(?:thoda\s+)?(?:up|badhao|badha)|aawaz\s+(?:thodi\s+)?badhao|sound\s+(?:thoda\s+)?badhao|sound\s+up|volume\s+up|aawaz\s+badhao|volume\s+badhao)\b",
        ],
        UniversalIntent.VOLUME_DOWN: [
            r"\b(?:volume\s+(?:thoda\s+)?(?:down|kam)|aawaz\s+(?:thodi\s+)?kam|sound\s+(?:thoda\s+)?kam|sound\s+down|volume\s+down|aawaz\s+kam|volume\s+kam)\b",
        ],
        UniversalIntent.MUTE_AUDIO: [
            r"\b(?:mute\s+audio|mute|mute\s+karo|aawaz\s+band)\b",
        ],
        UniversalIntent.UNMUTE_AUDIO: [
            r"\b(?:unmute\s+audio|unmute|unmute\s+karo|aawaz\s+kholo)\b",
        ],

        # ── Social & Interaction ─────────────────────────────────────────────
        UniversalIntent.LIKE: [
            r"\b(?:like\s+karo|like\s+thok|like\s+maar|like\s+this|video\s+like)\b",
        ],
        UniversalIntent.DISLIKE: [
            r"\b(?:dislike\s+karo|dislike\s+maar|dislike\s+this)\b",
        ],
        UniversalIntent.SUBSCRIBE: [
            r"\b(?:subscribe\s+karo|subscribe\s+maar|subscribe\s+thok)\b",
        ],
        UniversalIntent.SHARE: [
            r"\b(?:share\s+karo|share\s+video|forward\s+maar|share\s+this)\b",
        ],
        UniversalIntent.COMMENTS_VIEW: [
            r"\b(?:comments\s+dikhao|comments\s+padho|scroll\s+comments|comments\s+khol)\b",
        ],
        UniversalIntent.COMMENTS_HIDE: [
            r"\b(?:comments\s+band|video\s+par\s+jao|comments\s+hata)\b",
        ],

        # ── Navigation & Selection ───────────────────────────────────────────
        UniversalIntent.SCROLL_UP: [
            r"\b(?:upar\s+scroll|scroll\s+up|upar\s+karo|upar\s+le\s+jao|thoda\s+upar|page\s+up|upar\s+chalo|top\s+par\s+jao)\b",
        ],
        UniversalIntent.SCROLL_DOWN: [
            r"\b(?:niche\s+scroll|scroll\s+down|neeche\s+scroll|thoda\s+scroll|page\s+scroll|niche\s+karo|neeche\s+karo|thoda\s+niche|page\s+down|niche\s+chalo|neeche\s+chalo|scroll\s+karo|scroll\s+kar|scroll)\b",
        ],
        UniversalIntent.SELECT: [
            r"\b(?:select|click|dabao|chuno|choose|ispe\s+jao|isko\s+kholo|first\s+video|second\s+video|third\s+video|1st\s+video|2nd\s+video|3rd\s+video|pehli\s+video|dusri\s+video|teesri\s+video|pehla\s+video|dusra\s+video|teesra\s+video|play\s+first|play\s+second|play\s+third|play\s+1st|play\s+2nd|play\s+3rd|right\s+side\s+wali|right\s+side\s+video|sidebar\s+video|number\s+\d+|pehla\s+short|first\s+short|1st\s+short|dusra\s+short|2nd\s+short|teesra\s+short|3rd\s+short)\b",
        ],
        UniversalIntent.SEARCH: [
            r"\b(?:search|dhoondo|find|dhundho|pata\s+karo|khojo|lookup)\b",
        ],

        # ── Conversational ───────────────────────────────────────────────────
        UniversalIntent.GREETING: [
            r"^(?:hello|hi|hey|namaste|pranam|hello\s+jarvis|hi\s+jarvis)$",
        ],
        UniversalIntent.IDENTITY: [
            r"^(?:who\s+are\s+you|tum\s+kaun\s+ho|aap\s+kaun\s+ho|what\s+are\s+you)$",
        ],
        UniversalIntent.THANK_YOU: [
            r"^(?:thank\s+you|thanks|shukriya|dhanyawad|thanks\s+jarvis)$",
        ],
    }

    @classmethod
    def parse(cls, raw_transcript: str) -> SemanticParseResult:
        """Parse raw transcript into structured semantic intent with entities and target app."""
        if not raw_transcript or not raw_transcript.strip():
            return SemanticParseResult(
                raw_transcript="",
                normalized_transcript="",
                detected_language="english",
                primary_intent=UniversalIntent.UNKNOWN,
                confidence=0.0,
                entities=ExtractedEntities(),
            )

        # 1. Universal Semantic Translation across Languages & Dialects
        from backend.nlu.translator import UniversalLanguageTranslator
        translated, detected_lang = UniversalLanguageTranslator.translate_to_canonical(raw_transcript)

        # 2. Normalize Language & Repair STT Artifacts
        normalized, language = LanguageNormalizer.normalize(translated)

        # ── LEVEL 1: EXACT DETERMINISTIC COMMAND ALIASES (100% Guaranteed Intent Lock) ──
        clean_raw = raw_transcript.strip().lower()
        clean_norm = normalized.strip().lower()
        clean_trans = translated.strip().lower()

        EXACT_MAP = {
            # ── YouTube Shorts (1st to 5th Shorts) ──
            # 1st Short
            "play first short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            "play the first short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            "first short play karo": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            # 1st Short / Reel (Single-word & phrases)
            "1st": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, position_relative="shorts"), "youtube"),
            "first": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, position_relative="shorts"), "youtube"),
            "pehla": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, position_relative="shorts"), "youtube"),
            "pehli": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, position_relative="shorts"), "youtube"),
            "pehla wala": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, position_relative="shorts"), "youtube"),
            "open first short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            "open 1st short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            "play first short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            "first short chalao": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            "first short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            "pehla short chalao": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            "pehla short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            "pehla short pe click karo": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            "pehla short chala do": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            "pehla youtube short chalao": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            "youtube ka first short play karo": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            "youtube ka pehla short play karo": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            "पहला शॉर्ट चलाओ": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            "पहला शॉर्ट": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            "short chalao": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            "shorts chalao": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            "play short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            "play shorts": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            "reel chalao": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            "first reel": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            "pehli reel": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="short", position_relative="shorts"), "youtube"),
            # 2nd Short / Reel (Single-word & phrases)
            "2nd": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, position_relative="shorts"), "youtube"),
            "second": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, position_relative="shorts"), "youtube"),
            "dusra": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, position_relative="shorts"), "youtube"),
            "dusri": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, position_relative="shorts"), "youtube"),
            "doosra": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, position_relative="shorts"), "youtube"),
            "dusra wala": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, position_relative="shorts"), "youtube"),
            "open second short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, query="short", position_relative="shorts"), "youtube"),
            "open 2nd short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, query="short", position_relative="shorts"), "youtube"),
            "play second short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, query="short", position_relative="shorts"), "youtube"),
            "play the second short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, query="short", position_relative="shorts"), "youtube"),
            "play 2nd short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, query="short", position_relative="shorts"), "youtube"),
            "second short play karo": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, query="short", position_relative="shorts"), "youtube"),
            "second short chalao": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, query="short", position_relative="shorts"), "youtube"),
            "second short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, query="short", position_relative="shorts"), "youtube"),
            "dusra short chalao": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, query="short", position_relative="shorts"), "youtube"),
            "dusra short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, query="short", position_relative="shorts"), "youtube"),
            "dusri reel": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, query="short", position_relative="shorts"), "youtube"),
            "second reel": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, query="short", position_relative="shorts"), "youtube"),
            "dusra short pe click karo": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, query="short", position_relative="shorts"), "youtube"),
            "dusra short chala do": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, query="short", position_relative="shorts"), "youtube"),
            "दूसरा शॉर्ट चलाओ": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, query="short", position_relative="shorts"), "youtube"),
            "दूसरा शॉर्ट": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, query="short", position_relative="shorts"), "youtube"),
            # 3rd Short / Reel (Single-word & phrases)
            "3rd": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=3, position_relative="shorts"), "youtube"),
            "third": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=3, position_relative="shorts"), "youtube"),
            "teesra": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=3, position_relative="shorts"), "youtube"),
            "teesri": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=3, position_relative="shorts"), "youtube"),
            "teesra wala": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=3, position_relative="shorts"), "youtube"),
            "open third short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=3, query="short", position_relative="shorts"), "youtube"),
            "open 3rd short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=3, query="short", position_relative="shorts"), "youtube"),
            "play third short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=3, query="short", position_relative="shorts"), "youtube"),
            "play 3rd short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=3, query="short", position_relative="shorts"), "youtube"),
            "third short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=3, query="short", position_relative="shorts"), "youtube"),
            "teesra short chalao": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=3, query="short", position_relative="shorts"), "youtube"),
            "teesra short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=3, query="short", position_relative="shorts"), "youtube"),
            "teesri reel": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=3, query="short", position_relative="shorts"), "youtube"),
            "तीसरा शॉर्ट चलाओ": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=3, query="short", position_relative="shorts"), "youtube"),
            # 4th & 5th Shorts (Single-word & phrases)
            "4th": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=4, position_relative="shorts"), "youtube"),
            "fourth": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=4, position_relative="shorts"), "youtube"),
            "chautha": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=4, position_relative="shorts"), "youtube"),
            "chauthi": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=4, position_relative="shorts"), "youtube"),
            "chautha wala": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=4, position_relative="shorts"), "youtube"),
            "open fourth short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=4, query="short", position_relative="shorts"), "youtube"),
            "open 4th short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=4, query="short", position_relative="shorts"), "youtube"),
            "play fourth short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=4, query="short", position_relative="shorts"), "youtube"),
            "play 4th short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=4, query="short", position_relative="shorts"), "youtube"),
            "chautha short chalao": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=4, query="short", position_relative="shorts"), "youtube"),
            "chauthi reel": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=4, query="short", position_relative="shorts"), "youtube"),
            "चौथा शॉर्ट चलाओ": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=4, query="short", position_relative="shorts"), "youtube"),
            "5th": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=5, position_relative="shorts"), "youtube"),
            "fifth": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=5, position_relative="shorts"), "youtube"),
            "panchva": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=5, position_relative="shorts"), "youtube"),
            "panchvi": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=5, position_relative="shorts"), "youtube"),
            "panchva wala": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=5, position_relative="shorts"), "youtube"),
            "open fifth short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=5, query="short", position_relative="shorts"), "youtube"),
            "open 5th short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=5, query="short", position_relative="shorts"), "youtube"),
            "play fifth short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=5, query="short", position_relative="shorts"), "youtube"),
            "play 5th short": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=5, query="short", position_relative="shorts"), "youtube"),
            "panchva short chalao": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=5, query="short", position_relative="shorts"), "youtube"),
            "panchvi reel": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=5, query="short", position_relative="shorts"), "youtube"),
            "पांचवां शॉर्ट चलाओ": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=5, query="short", position_relative="shorts"), "youtube"),
            # Navigation (Shorts & Media)
            "next": (UniversalIntent.NEXT_SHORT, ExtractedEntities(query="short"), "youtube"),
            "agla": (UniversalIntent.NEXT_SHORT, ExtractedEntities(query="short"), "youtube"),
            "next karo": (UniversalIntent.NEXT_SHORT, ExtractedEntities(query="short"), "youtube"),
            "agla karo": (UniversalIntent.NEXT_SHORT, ExtractedEntities(query="short"), "youtube"),
            "next wala": (UniversalIntent.NEXT_SHORT, ExtractedEntities(query="short"), "youtube"),
            "agla wala": (UniversalIntent.NEXT_SHORT, ExtractedEntities(query="short"), "youtube"),
            "next short": (UniversalIntent.NEXT_SHORT, ExtractedEntities(query="short"), "youtube"),
            "agla short": (UniversalIntent.NEXT_SHORT, ExtractedEntities(query="short"), "youtube"),
            "agla short dikhao": (UniversalIntent.NEXT_SHORT, ExtractedEntities(query="short"), "youtube"),
            "agla short chalao": (UniversalIntent.NEXT_SHORT, ExtractedEntities(query="short"), "youtube"),
            "agli reel": (UniversalIntent.NEXT_SHORT, ExtractedEntities(query="short"), "youtube"),
            "next reel": (UniversalIntent.NEXT_SHORT, ExtractedEntities(query="short"), "youtube"),
            "prev": (UniversalIntent.PREV_SHORT, ExtractedEntities(query="short"), "youtube"),
            "previous": (UniversalIntent.PREV_SHORT, ExtractedEntities(query="short"), "youtube"),
            "pichla": (UniversalIntent.PREV_SHORT, ExtractedEntities(query="short"), "youtube"),
            "pichla wala": (UniversalIntent.PREV_SHORT, ExtractedEntities(query="short"), "youtube"),
            "previous short": (UniversalIntent.PREV_SHORT, ExtractedEntities(query="short"), "youtube"),
            "pichla short": (UniversalIntent.PREV_SHORT, ExtractedEntities(query="short"), "youtube"),
            "pichla short dikhao": (UniversalIntent.PREV_SHORT, ExtractedEntities(query="short"), "youtube"),
            "pichli reel": (UniversalIntent.PREV_SHORT, ExtractedEntities(query="short"), "youtube"),
            "prev reel": (UniversalIntent.PREV_SHORT, ExtractedEntities(query="short"), "youtube"),
            # YouTube Videos
            "play first video": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="video", position_relative="main"), "youtube"),
            "pehli video pe click karo": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="video", position_relative="main"), "youtube"),
            "pehli video chalao": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=1, query="video", position_relative="main"), "youtube"),
            "play second video": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, query="video", position_relative="main"), "youtube"),
            "dusri video pe click karo": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, query="video", position_relative="main"), "youtube"),
            "dusri video chalao": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=2, query="video", position_relative="main"), "youtube"),
            # Cursor & Hover Clicking
            "ispe click karo": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=0, position_relative="cursor"), "youtube"),
            "isko chalao": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=0, position_relative="cursor"), "youtube"),
            "isko play karo": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=0, position_relative="cursor"), "youtube"),
            "ispe chalao": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=0, position_relative="cursor"), "youtube"),
            "jahan cursor hai": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=0, position_relative="cursor"), "youtube"),
            "cursor wala chalao": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=0, position_relative="cursor"), "youtube"),
            "play this": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=0, position_relative="cursor"), "youtube"),
            "click this": (UniversalIntent.SELECT, ExtractedEntities(ordinal_index=0, position_relative="cursor"), "youtube"),
            # Volume Controls & Voice Adjustments
            "awaj badhao": (UniversalIntent.VOLUME_UP, ExtractedEntities(), "system"),
            "awaz badhao": (UniversalIntent.VOLUME_UP, ExtractedEntities(), "system"),
            "aawaz badhao": (UniversalIntent.VOLUME_UP, ExtractedEntities(), "system"),
            "awaj badhao youtube mein": (UniversalIntent.VOLUME_UP, ExtractedEntities(), "youtube"),
            "awaz badhao youtube mein": (UniversalIntent.VOLUME_UP, ExtractedEntities(), "youtube"),
            "volume badhao": (UniversalIntent.VOLUME_UP, ExtractedEntities(), "system"),
            "volume up": (UniversalIntent.VOLUME_UP, ExtractedEntities(), "system"),
            "sound badhao": (UniversalIntent.VOLUME_UP, ExtractedEntities(), "system"),
            "awaj tez karo": (UniversalIntent.VOLUME_UP, ExtractedEntities(), "system"),
            "awaz tez karo": (UniversalIntent.VOLUME_UP, ExtractedEntities(), "system"),
            "awaj kam karo": (UniversalIntent.VOLUME_DOWN, ExtractedEntities(), "system"),
            "awaz kam karo": (UniversalIntent.VOLUME_DOWN, ExtractedEntities(), "system"),
            "aawaz kam karo": (UniversalIntent.VOLUME_DOWN, ExtractedEntities(), "system"),
            "awaj kam": (UniversalIntent.VOLUME_DOWN, ExtractedEntities(), "system"),
            "awaz kam": (UniversalIntent.VOLUME_DOWN, ExtractedEntities(), "system"),
            "volume kam": (UniversalIntent.VOLUME_DOWN, ExtractedEntities(), "system"),
            "volume down": (UniversalIntent.VOLUME_DOWN, ExtractedEntities(), "system"),
            "mute karo": (UniversalIntent.MUTE_AUDIO, ExtractedEntities(), "system"),
            "unmute karo": (UniversalIntent.UNMUTE_AUDIO, ExtractedEntities(), "system"),
            # Negative & Explicit Navigation
            "downloads kholo": (UniversalIntent.OPEN_APP, ExtractedEntities(application="downloads", target_entity="downloads"), "youtube"),
            "open downloads": (UniversalIntent.OPEN_APP, ExtractedEntities(application="downloads", target_entity="downloads"), "youtube"),
            "file explorer kholo": (UniversalIntent.OPEN_APP, ExtractedEntities(application="explorer", target_entity="explorer"), "system"),
            "open file explorer": (UniversalIntent.OPEN_APP, ExtractedEntities(application="explorer", target_entity="explorer"), "system"),
        }

        for check_cand in [clean_raw, clean_norm, clean_trans]:
            if check_cand in EXACT_MAP:
                exact_intent, exact_ent, exact_app = EXACT_MAP[check_cand]
                return SemanticParseResult(
                    raw_transcript=raw_transcript,
                    normalized_transcript=normalized,
                    detected_language=detected_lang or language,
                    primary_intent=exact_intent,
                    confidence=1.0,
                    entities=exact_ent,
                    target_application=exact_app,
                )

        # 3. Query Current Desktop State (Active Application & Window Context)
        active_app = app_state_manager.get_active_app()

        # 4. Extract Entities & Parameters
        entities = EntityResolver.resolve_entities(normalized, active_app=active_app)

        # 4. Score Candidate Semantic Intents
        candidates = cls._score_candidate_intents(normalized, entities, active_app)

        if not candidates:
            # Fallback to Conversational Chat or Unknown
            primary_intent = UniversalIntent.CONVERSATIONAL_CHAT
            confidence = 0.50
        else:
            primary_intent = candidates[0].intent
            confidence = candidates[0].confidence

        # 5. Disambiguation using Context
        primary_intent = cls._disambiguate_intent(primary_intent, entities, active_app)

        # 6. Infer Target Application Domain
        target_app = entities.application or cls._infer_target_app(primary_intent, active_app)

        return SemanticParseResult(
            raw_transcript=raw_transcript,
            normalized_transcript=normalized,
            detected_language=language,
            primary_intent=primary_intent,
            confidence=confidence,
            entities=entities,
            candidate_intents=candidates,
            target_application=target_app,
            requires_clarification=False,
            clarification_prompt=None,
        )

    @classmethod
    def _score_candidate_intents(
        cls,
        text: str,
        entities: ExtractedEntities,
        active_app: Optional[str],
    ) -> List[CandidateInterpretation]:
        """Score each universal intent against the normalized input."""
        scored: List[CandidateInterpretation] = []

        for intent, patterns in cls.INTENT_SEMANTIC_PATTERNS.items():
            max_score = 0.0
            matched_pat = ""

            for pat in patterns:
                if re.search(pat, text, flags=re.IGNORECASE):
                    # Specific media/action intents get a higher base score
                    if intent in [
                        UniversalIntent.THEATER_MODE, UniversalIntent.MINIPLAYER,
                        UniversalIntent.FULLSCREEN, UniversalIntent.CLEAN_JUNK,
                        UniversalIntent.RESUME, UniversalIntent.PAUSE,
                        UniversalIntent.SEEK_TIMESTAMP, UniversalIntent.SEEK_FORWARD,
                        UniversalIntent.SEEK_BACKWARD, UniversalIntent.NEXT_SHORT,
                        UniversalIntent.PREV_SHORT
                    ]:
                        score = 0.88
                    elif intent == UniversalIntent.OPEN_APP and not entities.application:
                        score = 0.60
                    else:
                        score = 0.80

                    # Boost if relevant entities exist
                    if intent in [UniversalIntent.CALL_CONTACT, UniversalIntent.VIDEO_CALL] and entities.contact:
                        score += 0.18
                    elif intent == UniversalIntent.OPEN_APP and entities.application:
                        score += 0.25
                    elif intent in [UniversalIntent.SEEK_FORWARD, UniversalIntent.SEEK_BACKWARD] and entities.time_duration_sec:
                        score += 0.15
                    elif intent == UniversalIntent.SEEK_TIMESTAMP and (entities.time_str or entities.time_duration_sec):
                        score += 0.20
                    elif intent == UniversalIntent.SELECT and entities.ordinal_index is not None:
                        score += 0.18
                    elif intent in [UniversalIntent.SCROLL_DOWN, UniversalIntent.SCROLL_UP] and entities.direction:
                        score += 0.15

                    if score > max_score:
                        max_score = score
                        matched_pat = pat

            if max_score > 0.0:
                scored.append(CandidateInterpretation(
                    intent=intent,
                    confidence=min(1.0, max_score),
                    application=entities.application or active_app,
                    rationale=f"Matched semantic pattern '{matched_pat}'",
                ))

        # Sort by confidence descending
        scored.sort(key=lambda x: x.confidence, reverse=True)
        return scored

    @classmethod
    def _disambiguate_intent(
        cls,
        intent: UniversalIntent,
        entities: ExtractedEntities,
        active_app: Optional[str],
    ) -> UniversalIntent:
        """Disambiguate polysemous words using UI & app context."""
        # If user explicitly asked to seek timestamp, preserve SEEK_TIMESTAMP
        if intent == UniversalIntent.SEEK_TIMESTAMP:
            return UniversalIntent.SEEK_TIMESTAMP

        # If user said "chalao" / "lagao" with an application entity ("YouTube chalao")
        if intent == UniversalIntent.PLAY and entities.application:
            return UniversalIntent.OPEN_APP

        # If user asked for next video/media ("agla video chalao" / "next video")
        if re.search(r"\b(?:next\s+video|agla\s+video|agli\s+video|agla\s+gaana|next\s+song)\b", entities.query or "", re.IGNORECASE):
            return UniversalIntent.NEXT_MEDIA

        # If user specified ordinal selection or sidebar video ("second wala chalao" / "right side wali video")
        if (entities.ordinal_index is not None or entities.position_relative == "sidebar") and not entities.time_str and intent not in [UniversalIntent.COMMENTS_VIEW, UniversalIntent.COMMENTS_HIDE, UniversalIntent.NEXT_SHORT, UniversalIntent.PREV_SHORT]:
            return UniversalIntent.SELECT

        # If user said "search X" without app, and active app is YouTube/Chrome
        if intent == UniversalIntent.SEARCH and not entities.application and active_app:
            entities.application = active_app

        return intent

    @classmethod
    def _infer_target_app(cls, intent: UniversalIntent, active_app: Optional[str]) -> Optional[str]:
        """Infer target application from intent domain when not explicitly stated."""
        if intent in [
            UniversalIntent.CALL_CONTACT, UniversalIntent.VIDEO_CALL,
            UniversalIntent.END_CALL, UniversalIntent.MUTE_CALL,
            UniversalIntent.STATUS_VIEW, UniversalIntent.DELETE_MESSAGE
        ]:
            return "whatsapp"

        if intent in [
            UniversalIntent.LIKE, UniversalIntent.DISLIKE,
            UniversalIntent.SUBSCRIBE, UniversalIntent.THEATER_MODE,
            UniversalIntent.COMMENTS_VIEW, UniversalIntent.COMMENTS_HIDE
        ]:
            return "youtube"

        return active_app

    @classmethod
    def _split_multi_intents(cls, raw: str, normalized: str) -> List[SemanticParseResult]:
        """Split multi-action compound sentences joined by 'aur', 'and', 'ke baad', 'phir'."""
        split_patterns = [r"\s+(?:aur|and|ke\s+baad|phir|then)\s+"]
        parts = [normalized]
        for sp in split_patterns:
            new_parts = []
            for p in parts:
                chunks = re.split(sp, p, flags=re.IGNORECASE)
                new_parts.extend([c.strip() for c in chunks if c.strip()])
            parts = new_parts

        if len(parts) > 1:
            results = []
            for part in parts:
                entities = EntityResolver.resolve_entities(part)
                candidates = cls._generate_candidate_interpretations(part, entities, None)
                intent = candidates[0].intent if candidates else UniversalIntent.OPEN_APP
                conf = candidates[0].confidence if candidates else 0.75
                results.append(SemanticParseResult(
                    raw_transcript=part,
                    normalized_transcript=part,
                    detected_language=LanguageNormalizer._detect_language(part),
                    primary_intent=intent,
                    confidence=conf,
                    entities=entities,
                    target_application=entities.application,
                ))
            return results

        return []

    @classmethod
    def _get_current_active_application(cls) -> Optional[str]:
        """Inspect foreground window to provide real-time UI context."""
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                title = win32gui.GetWindowText(hwnd).lower()
                cls_name = win32gui.GetClassName(hwnd).lower()
                if "youtube" in title:
                    return "youtube"
                if "whatsapp" in title or "whatsapp" in cls_name:
                    return "whatsapp"
                if "chrome" in title or "chrome" in cls_name:
                    return "chrome"
                if "visual studio code" in title or "code" in title:
                    return "vscode"
                if "spotify" in title:
                    return "spotify"
        except Exception:
            pass
        return None
