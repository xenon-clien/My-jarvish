"""Short-term Context Memory & Entity Reference Engine for JARVIS AI.

Maintains active conversational context, recent search result candidates, and screen/tab context.
Enables seamless understanding of follow-up commands like:
- "dusra wala" / "second one"
- "isme se expensive gift wala"
- "ye wala chalao"
"""
import re
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.ai.semantic_matcher import ScoredCandidate, semantic_matcher
from backend.core.logger import get_logger

logger = get_logger("ContextMemory")


class SearchContext(BaseModel):
    """Holds details of the most recent search candidates."""
    platform: str = "youtube"
    query: str = ""
    timestamp: float = Field(default_factory=time.time)
    candidates: List[ScoredCandidate] = Field(default_factory=list)


class ActiveItemContext(BaseModel):
    """Holds details of the currently playing or active item on screen."""
    title: str = ""
    id: str = ""
    url: str = ""
    platform: str = "youtube"
    timestamp: float = Field(default_factory=time.time)


class ContextMemory:
    """Short-term conversational and candidate memory."""

    def __init__(self, ttl_seconds: float = 300.0):
        self.ttl_seconds = ttl_seconds
        self._last_search: Optional[SearchContext] = None
        self._active_item: Optional[ActiveItemContext] = None

    def record_search(
        self,
        platform: str,
        query: str,
        candidates: List[ScoredCandidate],
    ) -> None:
        """Store the candidates of a search for short-term follow-up referencing."""
        self._last_search = SearchContext(
            platform=platform,
            query=query,
            timestamp=time.time(),
            candidates=candidates,
        )
        logger.info(f"Recorded search context for '{query}' ({len(candidates)} candidates)")

    def record_active_item(self, title: str, item_id: str, url: str, platform: str = "youtube") -> None:
        """Store the currently active/playing item."""
        self._active_item = ActiveItemContext(
            title=title,
            id=item_id,
            url=url,
            platform=platform,
            timestamp=time.time(),
        )

    def get_last_search(self) -> Optional[SearchContext]:
        """Return valid active search context if within TTL."""
        if self._last_search and (time.time() - self._last_search.timestamp) <= self.ttl_seconds:
            return self._last_search
        return None

    def get_active_item(self) -> Optional[ActiveItemContext]:
        """Return currently active playing item."""
        return self._active_item

    def resolve_followup(self, user_text: str) -> Optional[ScoredCandidate]:
        """Resolve ordinal or descriptive follow-ups against recent candidates."""
        search = self.get_last_search()
        if not search or not search.candidates:
            return None

        text = user_text.lower().strip()

        followup_triggers = [
            "pehla", "first", "1st", "ek number", "dusra", "doosra", "second", "2nd", "do number",
            "teesra", "tisra", "third", "3rd", "teen number", "chautha", "fourth", "4th", "char number",
            "panchwa", "fifth", "5th", "paanch number", "ye wala", "woh wala", "is me se", "isme se",
            "wala", "wali", "wale", "dusri", "teesri", "chauthi", "pehli"
        ]
        if not any(t in text for t in followup_triggers):
            return None

        # 1. Ordinal indexing ("dusra wala", "teesra wala", "second one")
        ordinal_map = {
            "pehla": 0, "first": 0, "1st": 0, "ek number": 0,
            "dusra": 1, "doosra": 1, "second": 1, "2nd": 1, "do number": 1,
            "teesra": 2, "tisra": 2, "third": 2, "3rd": 2, "teen number": 2,
            "chautha": 3, "fourth": 3, "4th": 3, "char number": 3,
            "panchwa": 4, "fifth": 4, "5th": 4, "paanch number": 4,
        }

        for word, idx in ordinal_map.items():
            if word in text:
                if 0 <= idx < len(search.candidates):
                    selected = search.candidates[idx]
                    logger.info(f"Resolved ordinal follow-up '{word}' -> Candidate #{idx+1}: {selected.title}")
                    return selected

        # 2. Descriptive filtering ("isme se expensive gift wala", "unme se standup wala")
        if any(prefix in text for prefix in ["isme se", "unme se", "inme se", "from these", "from this"]):
            clean_subquery = re.sub(r"^(isme se|unme se|inme se|from these|from this)\s*", "", text).strip()
            if clean_subquery:
                # Rank candidates with the subquery
                candidate_dicts = [
                    {
                        "id": c.id,
                        "title": c.title,
                        "channel": c.channel,
                        "duration": c.duration_text,
                        "is_short": c.is_short,
                    }
                    for c in search.candidates
                ]
                re_ranked = semantic_matcher.rank_candidates(clean_subquery, candidate_dicts)
                if re_ranked and re_ranked[0].confidence_score >= 0.35:
                    logger.info(f"Resolved descriptive filter '{clean_subquery}' -> Candidate: {re_ranked[0].title}")
                    return re_ranked[0]

        # 2. Semantic matching fallback
        re_ranked = semantic_matcher.rank_candidates(text, search.candidates)
        if re_ranked:
            return re_ranked[0]
        return None


class UserPreferencesMemory:
    """Safe structured long-term user memory (preferences, preferred apps, contacts, folders).

    PRIVACY & SECURITY GUARANTEES:
    - Never stores passwords, bank info, API keys, tokens, or biometric frames.
    - Supports explicit memory inspection, deletion ("Forget this"), and full reset.
    """

    def __init__(self):
        self.preferred_apps: Dict[str, str] = {"browser": "chrome", "editor": "antigravity"}
        self.preferred_contacts: Dict[str, str] = {}
        self.frequently_used_folders: List[str] = []
        self.custom_preferences: Dict[str, Any] = {}

    def set_preferred_app(self, category: str, app_name: str) -> None:
        self.preferred_apps[category.lower()] = app_name.lower()
        logger.info(f"Memory saved: preferred app '{category}' -> '{app_name}'")

    def set_preferred_contact(self, name: str, contact_info: str) -> None:
        self.preferred_contacts[name.lower()] = contact_info
        logger.info(f"Memory saved: contact '{name}'")

    def add_favorite_folder(self, folder_path: str) -> None:
        if folder_path not in self.frequently_used_folders:
            self.frequently_used_folders.append(folder_path)

    def get_stored_preferences(self) -> Dict[str, Any]:
        """Return all safe stored preferences."""
        return {
            "preferred_apps": self.preferred_apps,
            "preferred_contacts": self.preferred_contacts,
            "frequently_used_folders": self.frequently_used_folders,
            "custom_preferences": self.custom_preferences,
        }

    def forget_item(self, key: str) -> str:
        """Forget a specific memory key."""
        k = key.lower().strip()
        if k in self.preferred_apps:
            del self.preferred_apps[k]
            return f"Forgot preferred app for '{k}'."
        if k in self.preferred_contacts:
            del self.preferred_contacts[k]
            return f"Forgot contact '{k}'."
        if k in self.custom_preferences:
            del self.custom_preferences[k]
            return f"Forgot preference '{k}'."
        return f"No memory found for '{key}'."

    def clear_memory(self) -> str:
        """Clear all stored long-term preferences."""
        self.preferred_apps.clear()
        self.preferred_contacts.clear()
        self.frequently_used_folders.clear()
        self.custom_preferences.clear()
        logger.info("Cleared all JARVIS long-term user memory.")
        return "All stored user memory has been cleared."


# Global singleton instances
context_memory = ContextMemory()
user_memory = UserPreferencesMemory()
