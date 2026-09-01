"""Developer Environment, Toolchains, and PATH Diagnostic Engine."""
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional

from backend.core.logger import get_logger
from backend.problem_solver.models import (
    DiagnosticItem, DiagnosticReport, DiagnosticStatus, ProblemCategory
)

logger = get_logger("DevEnvDiagnostic")


class DevEnvDiagnostic:
    """Diagnoses Developer toolchains: Node.js, npm, Python, Git, VS Code, C++, and PATH environments."""

    @staticmethod
    def run_diagnostic(specific_tool: Optional[str] = None) -> DiagnosticReport:
        """Execute developer environment diagnostic."""
        items: List[DiagnosticItem] = []
        raw_evidence: Dict[str, Any] = {}
        overall_status = DiagnosticStatus.HEALTHY
        summary_points = []

        tools_to_check = [
            ("python", "Python", ["python", "--version"]),
            ("node", "Node.js", ["node", "--version"]),
            ("npm", "NPM Package Manager", ["npm", "--version"]),
            ("git", "Git Version Control", ["git", "--version"]),
            ("code", "Visual Studio Code CLI", ["code", "--version"]),
            ("gcc", "C/C++ Compiler (MinGW/GCC)", ["gcc", "--version"]),
        ]

        if specific_tool:
            clean_t = specific_tool.lower().strip()
            tools_to_check = [t for t in tools_to_check if clean_t in t[0] or clean_t in t[1].lower()] or tools_to_check

        tool_results = {}
        for key, display_name, ver_cmd in tools_to_check:
            which_path = shutil.which(key)
            version_str = None
            is_ok = False

            if which_path:
                try:
                    res = subprocess.run(ver_cmd, shell=True, capture_output=True, text=True, timeout=3)
                    if res.returncode == 0:
                        version_str = res.stdout.strip().split("\n")[0].strip()
                        is_ok = True
                    else:
                        version_str = f"Found at {which_path} but returned error: {res.stderr.strip()}"
                except Exception as e:
                    version_str = f"Execution error: {e}"

            tool_results[key] = {
                "path": which_path,
                "version": version_str,
                "ok": is_ok,
            }

            if is_ok:
                items.append(DiagnosticItem(
                    name=display_name,
                    status=DiagnosticStatus.HEALTHY,
                    value=version_str,
                    details=f"Executable path: {which_path}",
                ))
            else:
                status_val = DiagnosticStatus.WARNING if key in ["gcc", "code"] else DiagnosticStatus.PROBLEM_DETECTED
                if status_val == DiagnosticStatus.PROBLEM_DETECTED and specific_tool and key in specific_tool.lower():
                    overall_status = DiagnosticStatus.PROBLEM_DETECTED
                    summary_points.append(f"{display_name} is not installed or not in system PATH")

                items.append(DiagnosticItem(
                    name=display_name,
                    status=status_val,
                    value="Not Found in PATH" if not which_path else version_str,
                    details=f"Command '{key}' could not be located in system environment PATH.",
                ))

        raw_evidence["tools"] = tool_results

        # Check system PATH size and validity
        sys_path = os.environ.get("PATH", "")
        path_entries = sys_path.split(";")
        raw_evidence["path_count"] = len(path_entries)

        if overall_status == DiagnosticStatus.HEALTHY:
            summary = "Developer toolchains, Node.js, Python, and Git environments are correctly configured."
        else:
            summary = f"Developer environment notice: {'; '.join(summary_points)}."

        return DiagnosticReport(
            category=ProblemCategory.DEV_ENVIRONMENT,
            overall_status=overall_status,
            summary=summary,
            items=items,
            raw_evidence=raw_evidence,
            suggested_focus="dev_tool_missing" if summary_points else None,
        )
