"""JARVIS 3.0 - Chrome & System Download Manager.

Tracks ongoing browser downloads (.crdownload / .tmp), locates completed downloads,
and provides status reports on recently saved files.
"""
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from core.logger import get_logger
from core.models import ToolExecutionResult

logger = get_logger("DownloadManager")


class DownloadItem(BaseModel):
    filename: str
    file_path: str
    size_bytes: int
    size_mb: float
    is_in_progress: bool
    modified_time: float


class DownloadManager:
    """Monitors the user's Downloads directory."""

    def __init__(self):
        self.downloads_dir = Path.home() / "Downloads"

    def get_downloads_directory(self) -> Path:
        return self.downloads_dir

    def list_recent_downloads(self, limit: int = 10) -> List[DownloadItem]:
        """Scan Downloads folder and return recent downloads sorted newest first."""
        if not self.downloads_dir.exists():
            return []

        items = []
        try:
            for entry in os.scandir(self.downloads_dir):
                if entry.is_file():
                    stat = entry.stat()
                    name = entry.name
                    in_progress = any(name.endswith(ext) for ext in [".crdownload", ".tmp", ".part", ".partial"])
                    clean_name = name
                    for ext in [".crdownload", ".tmp", ".part", ".partial"]:
                        if clean_name.endswith(ext):
                            clean_name = clean_name[:-len(ext)]

                    size_mb = round(stat.st_size / (1024 * 1024), 2)
                    items.append(DownloadItem(
                        filename=clean_name,
                        file_path=entry.path,
                        size_bytes=stat.st_size,
                        size_mb=size_mb,
                        is_in_progress=in_progress,
                        modified_time=stat.st_mtime,
                    ))
        except Exception as exc:
            logger.warning(f"Error scanning downloads directory: {exc}")

        # Sort by modification time descending
        items.sort(key=lambda x: x.modified_time, reverse=True)
        return items[:limit]

    def get_last_downloaded_file(self) -> Optional[DownloadItem]:
        """Return the most recently downloaded completed file."""
        downloads = self.list_recent_downloads(limit=10)
        completed = [d for d in downloads if not d.is_in_progress]
        return completed[0] if completed else None

    def get_active_downloads(self) -> List[DownloadItem]:
        """Return list of files currently being downloaded."""
        downloads = self.list_recent_downloads(limit=10)
        return [d for d in downloads if d.is_in_progress]

    def open_downloads_folder(self) -> ToolExecutionResult:
        """Open Windows Explorer at Downloads folder."""
        try:
            subprocess.Popen(f'explorer "{self.downloads_dir}"', shell=True)
            return ToolExecutionResult(
                success=True,
                message="Ji Boss, Downloads folder open kar diya.",
            )
        except Exception as exc:
            return ToolExecutionResult(
                success=False,
                error=f"Could not open Downloads folder: {exc}",
            )


download_manager = DownloadManager()
