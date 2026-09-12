"""Authoritative Single YouTube Browser Session via Chrome DevTools Protocol (CDP).

Maintains a single persistent connection to Google Chrome over CDP (default port 9222),
discovers active YouTube tabs, reuses the same tab to avoid duplicate windows,
and provides direct DOM evaluation and semantic navigation.
"""
import asyncio
import os
import re
from typing import Any, Dict, List, Optional
import urllib.request
import json

from backend.core.logger import get_logger

logger = get_logger("YouTubeBrowserSession")

DEFAULT_CDP_URL = os.environ.get("CHROME_CDP_URL", "http://127.0.0.1:9222")


import threading
import time
import socket
import concurrent.futures
from urllib.parse import urlparse

class YouTubeBrowserSession:
    """Single authoritative browser session controller for YouTube over CDP."""

    def __init__(self, cdp_url: Optional[str] = None):
        self.cdp_url = cdp_url or DEFAULT_CDP_URL
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        self._page_id = None
        self._lock = None
        self._last_cdp_check: float = 0.0
        self._cdp_cached_status: bool = False

        # Dedicated persistent background event loop thread for all Playwright operations
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, name="BrowserSessionLoop", daemon=True)
        self._thread.start()

    def _run_loop(self) -> None:
        """Run dedicated event loop continuously on background worker thread."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def is_cdp_available(self) -> bool:
        """Fast non-blocking check with caching if Chrome CDP port is responding."""
        now = time.time()
        if now - self._last_cdp_check < 2.0:
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
        """Connect or reconnect to Chrome over CDP and discover/track the YouTube tab."""
        async with self._get_lock():
            # If already connected and active page is open, verify connection
            if self._browser is not None and self._page is not None:
                try:
                    if not self._page.is_closed():
                        return True
                except Exception:
                    pass
                # Reset stale page reference
                self._page = None

            if not self.is_cdp_available():
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
                    # Reuse existing blank/generic tab rather than spawning new tab
                    self._page = pages[0]
                else:
                    self._page = await self._context.new_page()

                try:
                    self._page_id = await self._page.evaluate("() => window.__jarvis_tab_id || (window.__jarvis_tab_id = 'tab_' + Date.now())")
                except Exception:
                    self._page_id = "tab_main"

                logger.info(f"Connected to YouTube browser page: {self._page.url} [id={self._page_id}]")
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

    async def navigate_same_tab(self, url: str, wait_until: str = "domcontentloaded") -> bool:
        """Navigate the currently controlled YouTube tab without opening duplicate tabs."""
        page = await self.get_page()
        if not page:
            return False
        try:
            logger.info(f"Reusing existing tab for navigation: {url}")
            await page.goto(url, wait_until=wait_until, timeout=12000)
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

    async def click_selector(self, selector: str) -> bool:
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

    async def close(self) -> None:
        """Detach from CDP session without terminating the user's Chrome."""
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
                self._page_id = None

    # ── Synchronous Bridge Methods ──────────────────────────────────────────

    def execute_async_safe(self, coro):
        """Run an async coroutine safely on the dedicated persistent event loop thread."""
        if hasattr(self, "_thread") and threading.current_thread() == self._thread:
            raise RuntimeError("execute_async_safe cannot be called from within the dedicated BrowserSessionLoop thread")
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

    def navigate_same_tab_sync(self, url: str) -> bool:
        """Synchronous helper for same-tab navigation."""
        try:
            return bool(self.execute_async_safe(self.navigate_same_tab(url)))
        except Exception as exc:
            logger.debug(f"navigate_same_tab_sync exception: {exc}")
            return False

    def evaluate_sync(self, script: str, *args) -> Any:
        """Synchronous helper for evaluating script."""
        try:
            return self.execute_async_safe(self.evaluate(script, *args))
        except Exception as exc:
            logger.debug(f"evaluate_sync exception: {exc}")
            return None

    def evaluate_script_sync(self, script: str, *args) -> Any:
        """Alias for evaluate_sync."""
        return self.evaluate_sync(script, *args)


# Global singleton instance
browser_session = YouTubeBrowserSession()
