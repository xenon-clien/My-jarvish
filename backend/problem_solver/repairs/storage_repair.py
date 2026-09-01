"""Safe Storage and Temporary File Cleanup Repair Module."""
import os
import shutil
from typing import Any, Dict

from backend.core.logger import get_logger

logger = get_logger("StorageRepair")


class StorageRepair:
    """Performs safe, non-destructive temporary file cleanup and Recycle Bin flushing."""

    @staticmethod
    def clean_temporary_files() -> Dict[str, Any]:
        """Clean Windows and User temporary directories safely without touching personal files."""
        logger.info("Cleaning approved temporary file caches...")
        temp_dirs = [
            os.environ.get("TEMP", ""),
            os.environ.get("TMP", ""),
            os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Temp"),
        ]
        temp_dirs = list(set([d for d in temp_dirs if d and os.path.exists(d)]))

        deleted_bytes = 0
        deleted_count = 0

        for t_dir in temp_dirs:
            try:
                for item in os.listdir(t_dir):
                    item_path = os.path.join(t_dir, item)
                    try:
                        if os.path.isfile(item_path) or os.path.islink(item_path):
                            sz = os.path.getsize(item_path)
                            os.unlink(item_path)
                            deleted_bytes += sz
                            deleted_count += 1
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path, ignore_errors=True)
                    except Exception:
                        continue
            except Exception:
                continue

        freed_mb = round(deleted_bytes / (1024 ** 2), 1)
        return {
            "status": "success",
            "action": "clean_temporary_files",
            "freed_mb": freed_mb,
            "deleted_count": deleted_count,
            "message": f"Successfully cleared {freed_mb} MB of temporary files ({deleted_count} files removed).",
        }

    @staticmethod
    def empty_recycle_bin() -> Dict[str, Any]:
        """Empty the Windows Recycle Bin."""
        try:
            from backend.tools.cleaner_tools import empty_recycle_bin
            res = empty_recycle_bin()
            return {
                "status": "success",
                "action": "empty_recycle_bin",
                "message": res.get("message", "Recycle Bin emptied successfully."),
            }
        except Exception as e:
            return {"status": "error", "action": "empty_recycle_bin", "message": f"Recycle Bin error: {e}"}
