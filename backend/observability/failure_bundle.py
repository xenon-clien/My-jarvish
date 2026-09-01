"""Diagnostic Failure Bundle Generator for JARVIS.

When a command or verification fails, automatically creates an empirical diagnostic
archive containing DOM snapshots, screenshots, error stacks, and traces.
"""
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import traceback
from typing import Any, Dict, Optional
from rich.console import Console

from backend.core.logger import get_logger
from backend.observability.command_tracer import command_tracer, CommandTrace

logger = get_logger("FailureBundleManager")
console = Console()


class FailureBundleManager:
    """Singleton manager for creating self-contained diagnostic failure bundles."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or os.path.join(os.path.dirname(__file__), "..", "..", "logs", "observability", "failures")).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_failure_bundle(
        self,
        command_id: str,
        error_message: str,
        exception: Optional[Exception] = None,
        screenshot_path: Optional[str] = None,
        playwright_trace_path: Optional[str] = None,
        active_url: Optional[str] = None,
        active_window: Optional[str] = None,
        locator_used: Optional[str] = None,
        verification_details: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Create a complete diagnostic bundle directory with all empirical evidence."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bundle_name = f"BUNDLE_{command_id}_{ts}"
        bundle_dir = self.base_dir / bundle_name
        bundle_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"📦 Generating Failure Bundle at: {bundle_dir}")

        # 1. Save Command Trace JSON
        trace = command_tracer.get_trace(command_id)
        trace_data = trace.model_dump() if trace else {"command_id": command_id, "error": error_message}
        with open(bundle_dir / "command_trace.json", "w", encoding="utf-8") as f:
            json.dump(trace_data, f, indent=2)

        # 2. Save Error Stack Text
        stack_text = traceback.format_exc() if exception else error_message
        with open(bundle_dir / "error_stack.txt", "w", encoding="utf-8") as f:
            f.write(f"ERROR: {error_message}\n\nSTACK TRACE:\n{stack_text}\n")

        # 3. Save Active State Details
        state_data = {
            "timestamp": datetime.now().isoformat(),
            "command_id": command_id,
            "active_url": active_url,
            "active_window": active_window,
            "locator_used": locator_used,
        }
        with open(bundle_dir / "active_state.json", "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)

        # 4. Save Verification Report
        if verification_details:
            with open(bundle_dir / "verification_report.json", "w", encoding="utf-8") as f:
                json.dump(verification_details, f, indent=2)

        # 5. Copy Screenshot & Playwright Trace if available
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                shutil.copy2(screenshot_path, bundle_dir / "page_screenshot.png")
            except Exception:
                pass

        if playwright_trace_path and os.path.exists(playwright_trace_path):
            try:
                shutil.copy2(playwright_trace_path, bundle_dir / "playwright_trace.zip")
            except Exception:
                pass

        # Print Developer Diagnostics Banner
        console.print(f"\n[bold red]❌ FAILURE BUNDLE GENERATED:[/bold red] {bundle_dir}")
        console.print("[bold yellow]⚠️ ROOT CAUSE NOT YET CONFIRMED[/bold yellow] (Run reproducer script to isolate empirical subsystem)\n")

        return bundle_dir


# Global Singleton Failure Bundle Manager
failure_bundle_manager = FailureBundleManager()
