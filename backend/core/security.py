"""Security and sandboxing enforcement for JARVIS AI.

Validates filesystem paths, checks allowed directory boundaries,
and prevents directory traversal attacks.
"""
from pathlib import Path
from typing import List, Optional, Union

from backend.core.config import Settings, get_settings


class SecurityManager:
    """Provides security boundary checking and validation."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    def get_allowed_directories(self) -> List[Path]:
        """Return resolved Path objects for all configured allowed directories."""
        dirs = []
        raw_dirs = self.settings.ALLOWED_DIRECTORIES
        if isinstance(raw_dirs, list):
            for d in raw_dirs:
                try:
                    dirs.append(Path(d).resolve())
                except Exception:
                    continue
        return dirs

    def is_path_allowed(self, target_path: Union[str, Path]) -> bool:
        """Check if target_path is within one of the allowed directories.

        Guards against directory traversal attacks like '../../Windows/System32'.
        """
        try:
            resolved_target = Path(target_path).resolve()
        except Exception:
            return False

        allowed_dirs = self.get_allowed_directories()
        if not allowed_dirs:
            return False

        for allowed_dir in allowed_dirs:
            try:
                # If resolved_target is allowed_dir or a descendant of allowed_dir
                if resolved_target == allowed_dir or allowed_dir in resolved_target.parents:
                    return True
            except Exception:
                continue

        return False

    def ensure_path_allowed(self, target_path: Union[str, Path]) -> Path:
        """Resolve the path and raise PermissionError if it lies outside allowed boundaries."""
        resolved = Path(target_path).resolve()
        if not self.is_path_allowed(resolved):
            raise PermissionError(
                f"Access denied: Path '{target_path}' is outside configured allowed directories."
            )
        return resolved

    def validate_safe_filename(self, filename: str) -> bool:
        """Verify that a filename does not contain illegal characters or path separators."""
        if not filename or not isinstance(filename, str):
            return False
        if "/" in filename or "\\" in filename or ".." in filename:
            return False
        invalid_chars = set('<>:"/\\|?*')
        return not any(char in invalid_chars for char in filename)


# Global default instance
security_manager = SecurityManager()
