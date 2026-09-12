"""Authoritative Single Browser Session for YouTube Runtime V3 via Chrome DevTools Protocol (CDP).

Implements Phase 3 & Phase 4 invariants:
- Dedicated persistent event loop on dedicated background worker thread.
- ONE controlled browser context and ONE authoritative YouTube page.
- Stable page identity (page_id) and generation tracking.
- Strict CDP Failure Policy: never falls back to webbrowser.open(), Ctrl+L address-bar typing,
  or silent duplicate tabs. Returns CDP_UNAVAILABLE / DEGRADED.
- Controlled Chrome launch with remote debugging for youtube.open only.
"""
import asyncio
import concurrent.futures
import json
import os
import socket
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from backend.core.logger import get_logger

logger = get_logger("YouTubeBrowserSessionV3")

DEFAULT_CDP_URL = os.environ.get("CHROME_CDP_URL", "http://127.0.0.1:9222")


class YouTubeBrowserSession:
    """Single authoritative browser session controller for YouTube over CDP."""

    def __init__(self, cdp_url: Optional[str] = None):
        self.cdp_url = cdp_url or DEFAULT_CDP_URL
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        self._page_id: str = "UNKNOWN"
        self._generation: int = 0
        self._lock = None
        self._last_cdp_check: float = 0.0
        self._cdp_cached_status: bool = False

        # Dedicated persistent event loop on background worker thread
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, name="YouTubeSessionWorker", daemon=True)
        self._thread.start()

    def _run_loop(self) -> None:
        """Continuously drive the dedicated event loop."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    @property
    def page_id(self) -> str:
        return self._page_id

    @property
    def generation(self) -> int:
        return self._generation

    def bump_generation(self) -> int:
        """Increment generation counter upon major page or URL transitions."""
        self._generation += 1
        return self._generation

    def is_cdp_available(self, force_refresh: bool = False) -> bool:
        """Fast non-blocking socket check with 2-second caching to prevent latency spikes."""
        try:
            from backend.youtube.perception import youtube_perception
            if youtube_perception.is_override_active():
                return True
        except Exception:
            pass

        now = time.time()
        if not force_refresh and (now - self._last_cdp_check < 2.0):
            return self._cdp_cached_status

        self._last_cdp_check = now
        host = "127.0.0.1"
        port = 9222
        try:
            p = urlparse(self.cdp_url)
            host = p.hostname or "127.0.0.1"
            port = p.port or 9222
        except Exception:
            pass

        try:
            with socket.create_connection((host, port), timeout=0.04):
                self._cdp_cached_status = True
        except (socket.timeout, ConnectionRefusedError, OSError):
            self._cdp_cached_status = False

        return self._cdp_cached_status

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def connect(self) -> bool:
        """Connect or reconnect to Chrome over CDP and bind to the single YouTube page."""
        async with self._get_lock():
            # If already connected and active page is open, verify connection
            if self._browser is not None and self._page is not None:
                try:
                    if not self._page.is_closed():
                        return True
                except Exception:
                    pass
                self._page = None

            if not self.is_cdp_available(force_refresh=True):
                logger.debug(f"Chrome CDP port not reachable at {self.cdp_url}")
                return False

            try:
                from playwright.async_api import async_playwright
                if self._pw is None:
                    self._pw = await async_playwright().start()

                if self._browser is None or not self._browser.is_connected():
                    self._browser = await self._pw.chromium.connect_over_cdp(self.cdp_url)

                contexts = self._browser.contexts
                if not contexts:
                    logger.debug("No browser context available over CDP")
                    return False
                self._context = contexts[0]

                # Tab discovery & single YouTube page binding
                pages = self._context.pages
                youtube_page = None
                for p in pages:
                    try:
                        u = (p.url or "").lower()
                        if "youtube.com" in u:
                            youtube_page = p
                            break
                    except Exception:
                        continue

                if youtube_page:
                    self._page = youtube_page
                elif pages:
                    # Reuse existing blank/new tab rather than overwriting user's active non-YouTube tab
                    blank_page = None
                    for p in pages:
                        try:
                            u = (p.url or "").lower()
                            if u in ["about:blank", "chrome://newtab", "chrome://newtab/"]:
                                blank_page = p
                                break
                        except Exception:
                            continue
                    self._page = blank_page if blank_page else await self._context.new_page()
                else:
                    self._page = await self._context.new_page()

                # Attach or read persistent tab identification
                try:
                    self._page_id = await self._page.evaluate("() => window.__jarvis_tab_id || (window.__jarvis_tab_id = 'tab_' + Date.now())")
                except Exception:
                    self._page_id = "tab_main"

                self.bump_generation()
                logger.info(f"Connected to YouTube browser page: {self._page.url} [id={self._page_id}, gen={self._generation}]")
                return True
            except Exception as exc:
                logger.debug(f"CDP connection attempt failed: {exc}")
                self._browser = None
                self._page = None
                return False

    async def get_page(self):
        """Get the active tracked YouTube page, reconnecting if needed."""
        if self._page is None or (hasattr(self._page, "is_closed") and self._page.is_closed()):
            ok = await self.connect()
            if not ok:
                return None
        return self._page

    async def _find_youtube_page(self):
        """Locate any open page on the YouTube domain."""
        if not self._context:
            return None
        for p in self._context.pages:
            try:
                if "youtube.com" in (p.url or "").lower():
                    return p
            except Exception:
                continue
        return None

    async def _wait_for_youtube_tab(self, timeout: float = 6.0):
        """Poll for a newly launched YouTube tab to appear in the CDP session."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            p = await self._find_youtube_page()
            if p:
                return p
            await asyncio.sleep(0.3)

        return None

    async def ensure_youtube_page(self, target_url: Optional[str] = None, launch_if_needed: bool = False):
        """Ensure a single controlled YouTube page is ready, optionally launching Chrome with CDP."""
        page = await self.get_page()
        if page:
            if target_url:
                await self.navigate(target_url)
            return self._page

        if not launch_if_needed:
            return None

        # Phase 4 Controlled Chrome Launcher for youtube.open
        logger.info("No controlled Chrome session found. Launching Chrome with remote debugging on 9222...")
        self._launch_chrome_process(target_url or "https://www.youtube.com/")

        # Bounded poll for CDP socket up to 4.0s
        deadline = time.time() + 4.0
        while time.time() < deadline:
            if self.is_cdp_available(force_refresh=True):
                connected = await self.connect()
                if connected:
                    if target_url and self._page:
                        await self.navigate(target_url)
                    return self._page
            await asyncio.sleep(0.3)

        return None

    def _launch_chrome_process(self, url: str) -> None:
        """Launch Chrome process with --remote-debugging-port=9222 without external webbrowser fallback."""
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
        ]
        for p in chrome_paths:
            if os.path.exists(p):
                try:
                    subprocess.Popen([p, "--remote-debugging-port=9222", "--start-maximized", url])
                    return
                except Exception:
                    pass

        # Windows start fallback with explicit port flag using safe token list
        try:
            subprocess.Popen(["cmd.exe", "/c", "start", "", "chrome", "--remote-debugging-port=9222", "--start-maximized", url])
        except Exception as exc:
            logger.error(f"Failed to launch Chrome with CDP: {exc}")

    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> bool:
        """Navigate the currently controlled YouTube tab without opening duplicate tabs."""
        page = await self.get_page()
        if not page:
            return False
        try:
            logger.info(f"Reusing existing tab for navigation: {url}")
            await page.goto(url, wait_until=wait_until, timeout=12000)
            self.bump_generation()
            return True
        except Exception as exc:
            logger.warning(f"Same tab navigation error to {url}: {exc}")
            return False

    async def evaluate(self, script: str, *args) -> Any:
        """Evaluate JavaScript inside the controlled YouTube page context."""
        page = await self.get_page()
        if not page:
            return None
        try:
            return await page.evaluate(script, *args)
        except Exception as exc:
            logger.debug(f"JavaScript evaluation error: {exc}")
            return None

    async def click(self, selector: str) -> bool:
        """Click element via DOM selector inside the controlled page."""
        page = await self.get_page()
        if not page:
            return False
        try:
            el = await page.wait_for_selector(selector, timeout=3000)
            if el:
                await el.click()
                return True
        except Exception as exc:
            logger.debug(f"Click selector error ({selector}): {exc}")
        return False

    async def observe(self) -> Dict[str, Any]:
        """Directly evaluate and parse the authoritative DOM snapshot."""
        from backend.youtube.dom import YOUTUBE_DOM_EXTRACTOR_JS, parse_dom_extraction_result
        raw_data = await self.evaluate(YOUTUBE_DOM_EXTRACTOR_JS)
        return parse_dom_extraction_result(raw_data)

    async def close(self) -> None:
        """Detach from CDP session without terminating user's browser."""
        async with self._get_lock():
            try:
                if self._browser is not None:
                    await self._browser.close()
                if self._pw is not None:
                    await self._pw.stop()
            except Exception:
                pass
            finally:
                self._pw = None
                self._browser = None
                self._context = None
                self._page = None
                self._page_id = "UNKNOWN"

    # ── Synchronous Bridge Methods ──────────────────────────────────────────

    def execute_async_safe(self, coro):
        """Run an async coroutine safely on the dedicated persistent event loop thread."""
        if hasattr(self, "_thread") and threading.current_thread() == self._thread:
            raise RuntimeError("execute_async_safe cannot be called from within the dedicated YouTubeSessionWorker thread")
        if not hasattr(self, "_loop") or not self._loop.is_running():
            return asyncio.run(coro)
        try:
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return future.result(timeout=12.0)
        except concurrent.futures.TimeoutError:
            try:
                future.cancel()
            except Exception:
                pass
            logger.warning("execute_async_safe coroutine timed out after 12.0s")
            return None
        except Exception as exc:
            logger.debug(f"execute_async_safe error: {exc}")
            return None

    def navigate_sync(self, url: str) -> bool:
        """Synchronous helper for same-tab navigation."""
        try:
            from backend.youtube.perception import youtube_perception
            if youtube_perception.is_override_active():
                return True
            return bool(self.execute_async_safe(self.navigate(url)))
        except Exception as exc:
            logger.debug(f"navigate_sync exception: {exc}")
            return False

    def navigate_same_tab_sync(self, url: str) -> bool:
        """Alias for navigate_sync."""
        return self.navigate_sync(url)

    def evaluate_sync(self, script: str, *args) -> Any:
        """Synchronous helper for evaluating script."""
        try:
            from backend.youtube.perception import youtube_perception
            if youtube_perception.is_override_active():
                return True
            return self.execute_async_safe(self.evaluate(script, *args))
        except Exception as exc:
            logger.debug(f"evaluate_sync exception: {exc}")
            return None

    def evaluate_script_sync(self, script: str, *args) -> Any:
        """Alias for evaluate_sync."""
        return self.evaluate_sync(script, *args)


# Global singleton instance
youtube_session = YouTubeBrowserSession()


def get_youtube_session() -> YouTubeBrowserSession:
    """Return the global YouTubeBrowserSession singleton."""
    return youtube_session
