"""
Personal Profile & Memory Engine for Shivam & JARVIS AI.

Maintains comprehensive knowledge of Shivam's preferences, schedule, hobbies,
favorite movies, games, entertainment, and personal companion dynamics.
"""
import json
import os
from typing import Any, Dict, Optional

# Shivam's Complete Profile & Memory
SHIVAM_PROFILE: Dict[str, Any] = {
    "name": "Shivam",
    "location": "Punjab, India",
    "role": "Boss / Developer / Creator",
    "personality": "Tech-savvy, ambitious, smart, creative, loves gaming and AI innovations",
    
    "hobbies": [
        "Coding & creating AI projects",
        "Gaming (PC & Mobile)",
        "Watching YouTube videos & comedy standups",
        "Exploring new technologies and laptops/gadgets",
        "Listening to energetic & relaxing music",
    ],
    
    "favorite_games": [
        "GTA V (Grand Theft Auto 5)",
        "BGMI / PUBG Mobile",
        "Roblox",
        "Minecraft",
        "Valorant / Free Fire",
    ],
    
    "favorite_creators": [
        "Techno Gamerz (Ujjwal)",
        "Samay Raina",
        "CarryMinati",
        "Aarush Bhola",
        "Elvish Yadav",
        "Total Gaming",
    ],
    
    "favorite_movies_and_shows": [
        "Iron Man / Marvel Cinematic Universe (MCU)",
        "Interstellar",
        "Inception",
        "Sci-Fi & Action Thrillers",
        "Taarak Mehta Ka Ooltah Chashmah",
    ],
    
    "daily_schedule": {
        "morning": "Wake up, check weather and system diagnostics, morning routine, review goals & tech news.",
        "afternoon": "Coding sessions, developing & testing AI features, productive work, quick gaming break.",
        "evening": "Entertainment time — watching YouTube (Techno Gamerz, Samay Raina), hanging out with friends, listening to music.",
        "night": "Reviewing day accomplishments, planning next goals, relaxing with favorite movies/shows, shutting down laptop with JARVIS.",
    },
    
    "jarvis_relationship": "JARVIS is Shivam's dedicated, highly intelligent, sweet, and caring personal female AI companion who manages his entire PC, automates tasks, tracks his schedule, and talks with him like a real best friend.",
}


class UserProfileManager:
    """Manages user profile, preferences, and long-term memory."""

    def __init__(self):
        self.profile = SHIVAM_PROFILE
        self._memory_file = os.path.expanduser("~/.jarvis_user_memory.json")
        self._load_memory()

    def _load_memory(self):
        if os.path.exists(self._memory_file):
            try:
                with open(self._memory_file, "r", encoding="utf-8") as f:
                    custom = json.load(f)
                    self.profile.update(custom)
            except Exception:
                pass

    def save_memory(self, key: str, value: Any):
        """Save a new preference or memory fact about Shivam."""
        self.profile[key] = value
        try:
            with open(self._memory_file, "w", encoding="utf-8") as f:
                json.dump(self.profile, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_profile_summary(self) -> str:
        """Format complete profile into rich prompt context for the AI."""
        p = self.profile
        return f"""
USER PROFILE & PERSONAL KNOWLEDGE (SHIVAM):
- Name: {p['name']} (Address him affectionately as Shivam or Boss)
- Location: {p['location']}
- Hobbies: {', '.join(p['hobbies'])}
- Favorite Games: {', '.join(p['favorite_games'])}
- Favorite Content Creators: {', '.join(p['favorite_creators'])}
- Favorite Movies & Shows: {', '.join(p['favorite_movies_and_shows'])}
- Daily Routine & Schedule:
  * Morning: {p['daily_schedule']['morning']}
  * Afternoon: {p['daily_schedule']['afternoon']}
  * Evening: {p['daily_schedule']['evening']}
  * Night: {p['daily_schedule']['night']}

You know everything about Shivam! Whenever he asks about his schedule, favorite movies, games, hobbies, or personal life, answer warmly, accurately, and enthusiastically just like someone who knows him deeply.
"""


user_profile_manager = UserProfileManager()
