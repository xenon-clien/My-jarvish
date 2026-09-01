"""System junk cleaner, cache cleaner, and Windows maintenance tools for JARVIS AI."""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
import psutil

from backend.core.logger import get_logger
from backend.core.permissions import PermissionLevel, ToolCategory
from backend.tools.registry import tool

logger = get_logger("CleanerTools")


@tool(
    name="clean_junk_files",
    description="Clean temporary cache files, Windows Temp folder, and junk data to free up storage space. (e.g. 'Junk files clean karo', 'Clean cache', 'Free up space', 'Clean temporary files').",
    permission_level=PermissionLevel.LEVEL_1_NORMAL,
    category=ToolCategory.SYSTEM,
)
def clean_junk_files() -> Dict[str, Any]:
    """Clean Windows Temp directory and user cache files safely."""
    temp_dirs = [
        tempfile.gettempdir(),
        "C:\\Windows\\Temp",
    ]

    total_deleted_bytes = 0
    deleted_files_count = 0
    failed_files_count = 0

    for temp_dir in temp_dirs:
        if not os.path.exists(temp_dir):
            continue

        for root, dirs, files in os.walk(temp_dir, topdown=False):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                try:
                    size = os.path.getsize(file_path)
                    os.remove(file_path)
                    total_deleted_bytes += size
                    deleted_files_count += 1
                except Exception:
                    # In-use files will naturally be locked by active processes
                    failed_files_count += 1

            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    os.rmdir(dir_path)
                except Exception:
                    pass

    freed_mb = round(total_deleted_bytes / (1024 * 1024), 2)
    logger.info(f"Cleaned {deleted_files_count} junk files, freed {freed_mb} MB.")
    return {
        "status": "success",
        "freed_mb": freed_mb,
        "files_deleted": deleted_files_count,
        "locked_files_skipped": failed_files_count,
        "message": f"Successfully cleaned {deleted_files_count} temporary files and freed {freed_mb} MB of disk space.",
    }


@tool(
    name="empty_recycle_bin",
    description="Empty the Windows Recycle Bin permanently. (e.g. 'Recycle bin empty karo', 'Empty recycle bin', 'Trash clean karo').",
    permission_level=PermissionLevel.LEVEL_1_NORMAL,
    category=ToolCategory.SYSTEM,
)
def empty_recycle_bin() -> Dict[str, Any]:
    """Empty Windows Recycle Bin using PowerShell."""
    try:
        cmd = 'powershell.exe -NoProfile -Command "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"'
        subprocess.run(cmd, shell=True, timeout=10)
        logger.info("Emptied Windows Recycle Bin.")
        return {
            "status": "success",
            "message": "Windows Recycle Bin has been emptied successfully.",
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Could not empty recycle bin: {exc}",
        }


@tool(
    name="get_system_health",
    description="Scan overall PC health, RAM consumption, storage levels, and CPU load. (e.g. 'System health check karo', 'Check PC status').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.SYSTEM,
)
def get_system_health() -> Dict[str, Any]:
    """Retrieve diagnostic health status of Windows system."""
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")
    cpu = psutil.cpu_percent(interval=0.2)

    battery_info = "Desktop / No Battery"
    if hasattr(psutil, "sensors_battery"):
        bat = psutil.sensors_battery()
        if bat:
            battery_info = f"{round(bat.percent)}% ({'Charging' if bat.power_plugged else 'Discharging'})"

    return {
        "status": "success",
        "cpu_usage_percent": cpu,
        "ram_used_gb": round((mem.total - mem.available) / (1024**3), 2),
        "ram_total_gb": round(mem.total / (1024**3), 2),
        "ram_percent": mem.percent,
        "disk_free_gb": round(disk.free / (1024**3), 2),
        "disk_percent": disk.percent,
        "battery": battery_info,
        "message": f"System Health: CPU at {cpu}%, RAM at {mem.percent}% ({round(mem.used/(1024**3),1)}GB used), Disk C: at {disk.percent}% used ({round(disk.free/(1024**3),1)}GB free), Battery: {battery_info}.",
    }
