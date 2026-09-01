"""Safety, command validation, risk classification, and privacy redaction for Problem Solver."""
import re
import shlex
from typing import Any, Dict, List, Optional, Set, Tuple
from backend.core.logger import get_logger
from backend.problem_solver.models import RiskLevel

logger = get_logger("ProblemSolverSafety")

# Allowed safe system utilities and commands for diagnostics and repairs
SAFE_COMMAND_ALLOWLIST: Set[str] = {
    "ipconfig", "ping", "tracert", "nslookup", "netsh", "net", "sc",
    "powershell", "powershell.exe", "pwsh", "pwsh.exe", "cmd", "cmd.exe",
    "wmic", "systeminfo", "driverquery", "pnputil", "dism", "sfc",
    "tasklist", "taskkill", "node", "npm", "python", "git", "where",
    "get-service", "restart-service", "start-service", "stop-service",
    "get-pnpdevice", "restart-netadapter", "get-netadapter", "enable-netadapter",
    "disable-netadapter", "get-wmiobject", "get-ciminstance", "resmon",
    "chcp", "certutil", "hostname", "route", "arp", "cleanmgr"
}

# Strictly forbidden destructive commands and patterns
FORBIDDEN_COMMAND_PATTERNS: List[re.Pattern] = [
    re.compile(r"\bformat\s+[a-zA-Z]:", re.IGNORECASE),
    re.compile(r"\bdel\s+(/[a-zA-Z]\s+)*[a-zA-Z]:\\", re.IGNORECASE),
    re.compile(r"\brd\s+(/[a-zA-Z]\s+)*[a-zA-Z]:\\", re.IGNORECASE),
    re.compile(r"\brmdir\s+(/[a-zA-Z]\s+)*[a-zA-Z]:\\", re.IGNORECASE),
    re.compile(r"\breg\s+delete\s+hklm\\system", re.IGNORECASE),
    re.compile(r"\breg\s+delete\s+hklm\\software", re.IGNORECASE),
    re.compile(r"\bRemove-Item\s+-Recurse\s+[a-zA-Z]:\\", re.IGNORECASE),
    re.compile(r"\b(invoke-webrequest|iwr|curl|wget)\s+http[s]?://(?!.*(microsoft\.com|windowsupdate\.com|github\.com|nodejs\.org|python\.org))", re.IGNORECASE),
    re.compile(r"\b(Invoke-Expression|iex)\b", re.IGNORECASE),
    re.compile(r"\bshutdown\s+/[s|r|g|p]\b", re.IGNORECASE),  # Unprompted immediate shutdown
]

# Sensitive keys and data patterns to redact before sending to AI
SENSITIVE_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"(password|passwd|pwd)(\s*[:=]\s*['\"]?)([^\s\"';&]+)(['\"]?)", re.IGNORECASE), r"\1\2********\4"),
    (re.compile(r"(api[_-]?key|secret|token|bearer)(\s*[:=]\s*['\"]?)([a-zA-Z0-9_\-\.]{8,})(['\"]?)", re.IGNORECASE), r"\1\2********\4"),
    (re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE), "sk-********"),
    (re.compile(r"ghp_[a-zA-Z0-9]{20,}", re.IGNORECASE), "ghp_********"),
    (re.compile(r"xox[baprs]-[a-zA-Z0-9]{10,}", re.IGNORECASE), "xox-********"),
    (re.compile(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", re.IGNORECASE), r"user_email_redacted"),
]


class CommandSafetyEngine:
    """Validates and executes commands strictly within safety and permission boundaries."""

    @staticmethod
    def validate_command(command: str) -> Tuple[bool, str, RiskLevel]:
        """Check if a shell command is authorized, safe, and determine its risk level."""
        if not command or not command.strip():
            return False, "Empty command string.", RiskLevel.CRITICAL

        cmd_clean = command.strip()

        # 1. Check against forbidden destructive patterns
        for pattern in FORBIDDEN_COMMAND_PATTERNS:
            if pattern.search(cmd_clean):
                logger.warning(f"Forbidden command detected and blocked: {cmd_clean}")
                return False, f"Command matches forbidden safety policy: {pattern.pattern}", RiskLevel.CRITICAL

        # 2. Extract base executable name
        tokens = shlex.split(cmd_clean, posix=False) if '"' in cmd_clean else cmd_clean.split()
        if not tokens:
            return False, "Unable to parse command tokens.", RiskLevel.CRITICAL

        base_exe = tokens[0].lower().replace(".exe", "").strip('"\'')

        # If base is powershell/cmd, check the first sub-command if available
        if base_exe in ["powershell", "pwsh", "cmd"]:
            for t in tokens[1:]:
                clean_t = t.lower().replace(".exe", "").strip("-\"/")
                if clean_t in SAFE_COMMAND_ALLOWLIST or any(clean_t.startswith(cmd_prefix) for cmd_prefix in ["get-", "test-", "restart-", "start-", "stop-", "netsh", "ipconfig"]):
                    base_exe = clean_t
                    break

        # 3. Classify Risk Level
        risk = RiskLevel.LOW
        if any(w in cmd_clean.lower() for w in ["restart-netadapter", "netsh winsock reset", "netsh int ip reset", "sfc /scannow", "dism /online"]):
            risk = RiskLevel.MEDIUM
        elif any(w in cmd_clean.lower() for w in ["pnputil /delete-driver", "sc delete", "reg delete", "taskkill /f"]):
            risk = RiskLevel.HIGH
        elif any(w in cmd_clean.lower() for w in ["reg add", "set-itemproperty"]):
            risk = RiskLevel.HIGH

        return True, "Command authorized by safety policy.", risk

    @staticmethod
    def redact_sensitive_data(text: str) -> str:
        """Redact passwords, API keys, tokens, and sensitive strings from logs or AI prompts."""
        if not text:
            return ""
        result = text
        for pattern, replacement in SENSITIVE_PATTERNS:
            result = pattern.sub(replacement, result)
        return result
