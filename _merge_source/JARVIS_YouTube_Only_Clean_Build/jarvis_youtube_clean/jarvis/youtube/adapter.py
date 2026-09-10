from __future__ import annotations

import asyncio
from urllib.parse import quote_plus

from playwright.async_api import async_playwright

from jarvis.config import settings
from jarvis.core.models import ActionResult, Intent
from jarvis.youtube.observer import YouTubePageObserver


class YouTubeAdapter:
    def __init__(self):
        self._pw = None
        self._browser = None
        self._page = None
        self._observer = None

    async def connect(self) -> None:
        if self._browser is not None:
            return
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.connect_over_cdp(settings.cdp_url)
        contexts = self._browser.contexts
        if not contexts:
            raise RuntimeError("No Chrome context available over CDP")
        context = contexts[0]
        pages = context.pages
        youtube = next((p for p in pages if "youtube.com" in (p.url or "")), None)
        self._page = youtube or (pages[0] if pages else await context.new_page())
        self._observer = YouTubePageObserver(self._page)

    async def close(self) -> None:
        # Do not close the user's Chrome. Only detach Playwright.
        if self._pw:
            await self._pw.stop()
        self._pw = self._browser = self._page = self._observer = None

    async def context(self) -> dict:
        try:
            await self.connect()
            s = await self._observer.snapshot()
            return {"application": "youtube", **s}
        except Exception:
            return {"application": "youtube", "page_type": "UNKNOWN"}

    async def execute(self, intent: Intent) -> ActionResult:
        await self.connect()
        fn = getattr(self, f"_do_{intent.action}", None)
        if not fn:
            return ActionResult(False, "UNSUPPORTED", intent.canonical, f"Unsupported YouTube action: {intent.action}")
        try:
            return await fn(**intent.arguments)
        except Exception as exc:
            return ActionResult(False, "FAILED", intent.canonical, f"{type(exc).__name__}: {exc}")

    async def _wait_url_settle(self, old: str | None = None, timeout_ms: int = 8000) -> None:
        try:
            if old:
                await self._page.wait_for_function("old => location.href !== old", old, timeout=timeout_ms)
            else:
                await self._page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
        except Exception:
            pass
        await asyncio.sleep(0.4)

    async def _do_open(self) -> ActionResult:
        await self._page.goto("https://www.youtube.com/", wait_until="domcontentloaded")
        actual = await self._observer.snapshot()
        ok = actual["page_type"] in {"HOME", "SEARCH_RESULTS", "VIDEO", "SHORTS"}
        return ActionResult(ok, "LIVE_VERIFIED" if ok else "FAILED", "youtube.open", "YouTube opened" if ok else "YouTube page was not observed", actual=actual)

    async def _do_search(self, query: str) -> ActionResult:
        await self._page.goto(f"https://www.youtube.com/results?search_query={quote_plus(str(query))}", wait_until="domcontentloaded")
        actual = await self._observer.snapshot()
        ok = actual["page_type"] == "SEARCH_RESULTS"
        return ActionResult(ok, "LIVE_VERIFIED" if ok else "FAILED", "youtube.search", f"Search results for {query}" if ok else "Search page was not verified", expected={"query": query, "page_type": "SEARCH_RESULTS"}, actual=actual)

    async def _select_candidate(self, kind: str, ordinal: int) -> ActionResult:
        ordinal = int(ordinal or 1)
        if ordinal < 1:
            return ActionResult(False, "FAILED", f"youtube.play_{kind}", "Ordinal must be one-based and >= 1")
        candidates = await self._observer.candidates(kind)
        idx = ordinal - 1
        if idx >= len(candidates):
            return ActionResult(False, "FAILED", f"youtube.play_{kind}", f"Only {len(candidates)} visible {kind} candidates found", details={"candidate_count": len(candidates)})
        target = candidates[idx]
        expected_id = target["video_id"]
        old = self._page.url
        # Semantic identity was determined first; click exact href instead of guessed coordinates.
        href = target["href"]
        await self._page.evaluate("href => { const a=[...document.querySelectorAll('a')].find(x=>x.href===href); if(a) a.click(); else location.href=href; }", href)
        await self._wait_url_settle(old)
        actual = await self._observer.snapshot()
        ok = actual.get("current_video_id") == expected_id
        return ActionResult(ok, "LIVE_VERIFIED" if ok else "FAILED", f"youtube.play_{kind}", f"Opened {kind} #{ordinal}" if ok else "Opened content identity did not match requested ordinal", expected={"video_id": expected_id, "ordinal": ordinal}, actual=actual, details={"candidate_title": target.get("title")})

    async def _do_play_short(self, ordinal: int = 1) -> ActionResult:
        return await self._select_candidate("short", ordinal)

    async def _do_play_video(self, query: str | None = None, ordinal: int = 1) -> ActionResult:
        if query:
            search = await self._do_search(query)
            if not search.success:
                return search
        return await self._select_candidate("video", ordinal)

    async def _short_nav(self, direction: str) -> ActionResult:
        before = await self._observer.snapshot()
        before_id = before.get("current_video_id")
        if before.get("page_type") != "SHORTS":
            return ActionResult(False, "FAILED", f"youtube.{direction}_short", "Current page is not a Shorts player", actual=before)
        label = "Next video" if direction == "next" else "Previous video"
        clicked = await self._page.evaluate("""
        (label) => {
          const bs=[...document.querySelectorAll('button')];
          const b=bs.find(x => (x.getAttribute('aria-label')||'').toLowerCase().includes(label.toLowerCase()));
          if (b) { b.click(); return true; }
          return false;
        }
        """, label)
        if not clicked:
            await self._page.keyboard.press("ArrowDown" if direction == "next" else "ArrowUp")
        for _ in range(20):
            await asyncio.sleep(0.2)
            after = await self._observer.snapshot()
            if after.get("current_video_id") and after.get("current_video_id") != before_id:
                return ActionResult(True, "LIVE_VERIFIED", f"youtube.{direction}_short", f"Moved to {direction} Short", expected={"video_id_change": True}, actual=after)
        after = await self._observer.snapshot()
        return ActionResult(False, "FAILED", f"youtube.{direction}_short", "Short identity did not change", expected={"video_id_change": True}, actual=after)

    async def _do_next_short(self) -> ActionResult:
        return await self._short_nav("next")

    async def _do_previous_short(self) -> ActionResult:
        return await self._short_nav("previous")

    async def _set_play_state(self, desired: str) -> ActionResult:
        before = await self._observer.snapshot()
        if before.get("playback_state") == desired:
            return ActionResult(True, "LIVE_VERIFIED", f"youtube.{desired.lower()}", f"Already {desired.lower()}", actual=before)
        await self._page.evaluate("""
        async desired => {
          const v=document.querySelector('video');
          if(!v) throw new Error('video_not_found');
          if(desired==='PLAYING') await v.play(); else v.pause();
        }
        """, desired)
        await asyncio.sleep(0.25)
        after = await self._observer.snapshot()
        ok = after.get("playback_state") == desired
        return ActionResult(ok, "LIVE_VERIFIED" if ok else "FAILED", f"youtube.{desired.lower()}", desired.title() if ok else f"Could not verify {desired}", expected={"playback_state": desired}, actual=after)

    async def _do_pause(self) -> ActionResult:
        r = await self._set_play_state("PAUSED")
        r.action = "youtube.pause"
        return r

    async def _do_resume(self) -> ActionResult:
        r = await self._set_play_state("PLAYING")
        r.action = "youtube.resume"
        return r

    async def _toggle_button_state(self, action: str, desired: bool, selector: str, state_key: str) -> ActionResult:
        before = await self._observer.snapshot()
        observed = before.get(state_key)
        if observed is desired:
            return ActionResult(True, "LIVE_VERIFIED", action, f"Already {'on' if desired else 'off'}", actual=before)
        button = self._page.locator(selector).first
        if await button.count() == 0:
            return ActionResult(False, "DEGRADED", action, "Required semantic control was not found", actual=before)
        try:
            await button.click(timeout=3000)
        except Exception:
            return ActionResult(False, "DEGRADED", action, "Semantic control exists but could not be activated", actual=before)
        await asyncio.sleep(0.3)
        after = await self._observer.snapshot()
        ok = after.get(state_key) is desired
        return ActionResult(ok, "LIVE_VERIFIED" if ok else "DEGRADED", action, "State verified" if ok else "Control executed but final state could not be verified", expected={state_key: desired}, actual=after)

    async def _do_set_fullscreen(self, enabled: bool = True) -> ActionResult:
        before = await self._observer.snapshot()
        if before.get("fullscreen") is bool(enabled):
            return ActionResult(True, "LIVE_VERIFIED", "youtube.set_fullscreen", "Fullscreen already in requested state", actual=before)
        # YouTube player fullscreen button is the user-gesture-compatible path.
        selector = '.ytp-fullscreen-button'
        return await self._toggle_button_state("youtube.set_fullscreen", bool(enabled), selector, "fullscreen")

    async def _do_set_theater_mode(self, enabled: bool = True) -> ActionResult:
        return await self._toggle_button_state("youtube.set_theater_mode", bool(enabled), '.ytp-size-button', "theater_mode")

    async def _do_set_miniplayer(self, enabled: bool = True) -> ActionResult:
        before = await self._observer.snapshot()
        if before.get("miniplayer") is bool(enabled):
            return ActionResult(True, "LIVE_VERIFIED", "youtube.set_miniplayer", "Miniplayer already in requested state", actual=before)
        if not enabled:
            # Exit by clicking close/back-to-watch when available; otherwise state is degraded.
            ok = await self._page.evaluate("""
            () => {
              const bs=[...document.querySelectorAll('button')];
              const b=bs.find(x => /(close|miniplayer)/i.test(x.getAttribute('aria-label')||'') && /close/i.test(x.getAttribute('aria-label')||''));
              if (b) { b.click(); return true; } return false;
            }
            """)
            if not ok:
                return ActionResult(False, "DEGRADED", "youtube.set_miniplayer", "Could not find a semantic miniplayer exit control", actual=before)
            await asyncio.sleep(0.3)
            after = await self._observer.snapshot()
            success = after.get("miniplayer") is False
            return ActionResult(success, "LIVE_VERIFIED" if success else "DEGRADED", "youtube.set_miniplayer", "Miniplayer disabled" if success else "Could not verify miniplayer exit", actual=after)
        return await self._toggle_button_state("youtube.set_miniplayer", True, '.ytp-miniplayer-button', "miniplayer")

    async def _do_set_captions(self, enabled: bool = True) -> ActionResult:
        return await self._toggle_button_state("youtube.set_captions", bool(enabled), '.ytp-subtitles-button', "captions")

    async def _do_set_playback_speed(self, rate: float) -> ActionResult:
        target = max(0.25, min(2.0, float(rate)))
        await self._page.evaluate("r => { const v=document.querySelector('video'); if(!v) throw new Error('video_not_found'); v.playbackRate=r; }", target)
        await asyncio.sleep(0.15)
        after = await self._observer.snapshot()
        ok = after.get("playback_rate") is not None and abs(float(after["playback_rate"]) - target) <= 0.01
        return ActionResult(ok, "LIVE_VERIFIED" if ok else "FAILED", "youtube.set_playback_speed", f"Speed set to {target}x" if ok else "Playback speed could not be verified", expected={"playback_rate": target}, actual=after)

    async def _do_speed_up(self, step: float = 0.25) -> ActionResult:
        s = await self._observer.snapshot()
        if s.get("playback_rate") is None:
            return ActionResult(False, "FAILED", "youtube.speed_up", "No active video state")
        return await self._do_set_playback_speed(float(s["playback_rate"]) + float(step))

    async def _do_speed_down(self, step: float = 0.25) -> ActionResult:
        s = await self._observer.snapshot()
        if s.get("playback_rate") is None:
            return ActionResult(False, "FAILED", "youtube.speed_down", "No active video state")
        return await self._do_set_playback_speed(float(s["playback_rate"]) - float(step))

    async def _seek_to(self, target: float, action: str) -> ActionResult:
        target = max(0.0, float(target))
        await self._page.evaluate("t => { const v=document.querySelector('video'); if(!v) throw new Error('video_not_found'); v.currentTime=Math.min(t, Number.isFinite(v.duration)?v.duration:t); }", target)
        await asyncio.sleep(0.25)
        after = await self._observer.snapshot()
        actual = after.get("current_time")
        ok = actual is not None and abs(float(actual) - target) <= 2.5
        return ActionResult(ok, "LIVE_VERIFIED" if ok else "DEGRADED", action, f"Seeked to {target:.0f}s" if ok else "Seek executed but exact time could not be verified", expected={"current_time": target}, actual=after)

    async def _do_seek_timestamp(self, seconds: float) -> ActionResult:
        return await self._seek_to(seconds, "youtube.seek_timestamp")

    async def _do_seek_forward(self, seconds: float = 10) -> ActionResult:
        before = await self._observer.snapshot()
        if before.get("current_time") is None:
            return ActionResult(False, "FAILED", "youtube.seek_forward", "No active video time")
        return await self._seek_to(float(before["current_time"]) + float(seconds), "youtube.seek_forward")

    async def _do_seek_backward(self, seconds: float = 10) -> ActionResult:
        before = await self._observer.snapshot()
        if before.get("current_time") is None:
            return ActionResult(False, "FAILED", "youtube.seek_backward", "No active video time")
        return await self._seek_to(max(0, float(before["current_time"]) - float(seconds)), "youtube.seek_backward")

    async def _do_set_volume(self, level: int) -> ActionResult:
        level = max(0, min(100, int(level)))
        await self._page.evaluate("l => { const v=document.querySelector('video'); if(!v) throw new Error('video_not_found'); v.volume=l/100; if(l>0) v.muted=false; }", level)
        await asyncio.sleep(0.15)
        after = await self._observer.snapshot()
        ok = after.get("volume") is not None and abs(int(after["volume"]) - level) <= 1
        return ActionResult(ok, "LIVE_VERIFIED" if ok else "FAILED", "youtube.set_volume", f"YouTube volume {level}%" if ok else "Volume could not be verified", expected={"volume": level}, actual=after)

    async def _do_volume_up(self, step: int = 10) -> ActionResult:
        s = await self._observer.snapshot()
        if s.get("volume") is None:
            return ActionResult(False, "FAILED", "youtube.volume_up", "No active video volume")
        return await self._do_set_volume(int(s["volume"]) + int(step))

    async def _do_volume_down(self, step: int = 10) -> ActionResult:
        s = await self._observer.snapshot()
        if s.get("volume") is None:
            return ActionResult(False, "FAILED", "youtube.volume_down", "No active video volume")
        return await self._do_set_volume(int(s["volume"]) - int(step))

    async def _set_muted(self, desired: bool, action: str) -> ActionResult:
        before = await self._observer.snapshot()
        if before.get("muted") is desired:
            return ActionResult(True, "LIVE_VERIFIED", action, "Already in requested mute state", actual=before)
        await self._page.evaluate("m => { const v=document.querySelector('video'); if(!v) throw new Error('video_not_found'); v.muted=m; }", desired)
        await asyncio.sleep(0.15)
        after = await self._observer.snapshot()
        ok = after.get("muted") is desired
        return ActionResult(ok, "LIVE_VERIFIED" if ok else "FAILED", action, "Mute state verified" if ok else "Mute state not verified", expected={"muted": desired}, actual=after)

    async def _do_mute(self) -> ActionResult:
        return await self._set_muted(True, "youtube.mute")

    async def _do_unmute(self) -> ActionResult:
        return await self._set_muted(False, "youtube.unmute")

    async def _do_set_like(self, enabled: bool = True) -> ActionResult:
        desired = bool(enabled)
        before = await self._observer.like_state()
        if before is desired:
            snap = await self._observer.snapshot()
            return ActionResult(True, "LIVE_VERIFIED", "youtube.set_like", "Like state already correct", actual={**snap, "liked": before})
        if before is None:
            return ActionResult(False, "DEGRADED", "youtube.set_like", "Like state/control is not semantically observable on this layout or account")
        clicked = await self._page.evaluate("""
        () => {
          const bs=[...document.querySelectorAll('button, yt-button-shape button')];
          const b=bs.find(x => {
            const a=(x.getAttribute('aria-label')||'').toLowerCase();
            const t=(x.getAttribute('title')||'').toLowerCase();
            return a.startsWith('like') || t==='i like this';
          });
          if(b){ b.click(); return true; }
          return false;
        }
        """)
        if not clicked:
            return ActionResult(False, "DEGRADED", "youtube.set_like", "Like button was not found")
        await asyncio.sleep(0.6)
        after_like = await self._observer.like_state()
        snap = await self._observer.snapshot()
        ok = after_like is desired
        return ActionResult(ok, "LIVE_VERIFIED" if ok else "DEGRADED", "youtube.set_like", "Like state verified" if ok else "Like click occurred but final state was not verified", expected={"liked": desired}, actual={**snap, "liked": after_like})

    async def _do_replay(self) -> ActionResult:
        await self._page.evaluate("async () => { const v=document.querySelector('video'); if(!v) throw new Error('video_not_found'); v.currentTime=0; await v.play(); }")
        await asyncio.sleep(0.25)
        after = await self._observer.snapshot()
        ok = after.get("current_time") is not None and float(after["current_time"]) <= 2.5
        return ActionResult(ok, "LIVE_VERIFIED" if ok else "FAILED", "youtube.replay", "Replayed from start" if ok else "Replay could not be verified", expected={"current_time": 0}, actual=after)
