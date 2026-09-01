"""Playwright Browser Instrumentation and Trace Manager for JARVIS.

Captures action timelines, DOM snapshots, network requests, console errors,
and saves Playwright Trace Viewer zip archives on developer debug runs or failures.
"""
import asyncio
from datetime import datetime
import os
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.core.logger import get_logger

logger = get_logger("PlaywrightTracer")


class BrowserActionReport(BaseModel):
    """Detailed diagnostic report of a single browser automation action."""
    action_name: str
    target_locator: Optional[str] = None
    url_before: str = ""
    url_after: str = ""
    dom_snapshot_before: Optional[str] = None
    dom_snapshot_after: Optional[str] = None
    screenshot_path: Optional[str] = None
    trace_zip_path: Optional[str] = None
    console_errors: List[str] = Field(default_factory=list)
    network_requests: List[Dict[str, Any]] = Field(default_factory=list)
    duration_ms: float = 0.0
    status: str = "SUCCESS"  # SUCCESS, FAILED, TIMEOUT
    error: Optional[str] = None


class PlaywrightTraceManager:
    """Singleton manager for capturing Playwright browser execution traces."""

    def __init__(self, trace_dir: Optional[str] = None):
        self.trace_dir = Path(trace_dir or os.path.join(os.path.dirname(__file__), "..", "..", "logs", "observability", "playwright_traces")).resolve()
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._current_trace_file: Optional[Path] = None

    def create_trace_path(self, prefix: str = "trace") -> Path:
        """Generate timestamped path for trace zip archive."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{ts}.zip"
        return self.trace_dir / filename

    async def execute_with_trace(
        self,
        action_name: str,
        target_url: str,
        action_coro,
        locator_desc: Optional[str] = None,
        prefix: str = "trace",
    ) -> BrowserActionReport:
        """Execute a browser action inside an isolated Playwright context with full tracing."""
        from playwright.async_api import async_playwright

        start_t = time.time()
        report = BrowserActionReport(
            action_name=action_name,
            target_locator=locator_desc,
        )

        trace_path = self.create_trace_path(prefix)
        screenshot_path = self.trace_dir / f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context(viewport={"width": 1366, "height": 768})

                # Start comprehensive Playwright Tracing
                await context.tracing.start(screenshots=True, snapshots=True, sources=True)

                page = await context.new_page()

                # Listen to console errors
                page.on("console", lambda msg: report.console_errors.append(f"[{msg.type}] {msg.text}") if msg.type in ["error", "warning"] else None)

                # Listen to network requests
                page.on("requestfailed", lambda req: report.network_requests.append({
                    "url": req.url,
                    "failure": req.failure,
                    "method": req.method,
                }))

                if target_url:
                    await page.goto(target_url, wait_until="domcontentloaded", timeout=15000)
                
                report.url_before = page.url
                report.dom_snapshot_before = (await page.content())[:2000]

                # Execute action
                res = await action_coro(page)

                report.url_after = page.url
                report.dom_snapshot_after = (await page.content())[:2000]
                await page.screenshot(path=str(screenshot_path))
                report.screenshot_path = str(screenshot_path)

                # Stop and export Playwright trace archive
                await context.tracing.stop(path=str(trace_path))
                report.trace_zip_path = str(trace_path)
                report.status = "SUCCESS"

                await context.close()
                await browser.close()

        except Exception as exc:
            report.status = "FAILED"
            report.error = str(exc)
            logger.error(f"Playwright trace execution failed for '{action_name}': {exc}")
            # Try to stop tracing even on error if possible
            try:
                if 'context' in locals():
                    await context.tracing.stop(path=str(trace_path))
                    report.trace_zip_path = str(trace_path)
            except Exception:
                pass

        finally:
            report.duration_ms = round((time.time() - start_t) * 1000, 2)

        return report

    def get_recent_traces(self, limit: int = 5) -> List[Path]:
        """Return list of recently saved Playwright trace zip files."""
        files = sorted(self.trace_dir.glob("*.zip"), key=os.path.getmtime, reverse=True)
        return files[:limit]


# Global Singleton Playwright Tracer
playwright_tracer = PlaywrightTraceManager()
