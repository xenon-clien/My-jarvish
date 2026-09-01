"""Standard system diagnostic, status, and hardware tools for JARVIS AI."""
from datetime import datetime
import os
import platform
import socket
from typing import Any, Dict, List
import psutil
from pydantic import BaseModel, Field

from backend.core.permissions import PermissionLevel, ToolCategory
from backend.tools.registry import tool


class EchoArgs(BaseModel):
    message: str = Field(..., description="Message string to echo back.")


@tool(
    name="get_current_time",
    description="Get the current local system time, date, and timezone.",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.SYSTEM,
)
def get_current_time() -> Dict[str, str]:
    """Retrieve the current local system time and date."""
    now = datetime.now()
    return {
        "time": now.strftime("%I:%M:%S %p"),
        "date": now.strftime("%A, %B %d, %Y"),
        "iso": now.isoformat(),
    }


@tool(
    name="get_system_status",
    description="Get overall system health metrics including CPU usage, RAM utilization, and OS platform.",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.SYSTEM,
)
def get_system_status() -> Dict[str, Any]:
    """Retrieve current host system health metrics."""
    cpu_pct = psutil.cpu_percent(interval=0.1)
    virtual_mem = psutil.virtual_memory()

    return {
        "os": f"{platform.system()} {platform.release()}",
        "architecture": platform.machine(),
        "cpu_usage_percent": cpu_pct,
        "ram_used_gb": round(virtual_mem.used / (1024 ** 3), 2),
        "ram_total_gb": round(virtual_mem.total / (1024 ** 3), 2),
        "ram_percent": virtual_mem.percent,
        "status": "Healthy",
    }


@tool(
    name="get_battery_status",
    description="Get laptop battery percentage, power plug status, and remaining time.",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.SYSTEM,
)
def get_battery_status() -> Dict[str, Any]:
    """Retrieve battery status using psutil sensors."""
    battery = psutil.sensors_battery()
    if battery is None:
        return {
            "has_battery": False,
            "status": "Desktop / No battery sensor detected (Running on direct power).",
        }

    return {
        "has_battery": True,
        "percent": battery.percent,
        "power_plugged": battery.power_plugged,
        "charging_status": "Charging" if battery.power_plugged else "Discharging (On Battery)",
        "seconds_left": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None,
    }


@tool(
    name="get_storage_status",
    description="Get disk storage usage, total capacity, and available free space for system drives.",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.SYSTEM,
)
def get_storage_status() -> Dict[str, Any]:
    """Retrieve disk storage capacity and free space."""
    partitions = psutil.disk_partitions()
    drives: List[Dict[str, Any]] = []

    for part in partitions:
        try:
            # Skip read-only or optical drives
            if "cdrom" in part.opts or not part.fstype:
                continue
            usage = psutil.disk_usage(part.mountpoint)
            drives.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "total_gb": round(usage.total / (1024 ** 3), 2),
                "used_gb": round(usage.used / (1024 ** 3), 2),
                "free_gb": round(usage.free / (1024 ** 3), 2),
                "percent_used": usage.percent,
            })
        except (PermissionError, OSError):
            continue

    return {"drives": drives}


@tool(
    name="get_network_status",
    description="Get network status, hostname, local IP addresses, and internet connectivity test.",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.SYSTEM,
)
def get_network_status() -> Dict[str, Any]:
    """Retrieve network configuration and test internet connectivity."""
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "127.0.0.1"

    # Test connectivity with a fast socket ping to DNS 8.8.8.8
    internet_available = False
    try:
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_sock.settimeout(2.0)
        test_sock.connect(("8.8.8.8", 53))
        test_sock.close()
        internet_available = True
    except Exception:
        internet_available = False

    return {
        "hostname": hostname,
        "local_ip": local_ip,
        "internet_connected": internet_available,
        "status": "Online" if internet_available else "Offline / Local Network Only",
    }


@tool(
    name="echo_message",
    description="Echo a message back to the caller for connectivity and argument testing.",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.SYSTEM,
    args_schema=EchoArgs,
)
def echo_message(message: str) -> Dict[str, str]:
    """Echo test tool."""
    return {"echo": message}


class ProblemSolverArgs(BaseModel):
    problem_description: str = Field(..., description="Natural language description of the PC issue (e.g. 'Bluetooth nahi chal raha', 'WiFi disconnected', 'Laptop slow', 'No sound', 'npm error').")
    auto_repair: bool = Field(True, description="Whether to safely execute low-risk repairs automatically.")


@tool(
    name="diagnose_system_problem",
    description="Diagnose, troubleshoot, isolate root causes, and safely self-repair PC issues (Bluetooth, Wi-Fi, Internet, Audio, USB, Slow PC, Storage, Windows Update, NPM/Dev tools).",
    permission_level=PermissionLevel.LEVEL_1_NORMAL,
    category=ToolCategory.SYSTEM,
    args_schema=ProblemSolverArgs,
)
def diagnose_system_problem(problem_description: str, auto_repair: bool = True) -> Dict[str, Any]:
    """Execute end-to-end diagnosis, RCA, safe self-repair, and strict verification."""
    from backend.problem_solver.problem_solver_engine import problem_solver_engine
    return problem_solver_engine.solve_problem(problem_description, auto_repair=auto_repair)


@tool(
    name="get_comprehensive_system_health",
    description="Run a full-system universal hardware, OS, storage, battery, CPU, RAM, Bluetooth, Wi-Fi, and audio health scan.",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.SYSTEM,
)
def get_comprehensive_system_health() -> Dict[str, Any]:
    """Run master universal system health scan."""
    from backend.problem_solver.system_health import SystemHealthEngine
    return SystemHealthEngine.get_full_health_report()

