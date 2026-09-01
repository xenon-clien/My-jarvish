"""Entity Resolver for discovering apps, contacts, ordinals, pronouns, and parameters."""
import re
from typing import Optional, Tuple
from backend.nlu.models import ExtractedEntities
from backend.skills.context import app_state_manager


class EntityResolver:
    """Extracts structured entities, resolves pronouns, and maps fuzzy aliases."""

    # Fuzzy Application Aliases
    APP_ALIASES = {
        "youtube": ["youtube", "yt", "you tube", "video app", "videos app", "video wala app"],
        "chrome": ["chrome", "google chrome", "browser", "google browser", "internet browser", "internet wala browser"],
        "whatsapp": ["whatsapp", "wa", "whats app", "chat app", "message wala app", "messaging app"],
        "vscode": ["vscode", "vs code", "visual studio code", "code editor", "coding app"],
        "file-explorer": ["explorer", "file explorer", "files", "folder", "my computer", "this pc", "files app"],
        "spotify": ["spotify", "spotifi", "spoti"],
        "edge": ["edge", "microsoft edge", "ms edge"],
        "settings": ["settings", "system settings", "windows settings", "bluetooth settings", "wifi settings"],
        "notepad": ["notepad", "text editor", "notes", "नोटपैड"],
        "calculator": ["calculator", "calc", "कैलकुलेटर"],
        "cmd": ["cmd", "command prompt", "terminal"],
        "paint": ["paint", "ms paint"],
        "vlc": ["vlc", "vlc media player"],
    }

    # Known Address Book Contacts (in-memory fast cache + db fallback)
    KNOWN_CONTACTS = {
        "harsh": "8054840494",
        "shivam": "9501445740",
    }

    # Ordinal Mapping (Hindi + English)
    ORDINALS = {
        "first": 1, "1st": 1, "pehla": 1, "pehli": 1, "1": 1,
        "second": 2, "2nd": 2, "dusra": 2, "doosra": 2, "dusri": 2, "2": 2,
        "third": 3, "3rd": 3, "teesra": 3, "tisra": 3, "teesri": 3, "3": 3,
        "fourth": 4, "4th": 4, "chautha": 4, "chauthi": 4, "4": 4,
        "fifth": 5, "5th": 5, "panchwa": 5, "panchvi": 5, "5": 5,
        "last": -1, "aakhri": -1, "last wala": -1,
    }

    # Pronoun Tokens
    PRONOUNS = ["it", "this", "that", "isko", "usko", "ye", "woh", "ye wala", "woh wala", "isme", "usme"]

    @classmethod
    def resolve_entities(cls, text: str, active_app: Optional[str] = None) -> ExtractedEntities:
        """Extract all structured entities from normalized text."""
        entities = ExtractedEntities()
        lower = text.lower().strip()

        # 1. Resolve Application
        entities.application = cls._extract_application(lower)

        # 2. Resolve Contact Name and Phone Number
        contact_name, phone = cls._extract_contact(lower)
        if contact_name:
            entities.contact = contact_name
            entities.phone_number = phone

        # 3. Resolve Ordinal Index (duration-aware)
        entities.ordinal_index = cls._extract_ordinal(lower)

        # 4. Resolve Direction / Relative Position
        entities.direction = cls._extract_direction(lower)
        entities.position_relative = cls._extract_position(lower)

        # 5. Resolve Time Duration and Exact Timestamp
        sec_val, t_str = cls._extract_duration_and_timestamp(lower)
        entities.time_duration_sec = sec_val
        entities.time_str = t_str

        # 6. Resolve Pronoun References (e.g. "isko", "usko", "it", "this")
        entities.pronoun_reference = cls._extract_pronoun(lower)

        # Safe fallback target resolution
        if entities.pronoun_reference:
            get_target_fn = getattr(app_state_manager, "get_last_target", None)
            last_target = get_target_fn() if callable(get_target_fn) else None
            if last_target and not entities.query and not entities.contact:
                entities.raw_parameters["resolved_pronoun_target"] = last_target

        # 7. Extract File Type / Extension
        entities.file_type = cls._extract_file_type(lower)

        # 8. Extract Message Body / Query
        entities.message_body = cls._extract_message_body(text)
        entities.query = cls._extract_search_query(text, entities.application)

        return entities

    @classmethod
    def _extract_duration_and_timestamp(cls, text: str) -> Tuple[Optional[int], Optional[str]]:
        """Extract compound seconds/minutes duration and formatted YouTube timestamp."""
        # 1. Compound: "5 minute 30 second" / "5 min 30 sec" / "5 minute tees second"
        m_compound = re.search(r"(\d+)\s*(?:minute|minutes|min|m)\s*(?:and\s*)?(\d+)\s*(?:seconds|second|sec|s)?\b", text)
        if m_compound:
            mins = int(m_compound.group(1))
            secs = int(m_compound.group(2)) if m_compound.group(2) else 0
            total_sec = mins * 60 + secs
            t_str = f"{mins}m{secs}s" if secs else f"{mins}m"
            return total_sec, t_str

        # 2. Colon notation: "5:30" or "1:15:20"
        m_colon = re.search(r"\b(\d+):(\d+)(?::(\d+))?\b", text)
        if m_colon:
            if m_colon.group(3):
                hrs = int(m_colon.group(1))
                mins = int(m_colon.group(2))
                secs = int(m_colon.group(3))
                return hrs * 3600 + mins * 60 + secs, f"{hrs}h{mins}m{secs}s"
            else:
                mins = int(m_colon.group(1))
                secs = int(m_colon.group(2))
                return mins * 60 + secs, f"{mins}m{secs}s"

        # 3. Only Minutes: "10 minute" / "12 min"
        m_min = re.search(r"(\d+)\s*(?:minute|minutes|min|m)\b", text)
        if m_min:
            mins = int(m_min.group(1))
            return mins * 60, f"{mins}m"

        # 4. Only Seconds: "45 second" / "10 sec"
        m_sec = re.search(r"(\d+)\s*(?:seconds|second|sec|s)\b", text)
        if m_sec:
            secs = int(m_sec.group(1))
            return secs, f"{secs}s"

        return None, None

    @classmethod
    def _extract_application(cls, text: str) -> Optional[str]:
        """Fuzzy match application name or alias."""
        for app_id, aliases in cls.APP_ALIASES.items():
            for alias in aliases:
                if re.search(rf"\b{re.escape(alias)}\b", text):
                    return app_id
        return None

    @classmethod
    def _extract_contact(cls, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract contact name and phone number with typo and Hindi particle resilience."""
        # 1. Explicit phone number in string
        num_match = re.search(r"(\+?91[\s-]?)?([6-9]\d{9})", text)
        phone = num_match.group(2) if num_match else None

        # 2. Match known contacts
        for name, num in cls.KNOWN_CONTACTS.items():
            if re.search(rf"\b{name}\b", text):
                return name.capitalize(), phone or num

        # 3. Generic "X ko" / "X se" pattern for communication intents
        contact_match = re.search(r"([a-zA-Z]+?)\s+(?:ko|se|ka|ki|ke|lka)\s+(?:call|message|phone|msg)", text)
        if contact_match:
            c_name = contact_match.group(1).strip().capitalize()
            if c_name.lower() not in ["whatsapp", "chrome", "youtube", "browser", "video"]:
                return c_name, phone

        return None, phone

    @classmethod
    def _extract_ordinal(cls, text: str) -> Optional[int]:
        """Extract numeric or word ordinal index, ignoring duration units and Hindi verb particles."""
        # 1. Strip duration units
        clean = re.sub(r"\b\d+\s*(?:seconds?|secs?|minutes?|mins?|hours?|hrs?)\b", " ", text)
        # 2. Strip Hindi imperative verb endings with "do" (e.g. "chala do", "rok do", "kar do", "laga do")
        clean = re.sub(r"\b(?:chala|rok|kar|laga|badha|bana|de|le|hata|khol)\s+do\b", " ", clean)

        matches = []
        for word, idx in cls.ORDINALS.items():
            for m in re.finditer(rf"\b{re.escape(word)}\b", clean):
                matches.append((m.start(), idx))
        if matches:
            matches.sort(key=lambda x: x[0])
            return matches[-1][1]
        return None

    @classmethod
    def _extract_direction(cls, text: str) -> Optional[str]:
        """Extract direction: up, down, left, right, next, prev."""
        if any(w in text for w in ["niche", "neeche", "down", "bottom", "scroll down"]):
            return "down"
        if any(w in text for w in ["upar", "up", "top", "scroll up"]):
            return "up"
        if any(w in text for w in ["right", "right side", "daye"]):
            return "right"
        if any(w in text for w in ["left", "left side", "baye"]):
            return "left"
        return None

    @classmethod
    def _extract_position(cls, text: str) -> Optional[str]:
        """Extract relative position like sidebar, header, comments."""
        if any(w in text for w in ["comments", "comment section"]):
            return "comments"
        if any(w in text for w in ["sidebar", "right side", "sugggestion", "recommendations"]):
            return "sidebar"
        return None

    @classmethod
    def _extract_pronoun(cls, text: str) -> Optional[str]:
        """Extract reference pronouns."""
        for p in cls.PRONOUNS:
            if re.search(rf"\b{re.escape(p)}\b", text):
                return p
        return None

    @classmethod
    def _extract_file_type(cls, text: str) -> Optional[str]:
        """Extract file format extensions or types."""
        m = re.search(r"\b(pdf|docx|doc|xlsx|txt|png|jpg|jpeg|mp4|mp3|zip|py|js|json)\b", text)
        if m:
            return m.group(1)
        return None

    @classmethod
    def _extract_message_body(cls, text: str) -> Optional[str]:
        """Extract body text for a message command without misidentifying contact name as message."""
        m = re.search(r"(?:message|msg|likho|bolo)\s*(?:karo|bhejo)?\s*[:,\-]?\s+(.+)$", text, flags=re.IGNORECASE)
        if m:
            body = m.group(1).strip()
            clean_test = re.sub(r"\b(ko|se|ka|ki|ke|lka|whatsapp|par|pe)\b", "", body, flags=re.IGNORECASE).strip()
            if clean_test.lower() in cls.KNOWN_CONTACTS or len(clean_test.split()) <= 1 and clean_test.lower() in ["harsh", "shivam"]:
                return None

            body = re.sub(r"^(?:harsh|shivam|[a-zA-Z]+?)\s+(?:ko|se|lka)?\s*[:,\-]?\s*", "", body, flags=re.IGNORECASE).strip()
            body = re.sub(r"\b(bhej|bhejo|kar do|karo)\b$", "", body, flags=re.IGNORECASE).strip()
            if body and body.lower() not in ["harsh", "shivam"]:
                return body
        return None

    @classmethod
    def _extract_search_query(cls, text: str, app: Optional[str]) -> Optional[str]:
        """Extract search query from text."""
        # e.g. "Python search karo", "Search machine learning on youtube"
        cleaned = re.sub(r"\b(search|dhoondo|find|lookup|dhundho|pata\s+karo|karo|bhai|yaar|on\s+youtube|in\s+youtube|on\s+google|in\s+google|youtube|google)\b", "", text, flags=re.IGNORECASE).strip()
        return cleaned if cleaned else None
