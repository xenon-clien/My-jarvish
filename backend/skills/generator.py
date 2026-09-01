"""App Skill Generator for JARVIS AI.

Persists discovered application capability maps into local skill directories (skills/{app}/skill.json)
so skills load instantly on subsequent startups without re-scanning overhead.
"""
import json
import os
from typing import Optional

from backend.core.logger import get_logger
from backend.skills.models import AppCapabilityMap

logger = get_logger("AppSkillGenerator")

SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "skills")


class AppSkillGenerator:
    """Saves and loads JSON capability definitions in the skills/ directory."""

    def __init__(self, base_dir: str = SKILLS_DIR):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def save_skill(self, capability_map: AppCapabilityMap) -> str:
        """Save an AppCapabilityMap to skills/{app_name}/skill.json."""
        app_name = capability_map.application.lower().strip()
        app_dir = os.path.join(self.base_dir, app_name)
        os.makedirs(app_dir, exist_ok=True)

        file_path = os.path.join(app_dir, "skill.json")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(capability_map.model_dump(), f, indent=2, ensure_ascii=False)
            logger.info(f"Saved skill definition for '{app_name}' at {file_path}")
            return file_path
        except Exception as exc:
            logger.error(f"Failed to save skill for '{app_name}': {exc}")
            raise

    def load_skill(self, app_name: str) -> Optional[AppCapabilityMap]:
        """Load an AppCapabilityMap from skills/{app_name}/skill.json if it exists."""
        clean_name = app_name.lower().strip()
        file_path = os.path.join(self.base_dir, clean_name, "skill.json")
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AppCapabilityMap(**data)
        except Exception as exc:
            logger.warning(f"Error loading skill file {file_path}: {exc}")
            return None


# Global generator instance
skill_generator = AppSkillGenerator()
