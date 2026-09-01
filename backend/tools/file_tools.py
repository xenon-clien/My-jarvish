"""Safe sandboxed file and directory management tools for JARVIS AI.

Enforces strict boundary checking on every operation to prevent directory traversal
and restricts file interactions to user-approved directories.
"""
from datetime import datetime
import fnmatch
import os
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.core.permissions import PermissionLevel, ToolCategory
from backend.core.security import security_manager
from backend.tools.registry import tool


# ==========================================
# Pydantic Schemas for Tool Input Arguments
# ==========================================

class FindFilesArgs(BaseModel):
    query: str = Field(..., description="File name pattern or extension to search for (e.g. '*.pdf', 'resume', 'project.zip').")
    search_directory: Optional[str] = Field(None, description="Specific directory to search in. Defaults to searching allowed directories.")
    max_results: int = Field(15, description="Maximum number of matches to return.")


class ListDirectoryArgs(BaseModel):
    directory_path: Optional[str] = Field(None, description="Directory path to list. If omitted, lists the current project root.")
    show_hidden: bool = Field(False, description="Whether to include hidden files (starting with .).")


class ReadFileArgs(BaseModel):
    file_path: str = Field(..., description="Absolute or relative path of the file to read.")
    max_lines: int = Field(100, description="Maximum number of lines to read to avoid huge output tokens.")


class FileInfoArgs(BaseModel):
    file_path: str = Field(..., description="Path of the file to inspect.")


class CreateFolderArgs(BaseModel):
    folder_path: str = Field(..., description="Path of the new directory to create.")


class RenameFileArgs(BaseModel):
    source_path: str = Field(..., description="Current path of the file or folder to rename.")
    new_name: str = Field(..., description="New base name for the file or folder (not a full path).")


class CopyMoveFileArgs(BaseModel):
    source_path: str = Field(..., description="Source file or directory path.")
    destination_path: str = Field(..., description="Target destination file or directory path.")


class DeleteFileArgs(BaseModel):
    file_path: str = Field(..., description="Path of the file or directory to delete.")


# ==========================================
# Level 0 (Safe Read-Only Tools)
# ==========================================

@tool(
    name="find_files",
    description="Search for files by name pattern or extension (e.g. '*.py', 'DBMS PDF', 'project') across allowed directories. Set include_hidden=True if user explicitly requests hidden files.",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.FILE,
    args_schema=FindFilesArgs,
)
def find_files(
    query: str,
    search_directory: Optional[str] = None,
    include_hidden: bool = False,
    max_results: int = 15,
) -> Dict[str, Any]:
    """Recursively search for files matching a pattern within allowed directories."""
    results: List[Dict[str, Any]] = []

    # Determine directories to scan
    if search_directory:
        target_dir = security_manager.ensure_path_allowed(search_directory)
        if not target_dir.is_dir():
            raise NotADirectoryError(f"'{search_directory}' is not a directory.")
        scan_dirs = [target_dir]
    else:
        scan_dirs = security_manager.get_allowed_directories()

    pattern = f"*{query}*" if not ("*" in query or "?" in query) else query

    for root_dir in scan_dirs:
        if not root_dir.exists():
            continue
        for root, dirs, files in os.walk(root_dir):
            if not include_hidden:
                # Skip hidden folders and __pycache__
                dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]

            for file in files:
                if not include_hidden and file.startswith("."):
                    continue
                if fnmatch.fnmatch(file.lower(), pattern.lower()):
                    file_p = Path(root) / file
                    try:
                        stat = file_p.stat()
                        results.append({
                            "name": file,
                            "path": str(file_p),
                            "size_kb": round(stat.st_size / 1024, 2),
                            "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                        })
                    except (PermissionError, OSError):
                        continue

                    if len(results) >= max_results:
                        break
            if len(results) >= max_results:
                break

    return {
        "query": query,
        "matches_found": len(results),
        "files": results,
    }


@tool(
    name="list_directory",
    description="List all files and subdirectories inside an allowed folder. If directory_path is omitted or None, lists the current workspace directory.",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.FILE,
    args_schema=ListDirectoryArgs,
)
def list_directory(
    directory_path: Optional[str] = None,
    show_hidden: bool = False,
) -> Dict[str, Any]:
    """Inspect contents of a folder within allowed directories."""
    if directory_path:
        target = security_manager.ensure_path_allowed(directory_path)
    else:
        # Default to current directory if allowed, otherwise first allowed
        cwd = Path.cwd().resolve()
        target = cwd if security_manager.is_path_allowed(cwd) else security_manager.get_allowed_directories()[0]

    if not target.exists():
        raise FileNotFoundError(f"Directory '{target}' does not exist.")
    if not target.is_dir():
        raise NotADirectoryError(f"'{target}' is a file, not a directory.")

    entries: List[Dict[str, Any]] = []
    for item in target.iterdir():
        if not show_hidden and item.name.startswith("."):
            continue
        try:
            stat = item.stat()
            entries.append({
                "name": item.name,
                "type": "folder" if item.is_dir() else "file",
                "size_kb": round(stat.st_size / 1024, 2) if item.is_file() else None,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            })
        except (PermissionError, OSError):
            continue

    return {
        "directory": str(target),
        "total_items": len(entries),
        "items": sorted(entries, key=lambda x: (x["type"] != "folder", x["name"].lower())),
    }


@tool(
    name="read_file_content",
    description="Read and return text or code contents from a file in an allowed directory.",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.FILE,
    args_schema=ReadFileArgs,
)
def read_file_content(file_path: str, max_lines: int = 100) -> Dict[str, Any]:
    """Safely read text file content with line limit protection."""
    target = security_manager.ensure_path_allowed(file_path)

    if not target.exists():
        raise FileNotFoundError(f"File '{file_path}' does not exist.")
    if not target.is_file():
        raise IsADirectoryError(f"'{file_path}' is a directory, not a file.")

    # Guard against binary / excessively large files
    size_mb = target.stat().st_size / (1024 * 1024)
    if size_mb > 10.0:
        raise ValueError(f"File is too large to read safely ({round(size_mb, 2)} MB > 10 MB limit).")

    lines: List[str] = []
    with open(target, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            if i >= max_lines:
                break
            lines.append(line)

    content = "".join(lines)
    return {
        "file_path": str(target),
        "lines_read": len(lines),
        "content": content,
    }


@tool(
    name="get_file_info",
    description="Get metadata, size, timestamps, and permissions for a file or folder.",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.FILE,
    args_schema=FileInfoArgs,
)
def get_file_info(file_path: str) -> Dict[str, Any]:
    """Retrieve detailed metadata for a file or folder."""
    target = security_manager.ensure_path_allowed(file_path)

    if not target.exists():
        raise FileNotFoundError(f"Path '{file_path}' does not exist.")

    stat = target.stat()
    return {
        "name": target.name,
        "absolute_path": str(target),
        "is_file": target.is_file(),
        "is_directory": target.is_dir(),
        "size_bytes": stat.st_size,
        "size_kb": round(stat.st_size / 1024, 2),
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "created_at": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
        "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "extension": target.suffix if target.is_file() else None,
    }


# ==========================================
# Level 1 (Normal Operations)
# ==========================================

@tool(
    name="create_folder",
    description="Create a new folder inside an allowed directory.",
    permission_level=PermissionLevel.LEVEL_1_NORMAL,
    category=ToolCategory.FILE,
    args_schema=CreateFolderArgs,
)
def create_folder(folder_path: str) -> Dict[str, Any]:
    """Create a directory including any missing parent directories."""
    target = security_manager.ensure_path_allowed(folder_path)
    target.mkdir(parents=True, exist_ok=True)
    return {
        "status": "success",
        "message": f"Folder created at '{target}'",
        "path": str(target),
    }


@tool(
    name="rename_file",
    description="Rename a file or folder in place within allowed directories.",
    permission_level=PermissionLevel.LEVEL_1_NORMAL,
    category=ToolCategory.FILE,
    args_schema=RenameFileArgs,
)
def rename_file(source_path: str, new_name: str) -> Dict[str, Any]:
    """Rename a file or directory safely."""
    if not security_manager.validate_safe_filename(new_name):
        raise ValueError(f"Invalid filename '{new_name}'. Cannot contain path separators or illegal characters.")

    source = security_manager.ensure_path_allowed(source_path)
    if not source.exists():
        raise FileNotFoundError(f"Source '{source_path}' does not exist.")

    destination = source.parent / new_name
    security_manager.ensure_path_allowed(destination)

    if destination.exists():
        raise FileExistsError(f"A file or folder named '{new_name}' already exists in that location.")

    source.rename(destination)
    return {
        "status": "success",
        "message": f"Renamed '{source.name}' to '{new_name}'",
        "new_path": str(destination),
    }


@tool(
    name="copy_file",
    description="Copy a file or directory from one allowed location to another.",
    permission_level=PermissionLevel.LEVEL_1_NORMAL,
    category=ToolCategory.FILE,
    args_schema=CopyMoveFileArgs,
)
def copy_file(source_path: str, destination_path: str) -> Dict[str, Any]:
    """Copy a file or directory tree safely."""
    source = security_manager.ensure_path_allowed(source_path)
    destination = security_manager.ensure_path_allowed(destination_path)

    if not source.exists():
        raise FileNotFoundError(f"Source path '{source_path}' does not exist.")

    # If destination is an existing directory, copy inside it
    if destination.is_dir():
        destination = destination / source.name

    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)
    else:
        shutil.copy2(source, destination)

    return {
        "status": "success",
        "message": f"Copied '{source.name}' to '{destination}'",
        "destination": str(destination),
    }


@tool(
    name="move_file",
    description="Move a file or directory from one allowed location to another.",
    permission_level=PermissionLevel.LEVEL_1_NORMAL,
    category=ToolCategory.FILE,
    args_schema=CopyMoveFileArgs,
)
def move_file(source_path: str, destination_path: str) -> Dict[str, Any]:
    """Move a file or directory safely."""
    source = security_manager.ensure_path_allowed(source_path)
    destination = security_manager.ensure_path_allowed(destination_path)

    if not source.exists():
        raise FileNotFoundError(f"Source path '{source_path}' does not exist.")

    if destination.is_dir():
        destination = destination / source.name

    shutil.move(str(source), str(destination))
    return {
        "status": "success",
        "message": f"Moved '{source.name}' to '{destination}'",
        "destination": str(destination),
    }


# ==========================================
# Level 3 (Destructive Actions - Mandatory Confirmation)
# ==========================================

@tool(
    name="delete_file",
    description="Delete a file or folder permanently. (LEVEL 3: Requires explicit user confirmation).",
    permission_level=PermissionLevel.LEVEL_3_DESTRUCTIVE,
    category=ToolCategory.FILE,
    args_schema=DeleteFileArgs,
)
def delete_file(file_path: str) -> Dict[str, Any]:
    """Delete a file or folder within allowed directories."""
    target = security_manager.ensure_path_allowed(file_path)

    if not target.exists():
        raise FileNotFoundError(f"Target path '{file_path}' does not exist.")

    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()

    return {
        "status": "success",
        "message": f"Permanently deleted '{target.name}'",
        "deleted_path": str(target),
    }
