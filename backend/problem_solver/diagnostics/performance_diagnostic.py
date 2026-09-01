"""System Performance, Freezing, High CPU/RAM/Disk, and Bottleneck Diagnostic Engine."""
import os
import subprocess
from typing import Any, Dict, List, Optional
import psutil

from backend.core.logger import get_logger
from backend.problem_solver.models import (
    DiagnosticItem, DiagnosticReport, DiagnosticStatus, ProblemCategory
)

logger = get_logger("PerformanceDiagnostic")


class PerformanceDiagnostic:
    """Diagnoses laptop freezing, slow performance, 100% CPU/Disk usage, and RAM saturation."""

    @staticmethod
    def run_diagnostic() -> DiagnosticReport:
        """Execute deep system performance analysis."""
        items: List[DiagnosticItem] = []
        raw_evidence: Dict[str, Any] = {}
        overall_status = DiagnosticStatus.HEALTHY
        summary_points = []

        # 1. CPU Utilization & Core load
        cpu_pct = psutil.cpu_percent(interval=0.2)
        logical_cores = psutil.cpu_count(logical=True)
        raw_evidence["cpu_percent"] = cpu_pct
        raw_evidence["cpu_cores"] = logical_cores

        if cpu_pct >= 90.0:
            overall_status = DiagnosticStatus.PROBLEM_DETECTED
            items.append(DiagnosticItem(
                name="CPU Utilization",
                status=DiagnosticStatus.PROBLEM_DETECTED,
                value=f"{cpu_pct}% (Severe Load / Spiking)",
                details="Processor is under extreme load causing system sluggishness or freezing.",
            ))
            summary_points.append(f"High CPU usage ({cpu_pct}%)")
        elif cpu_pct >= 75.0:
            items.append(DiagnosticItem(
                name="CPU Utilization",
                status=DiagnosticStatus.WARNING,
                value=f"{cpu_pct}% (High Load)",
                details="Processor load is moderately high.",
            ))
        else:
            items.append(DiagnosticItem(
                name="CPU Utilization",
                status=DiagnosticStatus.HEALTHY,
                value=f"{cpu_pct}% (Normal)",
                details=f"CPU load across {logical_cores} cores is normal.",
            ))

        # 2. RAM Memory Saturation
        mem = psutil.virtual_memory()
        ram_pct = mem.percent
        used_gb = round(mem.used / (1024 ** 3), 2)
        total_gb = round(mem.total / (1024 ** 3), 2)
        free_gb = round(mem.available / (1024 ** 3), 2)
        raw_evidence["ram_percent"] = ram_pct
        raw_evidence["ram_used_gb"] = used_gb
        raw_evidence["ram_total_gb"] = total_gb

        if ram_pct >= 90.0:
            overall_status = DiagnosticStatus.PROBLEM_DETECTED
            items.append(DiagnosticItem(
                name="RAM Memory Usage",
                status=DiagnosticStatus.PROBLEM_DETECTED,
                value=f"{ram_pct}% ({used_gb} GB / {total_gb} GB used)",
                details=f"Only {free_gb} GB RAM remaining. System may start aggressive disk paging/swapping.",
            ))
            summary_points.append(f"RAM almost saturated ({ram_pct}%)")
        elif ram_pct >= 80.0:
            items.append(DiagnosticItem(
                name="RAM Memory Usage",
                status=DiagnosticStatus.WARNING,
                value=f"{ram_pct}% ({used_gb} GB / {total_gb} GB used)",
                details=f"{free_gb} GB RAM available.",
            ))
        else:
            items.append(DiagnosticItem(
                name="RAM Memory Usage",
                status=DiagnosticStatus.HEALTHY,
                value=f"{ram_pct}% ({used_gb} GB / {total_gb} GB used)",
                details=f"{free_gb} GB RAM available for smooth multitasking.",
            ))

        # 3. Top Resource Consuming Processes
        top_cpu_procs = []
        top_mem_procs = []
        try:
            procs = []
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info']):
                try:
                    p_info = p.info
                    procs.append(p_info)
                except Exception:
                    continue

            # Sort top memory
            procs_by_mem = sorted(procs, key=lambda x: (x.get('memory_percent') or 0.0), reverse=True)[:5]
            for p in procs_by_mem:
                mem_mb = round((p.get('memory_info').rss if p.get('memory_info') else 0) / (1024 ** 2), 1)
                top_mem_procs.append({
                    "name": p.get('name'),
                    "pid": p.get('pid'),
                    "ram_mb": mem_mb,
                    "ram_percent": round(p.get('memory_percent') or 0.0, 1),
                })
        except Exception as e:
            logger.debug(f"Process inspection error: {e}")

        raw_evidence["top_memory_processes"] = top_mem_procs

        if top_mem_procs:
            top_mem_text = ", ".join([f"{p['name']} ({p['ram_mb']}MB)" for p in top_mem_procs[:3]])
            items.append(DiagnosticItem(
                name="Top Memory Consumers",
                status=DiagnosticStatus.HEALTHY if ram_pct < 85 else DiagnosticStatus.WARNING,
                value=top_mem_text,
                details=f"Top RAM processes: {top_mem_text}",
            ))

        # 4. Startup Programs Inspection via Windows Registry
        startup_items = []
        try:
            cmd = "powershell -NoProfile -Command \"Get-CimInstance Win32_StartupCommand | Select-Object -Property Name, Command, Location | ConvertTo-Json -Compress\""
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=4)
            if res.returncode == 0 and res.stdout.strip():
                import json
                try:
                    data = json.loads(res.stdout.strip())
                    startup_items = [data] if isinstance(data, dict) else (data if isinstance(data, list) else [])
                except Exception:
                    startup_items = []
        except Exception:
            pass

        raw_evidence["startup_count"] = len(startup_items)
        if len(startup_items) > 12:
            items.append(DiagnosticItem(
                name="Startup Applications",
                status=DiagnosticStatus.WARNING,
                value=f"{len(startup_items)} Programs launching on Boot",
                details="High number of background applications starting with Windows can slow down boot and overall speed.",
            ))
            if ram_pct >= 80.0:
                summary_points.append(f"{len(startup_items)} startup programs loading into memory")
        else:
            items.append(DiagnosticItem(
                name="Startup Applications",
                status=DiagnosticStatus.HEALTHY,
                value=f"{len(startup_items)} Programs on Boot",
                details="Startup application load is within normal parameters.",
            ))

        if overall_status == DiagnosticStatus.HEALTHY:
            summary = "System performance, CPU load, and RAM memory utilization are healthy."
        else:
            summary = f"Performance bottleneck detected: {'; '.join(summary_points)}."

        return DiagnosticReport(
            category=ProblemCategory.PERFORMANCE_HANG if cpu_pct >= 90 or ram_pct >= 90 else ProblemCategory.SLOW_SYSTEM,
            overall_status=overall_status,
            summary=summary,
            items=items,
            raw_evidence=raw_evidence,
            suggested_focus="cpu_spike" if cpu_pct >= 90 else ("ram_saturation" if ram_pct >= 85 else "startup_apps"),
        )
