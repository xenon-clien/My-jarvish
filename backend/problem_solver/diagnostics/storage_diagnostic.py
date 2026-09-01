"""Storage Capacity, Disk Space, Temporary Files, and Large Files Diagnostic Engine."""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import psutil

from backend.core.logger import get_logger
from backend.problem_solver.models import (
    DiagnosticItem, DiagnosticReport, DiagnosticStatus, ProblemCategory
)

logger = get_logger("StorageDiagnostic")


class StorageDiagnostic:
    """Diagnoses low disk space, temporary junk accumulation, and large file storage distribution."""

    @staticmethod
    def run_diagnostic() -> DiagnosticReport:
        """Execute comprehensive storage diagnostics and preview generation."""
        items: List[DiagnosticItem] = []
        raw_evidence: Dict[str, Any] = {}
        overall_status = DiagnosticStatus.HEALTHY
        summary_points = []

        # 1. Drive Partitions Space Analysis
        partitions = psutil.disk_partitions()
        drives_data = []
        low_space_drives = []

        for part in partitions:
            try:
                if "cdrom" in part.opts or not part.fstype:
                    continue
                usage = psutil.disk_usage(part.mountpoint)
                total_gb = round(usage.total / (1024 ** 3), 1)
                used_gb = round(usage.used / (1024 ** 3), 1)
                free_gb = round(usage.free / (1024 ** 3), 1)
                pct = usage.percent

                drives_data.append({
                    "mountpoint": part.mountpoint,
                    "total_gb": total_gb,
                    "free_gb": free_gb,
                    "percent_used": pct,
                })

                if free_gb < 15.0 or pct >= 90.0:
                    low_space_drives.append(part.mountpoint)
                    items.append(DiagnosticItem(
                        name=f"Drive ({part.mountpoint}) Space",
                        status=DiagnosticStatus.PROBLEM_DETECTED,
                        value=f"{free_gb} GB Free ({pct}% Used)",
                        details=f"Critically low disk space on {part.mountpoint}. May impact Windows Updates and virtual memory.",
                    ))
                    summary_points.append(f"Drive {part.mountpoint} low on space ({free_gb} GB free)")
                elif free_gb < 30.0 or pct >= 80.0:
                    items.append(DiagnosticItem(
                        name=f"Drive ({part.mountpoint}) Space",
                        status=DiagnosticStatus.WARNING,
                        value=f"{free_gb} GB Free ({pct}% Used)",
                        details=f"Moderate disk space available on {part.mountpoint}.",
                    ))
                else:
                    items.append(DiagnosticItem(
                        name=f"Drive ({part.mountpoint}) Space",
                        status=DiagnosticStatus.HEALTHY,
                        value=f"{free_gb} GB Free ({pct}% Used)",
                        details=f"Plenty of free storage on {part.mountpoint} ({total_gb} GB total).",
                    ))
            except Exception:
                continue

        raw_evidence["drives"] = drives_data

        if low_space_drives:
            overall_status = DiagnosticStatus.PROBLEM_DETECTED

        # 2. Temporary Files and Cache Footprint Scan
        temp_dirs = [
            os.environ.get("TEMP", ""),
            os.environ.get("TMP", ""),
            os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Temp"),
        ]
        temp_dirs = list(set([d for d in temp_dirs if d and os.path.exists(d)]))

        total_temp_bytes = 0
        temp_file_count = 0
        for t_dir in temp_dirs:
            try:
                for root, _, files in os.walk(t_dir):
                    for f in files:
                        try:
                            fp = os.path.join(root, f)
                            total_temp_bytes += os.path.getsize(fp)
                            temp_file_count += 1
                        except Exception:
                            continue
            except Exception:
                continue

        temp_mb = round(total_temp_bytes / (1024 ** 2), 1)
        raw_evidence["temp_files"] = {"size_mb": temp_mb, "count": temp_file_count}

        if temp_mb >= 5000:  # >5 GB
            items.append(DiagnosticItem(
                name="Temporary & Cache Files",
                status=DiagnosticStatus.WARNING,
                value=f"{round(temp_mb/1024, 2)} GB ({temp_file_count} files)",
                details="Significant accumulation of Windows and application temporary cache files.",
            ))
            if not summary_points:
                summary_points.append(f"{round(temp_mb/1024, 1)} GB reclaimable temp files")
        else:
            items.append(DiagnosticItem(
                name="Temporary & Cache Files",
                status=DiagnosticStatus.HEALTHY,
                value=f"{temp_mb} MB ({temp_file_count} files)",
                details="Temporary file footprint is within normal limits.",
            ))

        # 3. Downloads Folder Footprint
        user_profile = os.environ.get("USERPROFILE", "")
        downloads_dir = os.path.join(user_profile, "Downloads")
        downloads_mb = 0
        if os.path.exists(downloads_dir):
            try:
                for f in os.listdir(downloads_dir):
                    fp = os.path.join(downloads_dir, f)
                    if os.path.isfile(fp):
                        try:
                            downloads_mb += os.path.getsize(fp)
                        except Exception:
                            pass
                downloads_mb = round(downloads_mb / (1024 ** 2), 1)
            except Exception:
                pass

        raw_evidence["downloads_mb"] = downloads_mb
        items.append(DiagnosticItem(
            name="Downloads Folder",
            status=DiagnosticStatus.HEALTHY if downloads_mb < 20000 else DiagnosticStatus.WARNING,
            value=f"{round(downloads_mb/1024, 1)} GB" if downloads_mb >= 1024 else f"{downloads_mb} MB",
            details="User Downloads directory contents.",
        ))

        if overall_status == DiagnosticStatus.HEALTHY:
            summary = "Storage capacity and disk space across system partitions are in good health."
        else:
            summary = f"Storage warning: {'; '.join(summary_points)}."

        return DiagnosticReport(
            category=ProblemCategory.STORAGE,
            overall_status=overall_status,
            summary=summary,
            items=items,
            raw_evidence=raw_evidence,
            suggested_focus="low_disk_space" if low_space_drives else "temp_cleanup",
        )
