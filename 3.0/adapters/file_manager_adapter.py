"""JARVIS 3.0 - Dedicated File Manager Application Adapter.

Handles file search, hidden files toggle, large file discovery, recent files,
folder management, and file inspection in sandboxed user directories.
"""
from datetime import datetime, timedelta
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from adapters.base_adapter import BaseAdapter
from core.config import get_settings
from core.logger import get_logger
from core.models import PermissionLevel, PermissionType, ToolCategory, ToolExecutionResult
from core.tool_contract import FunctionalTool
from core.tool_registry import ToolRegistry, default_registry

logger = get_logger("FileManager")

try:
    import winreg
    WINREG_AVAILABLE = True
except ImportError:
    WINREG_AVAILABLE = False


class FileQueryArgs(BaseModel):
    query: str = Field(..., description="File name pattern to search.")
    directory: Optional[str] = Field(default=None, description="Starting search directory.")


class FileExtensionArgs(BaseModel):
    extension: str = Field(..., description="File extension (e.g. 'pdf', 'png', 'mp4', 'docx').")
    directory: Optional[str] = Field(default=None, description="Starting directory.")


class LargeFileArgs(BaseModel):
    min_size_mb: float = Field(default=100.0, description="Minimum file size in megabytes.")
    directory: Optional[str] = Field(default=None, description="Directory to scan.")


class SinglePathArgs(BaseModel):
    path: str = Field(..., description="Path to file or folder.")


class CreateFolderArgs(BaseModel):
    folder_name: str = Field(..., description="Folder name or path to create.")
    directory: Optional[str] = Field(default=None, description="Parent directory.")


class FileManagerAdapter(BaseAdapter):
    """Encapsulates Windows File Explorer and filesystem operations."""

    def __init__(self):
        super().__init__(name="file_manager", category=ToolCategory.FILE)
        self.settings = get_settings()

    def register_tools(self, registry: Optional[ToolRegistry] = None) -> None:
        reg = registry or default_registry

        # 1. files.open
        reg.register(self._make_tool("files.open", "Open a file or folder in its default desktop application.", self.open_file_or_folder, parameters_schema=SinglePathArgs))

        # 2. files.search
        reg.register(self._make_tool("files.search", "Search for files by name in Downloads, Desktop, or Documents.", self.search_files, parameters_schema=FileQueryArgs))

        # 3. files.find_by_extension
        reg.register(self._make_tool("files.find_by_extension", "Find files by specific extension (e.g., pdf, jpg, docx, mp4).", self.find_by_extension, parameters_schema=FileExtensionArgs))

        # 4. files.find_large
        reg.register(self._make_tool("files.find_large", "Find large files taking up storage space.", self.find_large_files, parameters_schema=LargeFileArgs))

        # 5. files.find_recent
        reg.register(self._make_tool("files.find_recent", "Find files modified recently in the last 24-48 hours.", self.find_recent_files))

        # 6. files.show_hidden
        reg.register(self._make_tool("files.show_hidden", "Configure Windows Explorer to show hidden files and folders.", self.show_hidden_files))

        # 7. files.hide_hidden
        reg.register(self._make_tool("files.hide_hidden", "Configure Windows Explorer to hide hidden files.", self.hide_hidden_files))

        # 8. files.create_folder
        reg.register(self._make_tool("files.create_folder", "Create a new folder in user directory.", self.create_folder, parameters_schema=CreateFolderArgs))

        # 9. files.properties
        reg.register(self._make_tool("files.properties", "Inspect metadata, size, and modification date of a file.", self.get_file_properties, parameters_schema=SinglePathArgs))

        self.is_initialized = True
        logger.info("Registered FileManagerAdapter tools.")

    def _make_tool(self, name: str, desc: str, func: Any, parameters_schema: Optional[type] = None) -> FunctionalTool:
        return FunctionalTool(
            name=name,
            description=desc,
            category=ToolCategory.FILE,
            func=func,
            permission_level=PermissionLevel.LEVEL_0_SAFE,
            required_permissions=[PermissionType.FILESYSTEM],
            parameters_schema=parameters_schema,
        )

    def get_application_state(self) -> Dict[str, Any]:
        return {"allowed_roots": [str(d) for d in self.settings.ALLOWED_DIRECTORIES]}

    def _resolve_safe_directory(self, dir_hint: Optional[str] = None) -> Path:
        if dir_hint:
            p = Path(dir_hint).resolve()
            if self._is_path_allowed(str(p)):
                return p
        return Path.home() / "Downloads"

    def _is_path_allowed(self, target_path: str) -> bool:
        try:
            resolved = Path(target_path).resolve()
            allowed = [Path(d).resolve() for d in self.settings.ALLOWED_DIRECTORIES]
            return any(resolved == a or a in resolved.parents for a in allowed)
        except Exception:
            return False

    # ── TOOL IMPLEMENTATIONS ──────────────────────────────────────────────────
    async def open_file_or_folder(self, path: str) -> ToolExecutionResult:
        try:
            p = Path(path).resolve()
            if not p.exists():
                # Search by name in Downloads
                matches = list((Path.home() / "Downloads").glob(f"*{path}*"))
                if matches:
                    p = matches[0]
                else:
                    return ToolExecutionResult(success=False, error=f"Path '{path}' nahi mila.")

            os.startfile(str(p))
            return ToolExecutionResult(success=True, message=f"Ji Boss, '{p.name}' open kar diya.")
        except Exception as exc:
            return ToolExecutionResult(success=False, error=str(exc))

    async def search_files(self, query: str, directory: Optional[str] = None) -> ToolExecutionResult:
        root = self._resolve_safe_directory(directory)
        clean_q = query.lower().strip()
        matches = []

        try:
            for dirpath, _, filenames in os.walk(root):
                for f in filenames:
                    if clean_q in f.lower():
                        fp = os.path.join(dirpath, f)
                        matches.append({"name": f, "path": fp})
                        if len(matches) >= 15:
                            break
                if len(matches) >= 15:
                    break

            if not matches:
                return ToolExecutionResult(success=True, message=f"Boss, '{query}' se match karti koi file nahi mili.")

            names = ", ".join([m["name"] for m in matches[:5]])
            return ToolExecutionResult(
                success=True,
                data={"files": matches},
                message=f"Boss, {len(matches)} files mili hain: {names}",
            )
        except Exception as exc:
            return ToolExecutionResult(success=False, error=str(exc))

    async def find_by_extension(self, extension: str, directory: Optional[str] = None) -> ToolExecutionResult:
        root = self._resolve_safe_directory(directory)
        clean_ext = extension.lower().lstrip(".")
        matches = []

        try:
            for dirpath, _, filenames in os.walk(root):
                for f in filenames:
                    if f.lower().endswith(f".{clean_ext}"):
                        fp = os.path.join(dirpath, f)
                        stat = os.stat(fp)
                        matches.append({
                            "name": f,
                            "path": fp,
                            "size_mb": round(stat.st_size / (1024 * 1024), 2),
                        })
                        if len(matches) >= 15:
                            break
                if len(matches) >= 15:
                    break

            if not matches:
                return ToolExecutionResult(success=True, message=f"Boss, .{clean_ext} extension ki koi file nahi mili.")

            names = ", ".join([f"{m['name']} ({m['size_mb']}MB)" for m in matches[:5]])
            return ToolExecutionResult(
                success=True,
                data={"files": matches},
                message=f"Boss, {len(matches)} .{clean_ext} files mili hain: {names}",
            )
        except Exception as exc:
            return ToolExecutionResult(success=False, error=str(exc))

    async def find_large_files(self, min_size_mb: float = 100.0, directory: Optional[str] = None) -> ToolExecutionResult:
        root = self._resolve_safe_directory(directory)
        min_bytes = int(min_size_mb * 1024 * 1024)
        matches = []

        try:
            for dirpath, _, filenames in os.walk(root):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        stat = os.stat(fp)
                        if stat.st_size >= min_bytes:
                            matches.append({
                                "name": f,
                                "path": fp,
                                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                            })
                    except Exception:
                        pass
                if len(matches) >= 15:
                    break

            if not matches:
                return ToolExecutionResult(success=True, message=f"Boss, {min_size_mb}MB se badi koi file nahi mili.")

            matches.sort(key=lambda x: x["size_mb"], reverse=True)
            names = ", ".join([f"{m['name']} ({m['size_mb']}MB)" for m in matches[:5]])
            return ToolExecutionResult(
                success=True,
                data={"files": matches},
                message=f"Boss, {len(matches)} large files mili hain: {names}",
            )
        except Exception as exc:
            return ToolExecutionResult(success=False, error=str(exc))

    async def find_recent_files(self) -> ToolExecutionResult:
        root = Path.home() / "Downloads"
        cutoff = time.time() - (48 * 3600)  # last 48h
        matches = []

        try:
            for entry in os.scandir(root):
                if entry.is_file():
                    stat = entry.stat()
                    if stat.st_mtime >= cutoff:
                        matches.append({
                            "name": entry.name,
                            "path": entry.path,
                            "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%I:%M %p"),
                        })
            matches.sort(key=lambda x: x["modified"], reverse=True)
            if not matches:
                return ToolExecutionResult(success=True, message="Boss, pichle 48 ghanto mein koi nayi file modify nahi hui.")

            names = ", ".join([m["name"] for m in matches[:5]])
            return ToolExecutionResult(
                success=True,
                data={"files": matches},
                message=f"Boss, recent modified files: {names}",
            )
        except Exception as exc:
            return ToolExecutionResult(success=False, error=str(exc))

    async def show_hidden_files(self) -> ToolExecutionResult:
        """Set Windows Explorer to display hidden files."""
        if not WINREG_AVAILABLE:
            return ToolExecutionResult(success=False, error="Windows registry is not accessible.")
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "Hidden", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            return ToolExecutionResult(
                success=True,
                message="Ji Boss, Windows Explorer mein hidden files show kar di gayi hain.",
            )
        except Exception as exc:
            return ToolExecutionResult(success=False, error=f"Could not change hidden files setting: {exc}")

    async def hide_hidden_files(self) -> ToolExecutionResult:
        """Set Windows Explorer to hide hidden files."""
        if not WINREG_AVAILABLE:
            return ToolExecutionResult(success=False, error="Windows registry is not accessible.")
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "Hidden", 0, winreg.REG_DWORD, 2)
            winreg.CloseKey(key)
            return ToolExecutionResult(
                success=True,
                message="Ji Boss, hidden files hide kar di gayi hain.",
            )
        except Exception as exc:
            return ToolExecutionResult(success=False, error=f"Could not change hidden files setting: {exc}")

    async def create_folder(self, folder_name: str, directory: Optional[str] = None) -> ToolExecutionResult:
        root = self._resolve_safe_directory(directory)
        target = root / folder_name
        try:
            target.mkdir(parents=True, exist_ok=True)
            return ToolExecutionResult(
                success=True,
                message=f"Ji Boss, '{folder_name}' folder create kar diya at {target}.",
            )
        except Exception as exc:
            return ToolExecutionResult(success=False, error=str(exc))

    async def get_file_properties(self, path: str) -> ToolExecutionResult:
        try:
            p = Path(path).resolve()
            if not p.exists():
                return ToolExecutionResult(success=False, error="File not found.")
            stat = p.stat()
            size_mb = round(stat.st_size / (1024 * 1024), 2)
            mod_t = datetime.fromtimestamp(stat.st_mtime).strftime("%d %b %Y %I:%M %p")
            msg = f"File: {p.name}\nSize: {size_mb} MB ({stat.st_size} bytes)\nModified: {mod_t}\nPath: {p}"
            return ToolExecutionResult(
                success=True,
                data={"name": p.name, "size_mb": size_mb, "modified": mod_t, "path": str(p)},
                message=msg,
            )
        except Exception as exc:
            return ToolExecutionResult(success=False, error=str(exc))


file_manager_adapter = FileManagerAdapter()
