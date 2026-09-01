"""JARVIS 3.0 - Filesystem Adapter.

Provides sandboxed, secure file operations guarding against directory traversal attacks.
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from adapters.base_adapter import BaseAdapter
from core.config import get_settings
from core.logger import get_logger
from core.models import PermissionLevel, PermissionType, ToolCategory, ToolExecutionResult
from core.tool_contract import FunctionalTool
from core.tool_registry import ToolRegistry, default_registry

logger = get_logger("FilesystemAdapter")


class SearchFilesArgs(BaseModel):
    query: str = Field(..., description="File name pattern or extension to search.")
    directory: Optional[str] = Field(default=None, description="Starting directory to search in.")


class ReadFileArgs(BaseModel):
    file_path: str = Field(..., description="Path to the file to inspect.")


class FilesystemAdapter(BaseAdapter):
    """Encapsulates sandboxed file operations."""

    def __init__(self):
        super().__init__(name="filesystem", category=ToolCategory.FILE)
        self.settings = get_settings()

    def register_tools(self, registry: Optional[ToolRegistry] = None) -> None:
        reg = registry or default_registry

        # 1. files.search
        reg.register(FunctionalTool(
            name="files.search",
            description="Search for files by name in allowed user directories.",
            category=ToolCategory.FILE,
            func=self.search_files,
            permission_level=PermissionLevel.LEVEL_0_SAFE,
            required_permissions=[PermissionType.FILESYSTEM],
            parameters_schema=SearchFilesArgs,
        ))

        # 2. files.read
        reg.register(FunctionalTool(
            name="files.read",
            description="Read text preview of a file in allowed user folders.",
            category=ToolCategory.FILE,
            func=self.read_file,
            permission_level=PermissionLevel.LEVEL_0_SAFE,
            required_permissions=[PermissionType.FILESYSTEM],
            parameters_schema=ReadFileArgs,
        ))

        self.is_initialized = True
        logger.info("Registered FilesystemAdapter tools: files.search, files.read")

    def get_application_state(self) -> Dict[str, Any]:
        return {"allowed_directories": [str(d) for d in self.settings.ALLOWED_DIRECTORIES]}

    def _is_path_allowed(self, target_path: str) -> bool:
        """Check if target path resides within allowed sandboxed folders."""
        try:
            resolved = Path(target_path).resolve()
            allowed = [Path(d).resolve() for d in self.settings.ALLOWED_DIRECTORIES]
            return any(resolved == a or a in resolved.parents for a in allowed)
        except Exception:
            return False

    async def search_files(self, query: str, directory: Optional[str] = None) -> ToolExecutionResult:
        search_root = Path(directory).resolve() if directory else Path.home() / "Downloads"
        if not self._is_path_allowed(str(search_root)):
            search_root = Path.home() / "Downloads"

        matches = []
        clean_q = query.lower().strip()
        try:
            for root, _, files in os.walk(search_root):
                for f in files:
                    if clean_q in f.lower():
                        full_p = os.path.join(root, f)
                        matches.append({"name": f, "path": full_p})
                        if len(matches) >= 10:
                            break
                if len(matches) >= 10:
                    break

            if not matches:
                return ToolExecutionResult(
                    success=True,
                    data={"files": []},
                    message=f"Boss, '{query}' naam ki koi file nahi mili.",
                )

            names = ", ".join([m["name"] for m in matches[:5]])
            return ToolExecutionResult(
                success=True,
                data={"files": matches},
                message=f"Boss, {len(matches)} files mili hain: {names}.",
            )
        except Exception as exc:
            return ToolExecutionResult(success=False, error=str(exc))

    async def read_file(self, file_path: str) -> ToolExecutionResult:
        if not self._is_path_allowed(file_path):
            return ToolExecutionResult(
                success=False,
                error="Access denied: Path is outside allowed directories.",
            )
        try:
            p = Path(file_path)
            if not p.exists():
                return ToolExecutionResult(success=False, error="File not found.")
            content = p.read_text(encoding="utf-8", errors="replace")[:1000]
            return ToolExecutionResult(
                success=True,
                data={"content": content, "path": str(p)},
                message=f"Content of '{p.name}':\n{content}",
            )
        except Exception as exc:
            return ToolExecutionResult(success=False, error=str(exc))


filesystem_adapter = FilesystemAdapter()
