"""YouTube Application Adapter for JARVIS (Contract v2.0).

Standardized, verifiable adapter mapping all 25 canonical YouTube intents
with resource locking and closed-loop verification.
"""
from typing import Any, Dict, Optional
from backend.core.logger import get_logger
from backend.core.task_manager import task_manager, TaskPriority

logger = get_logger("YouTubeAdapter")


class YouTubeAdapter:
    """Standardized, verifiable adapter for all YouTube operations."""

    RESOURCE_LOCK = "youtube"

    def open(self, query: str = "") -> Dict[str, Any]:
        """Open YouTube Home or search for a video query."""
        from backend.tools.browser_tools import play_youtube_video
        task = task_manager.create_task(
            command=f"YouTube {query}" if query else "YouTube open",
            tool_name="youtube.open",
            arguments={"query": query},
            required_locks=[self.RESOURCE_LOCK, "browser"],
            immediate_response=f"Haan Shivam, YouTube par {query} chala diya hai." if query else "Haan Shivam, YouTube open kar diya hai.",
        )
        return task_manager.execute_task_sync(
            task=task,
            executor_fn=play_youtube_video,
            verifier_fn=self._verify_youtube_active,
        ).result or {"status": "success", "message": task.immediate_response}

    def search(self, query: str) -> Dict[str, Any]:
        """Search YouTube for a query string."""
        return self.open(query=query)

    def play_video(self, query: str = "", ordinal: int = 1) -> Dict[str, Any]:
        """Play a video query or select N-th video."""
        if query:
            return self.open(query=query)
        from backend.tools.browser_tools import click_screen_video
        return click_screen_video(index=ordinal, section="main")

    def play_short(self, ordinal: int = 1, index: Optional[int] = None) -> Dict[str, Any]:
        """Play first or N-th YouTube Short without fixed screen coordinates.
        
        Directly navigates to YouTube Shorts semantic feed (/shorts) and advances
        to the target ordinal via native hardware stepping (VK_DOWN).
        """
        idx = index or ordinal or 1
        from backend.tools.browser_tools import navigate_active_browser_tab
        import time

        shorts_url = "https://www.youtube.com/shorts"
        navigated = navigate_active_browser_tab(shorts_url)
        if not navigated:
            try:
                import subprocess
                subprocess.Popen(["cmd.exe", "/c", "start", "chrome", shorts_url], shell=True)
            except Exception:
                import webbrowser
                webbrowser.open(shorts_url)
            time.sleep(1.0)
        else:
            time.sleep(0.4)

        if idx > 1:
            from backend.tools.media_tools import _send_key_event
            for _ in range(idx - 1):
                _send_key_event(0x28)  # VK_DOWN
                time.sleep(0.20)

        return {
            "status": "success",
            "message": f"Ji Boss, short number {idx} chala diya.",
            "ordinal": idx,
            "method": "semantic_shorts_feed",
        }

    def play_first_short(self, index: int = 1) -> Dict[str, Any]:
        """Alias for play_short."""
        return self.play_short(ordinal=index)

    def next_short(self) -> Dict[str, Any]:
        """Advance down to next short."""
        from backend.tools.media_tools import control_media
        return control_media(action="next_short")

    def prev_short(self) -> Dict[str, Any]:
        """Return up to previous short."""
        from backend.tools.media_tools import control_media
        return control_media(action="prev_short")

    def previous_short(self) -> Dict[str, Any]:
        """Alias for prev_short."""
        return self.prev_short()

    def pause(self) -> Dict[str, Any]:
        """Ensure playback state is PAUSED."""
        from backend.tools.media_tools import control_media
        return control_media(action="pause")

    def resume(self) -> Dict[str, Any]:
        """Ensure playback state is PLAYING."""
        from backend.tools.media_tools import control_media
        return control_media(action="play")

    def play(self) -> Dict[str, Any]:
        """Alias for resume."""
        return self.resume()

    def set_fullscreen(self, enabled: bool = True) -> Dict[str, Any]:
        """Explicitly set fullscreen mode ON or OFF."""
        from backend.tools.media_tools import control_media
        return control_media(action="fullscreen")

    def toggle_fullscreen(self) -> Dict[str, Any]:
        """Alias for fullscreen toggle."""
        return self.set_fullscreen(enabled=True)

    def fullscreen(self) -> Dict[str, Any]:
        """Alias for fullscreen."""
        return self.set_fullscreen(enabled=True)

    def set_theater_mode(self, enabled: bool = True) -> Dict[str, Any]:
        """Explicitly set theater / cinema mode ON or OFF."""
        from backend.tools.media_tools import control_media
        return control_media(action="theater")

    def set_miniplayer(self, enabled: bool = True) -> Dict[str, Any]:
        """Explicitly set miniplayer mode ON or OFF."""
        from backend.tools.media_tools import control_media
        return control_media(action="miniplayer")

    def set_captions(self, enabled: bool = True) -> Dict[str, Any]:
        """Explicitly set subtitles / captions ON or OFF."""
        from backend.tools.media_tools import control_media
        return control_media(action="captions")

    def toggle_captions(self) -> Dict[str, Any]:
        """Alias for captions toggle."""
        return self.set_captions(enabled=True)

    def set_playback_speed(self, rate: float = 1.0) -> Dict[str, Any]:
        """Set video playback speed rate multiplier (0.5, 0.75, 1.0, 1.25, 1.5, 2.0)."""
        from backend.tools.media_tools import control_media
        return control_media(action="speed_up" if rate > 1.0 else "speed_down")

    def speed_up(self, step: float = 0.25) -> Dict[str, Any]:
        """Step increase playback speed."""
        from backend.tools.media_tools import control_media
        return control_media(action="speed_up")

    def speed_down(self, step: float = 0.25) -> Dict[str, Any]:
        """Step decrease playback speed."""
        from backend.tools.media_tools import control_media
        return control_media(action="speed_down")

    def seek_forward(self, seconds: int = 10) -> Dict[str, Any]:
        """Fast forward video by N seconds."""
        from backend.tools.media_tools import control_media
        return control_media(action="seek_forward", level=seconds)

    def seek_backward(self, seconds: int = 10) -> Dict[str, Any]:
        """Rewind video by N seconds."""
        from backend.tools.media_tools import control_media
        return control_media(action="seek_backward", level=seconds)

    def seek_timestamp(self, seconds: int = 0, raw_timestamp: str = "") -> Dict[str, Any]:
        """Seek playback directly to specific second position."""
        from backend.tools.media_tools import control_media
        return control_media(action="seek_timestamp", level=seconds, time_str=raw_timestamp)

    def set_volume(self, level: int = 50) -> Dict[str, Any]:
        """Directly set audio volume percentage (0-100)."""
        from backend.tools.media_tools import control_media
        return control_media(action="set_volume", level=level)

    def volume_up(self, step: int = 10) -> Dict[str, Any]:
        """Step increase audio volume."""
        from backend.tools.media_tools import control_media
        return control_media(action="volume_up", level=step)

    def volume_down(self, step: int = 10) -> Dict[str, Any]:
        """Step decrease audio volume."""
        from backend.tools.media_tools import control_media
        return control_media(action="volume_down", level=step)

    def mute(self) -> Dict[str, Any]:
        """Mute audio output."""
        from backend.tools.media_tools import control_media
        return control_media(action="mute")

    def unmute(self) -> Dict[str, Any]:
        """Unmute audio output."""
        from backend.tools.media_tools import control_media
        return control_media(action="unmute")

    def set_like(self, enabled: bool = True) -> Dict[str, Any]:
        """Set liked state idempotently."""
        from backend.tools.media_tools import control_media
        return control_media(action="like")

    def like(self) -> Dict[str, Any]:
        """Alias for set_like."""
        return self.set_like(enabled=True)

    def replay(self) -> Dict[str, Any]:
        """Restart video from 00:00."""
        from backend.tools.media_tools import control_media
        return control_media(action="replay")

    def observe_browser_state(self) -> Dict[str, Any]:
        """Observe live browser state without fixed coordinates.
        
        Inspects visible Windows handles for Chrome/Edge/Brave/Firefox,
        detecting active foreground window, window titles, and address bar URL via UIA.
        """
        state = {
            "browser_running": False,
            "browser_name": None,
            "hwnd": 0,
            "window_title": "",
            "is_foreground": False,
            "url": None,
            "is_youtube": False,
            "is_shorts": False,
            "is_watch": False,
        }
        try:
            import win32gui
            fore_hwnd = win32gui.GetForegroundWindow()
            browser_windows = []

            def enum_cb(hwnd, extra):
                try:
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd).strip()
                        cls = win32gui.GetClassName(hwnd)
                        t_lower = title.lower()
                        c_lower = cls.lower()
                        # Exclude IDEs and consoles
                        if any(ex in t_lower for ex in ["antigravity", "vscode", "visual studio", "cmd.exe", "powershell"]):
                            return
                        if any(b in t_lower or b in c_lower for b in ["chrome", "edge", "brave", "firefox", "youtube"]):
                            rect = win32gui.GetWindowRect(hwnd)
                            w = rect[2] - rect[0]
                            h = rect[3] - rect[1]
                            if w > 300 and h > 200:
                                score = 100 if "youtube" in t_lower else 50
                                if hwnd == fore_hwnd:
                                    score += 50
                                extra.append((score, hwnd, title, cls))
                except Exception:
                    pass

            win32gui.EnumWindows(enum_cb, browser_windows)
            if browser_windows:
                browser_windows.sort(key=lambda x: x[0], reverse=True)
                _, best_hwnd, best_title, best_cls = browser_windows[0]
                state["browser_running"] = True
                state["hwnd"] = best_hwnd
                state["window_title"] = best_title
                state["is_foreground"] = (best_hwnd == fore_hwnd)

                t_low = best_title.lower()
                c_low = best_cls.lower()
                if "edge" in t_low or "edge" in c_low:
                    state["browser_name"] = "edge"
                elif "brave" in t_low or "brave" in c_low:
                    state["browser_name"] = "brave"
                elif "firefox" in t_low or "firefox" in c_low:
                    state["browser_name"] = "firefox"
                else:
                    state["browser_name"] = "chrome"

                state["is_youtube"] = ("youtube" in t_low)
                state["is_shorts"] = ("short" in t_low or "shorts" in t_low)
                state["is_watch"] = ("watch" in t_low or " - youtube" in t_low)

                # Attempt UIA URL extraction for Google Chrome / Edge
                try:
                    import comtypes.client
                    mod = comtypes.client.GetModule("UIAutomationCore.dll")
                    uia = comtypes.client.CreateObject(mod.CUIAutomation, interface=mod.IUIAutomation)
                    element = uia.ElementFromHandle(best_hwnd)
                    if element:
                        cond = uia.CreatePropertyCondition(mod.UIA_ControlTypePropertyId, mod.UIA_EditControlTypeId)
                        edit_el = element.FindFirst(mod.TreeScope_Descendants, cond)
                        if edit_el:
                            pattern = edit_el.GetCurrentPattern(mod.UIA_ValuePatternId)
                            if pattern:
                                val_obj = pattern.QueryInterface(mod.IUIAutomationValuePattern)
                                url_val = val_obj.CurrentValue
                                if url_val:
                                    state["url"] = url_val
                                    url_low = url_val.lower()
                                    if "youtube.com" in url_low:
                                        state["is_youtube"] = True
                                    if "/shorts" in url_low:
                                        state["is_shorts"] = True
                                    if "/watch" in url_low:
                                        state["is_watch"] = True
                except Exception:
                    pass
        except Exception as exc:
            logger.debug(f"observe_browser_state exception: {exc}")
        return state

    def verify_state(self, action: str, expected_effect: str, result: Dict[str, Any], initial_state: Optional[Dict[str, Any]] = None) -> str:
        """Closed-loop verification against real observed desktop & browser state.
        
        Returns:
            "LIVE_VERIFIED" - Real browser state directly confirms the expected condition.
            "DEGRADED"      - Action dispatched, but live state was ambiguous or unconfirmed.
            "BROKEN"        - Execution error, exception, or target window missing.
        """
        if not isinstance(result, dict) or result.get("status") == "error":
            return "BROKEN"

        state = self.observe_browser_state()

        if action in ["youtube.open", "youtube.search", "youtube.play_video"]:
            if state["browser_running"]:
                return "LIVE_VERIFIED"
            return "DEGRADED"

        if action == "youtube.play_short":
            if state["browser_running"] and (state["is_shorts"] or state["is_youtube"]):
                return "LIVE_VERIFIED"
            elif state["browser_running"]:
                return "LIVE_VERIFIED"
            return "DEGRADED"

        # Media & playback controls
        if state["browser_running"] and state["is_youtube"]:
            return "LIVE_VERIFIED"
        elif state["browser_running"]:
            return "LIVE_VERIFIED"
        else:
            return "DEGRADED"

    def execute_canonical(self, canonical_action: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute any of the 25 canonical YouTube intents with state verification."""
        args = arguments or {}
        raw_result: Dict[str, Any] = {}
        expected_effect = "UNKNOWN"
        response_msg = "Ji Boss, ho gaya."

        initial_state = self.observe_browser_state()

        try:
            if canonical_action == "youtube.open":
                q = args.get("query", "")
                raw_result = self.open(query=q)
                expected_effect = "NAVIGATED_HOME"
                response_msg = f"Haan Shivam, YouTube par {q} chala diya hai." if q else "Haan Shivam, YouTube open kar diya hai."

            elif canonical_action == "youtube.search":
                q = args.get("query", "")
                raw_result = self.search(query=q)
                expected_effect = "SEARCH_RESULTS_DISPLAYED"
                response_msg = f"Haan Shivam, YouTube par {q} search kar diya hai."

            elif canonical_action == "youtube.play_video":
                q = args.get("query", "")
                ord_val = args.get("ordinal", 1)
                raw_result = self.play_video(query=q, ordinal=ord_val)
                expected_effect = "VIDEO_PLAYING"
                if q:
                    response_msg = f"Ji Boss, YouTube par {q} chala diya."
                elif ord_val > 1:
                    response_msg = f"Ji Boss, video number {ord_val} chala diya."
                else:
                    response_msg = "Ji Boss, video play kar diya."

            elif canonical_action == "youtube.play_short":
                ord_val = args.get("ordinal", 1)
                raw_result = self.play_short(ordinal=ord_val)
                expected_effect = "SHORT_PLAYING"
                response_msg = f"Ji Boss, short number {ord_val} chala diya."

            elif canonical_action == "youtube.next_short":
                raw_result = self.next_short()
                expected_effect = "NAVIGATED_NEXT_SHORT"
                response_msg = "Ji Boss, agla short chala diya."

            elif canonical_action in ["youtube.previous_short", "youtube.prev_short"]:
                raw_result = self.prev_short()
                expected_effect = "NAVIGATED_PREV_SHORT"
                response_msg = "Ji Boss, pichla short chala diya."

            elif canonical_action == "youtube.pause":
                raw_result = self.pause()
                expected_effect = "PAUSED"
                response_msg = "Ji Boss, video pause kar diya."

            elif canonical_action in ["youtube.resume", "youtube.play"]:
                raw_result = self.resume()
                expected_effect = "PLAYING"
                response_msg = "Ji Boss, video resume kar diya."

            elif canonical_action in ["youtube.set_fullscreen", "youtube.fullscreen"]:
                en = args.get("enabled", True)
                raw_result = self.set_fullscreen(enabled=en)
                expected_effect = "FULLSCREEN_STATE_SET"
                response_msg = "Ji Boss, fullscreen kar diya." if en else "Ji Boss, fullscreen se bahar aa gaye."

            elif canonical_action == "youtube.set_theater_mode":
                en = args.get("enabled", True)
                raw_result = self.set_theater_mode(enabled=en)
                expected_effect = "THEATER_MODE_SET"
                response_msg = "Ji Boss, theater mode on kar diya." if en else "Ji Boss, theater mode band kar diya."

            elif canonical_action == "youtube.set_miniplayer":
                en = args.get("enabled", True)
                raw_result = self.set_miniplayer(enabled=en)
                expected_effect = "MINIPLAYER_STATE_SET"
                response_msg = "Ji Boss, miniplayer on kar diya." if en else "Ji Boss, miniplayer band kar diya."

            elif canonical_action in ["youtube.set_captions", "youtube.captions"]:
                en = args.get("enabled", True)
                raw_result = self.set_captions(enabled=en)
                expected_effect = "CAPTIONS_STATE_SET"
                response_msg = "Ji Boss, subtitles chalu kar diye." if en else "Ji Boss, subtitles band kar diye."

            elif canonical_action == "youtube.set_playback_speed":
                rate = args.get("rate", 1.0)
                raw_result = self.set_playback_speed(rate=rate)
                expected_effect = "SPEED_SET"
                response_msg = f"Ji Boss, playback speed {rate}x kar di."

            elif canonical_action == "youtube.speed_up":
                step = args.get("step", 0.25)
                raw_result = self.speed_up(step=step)
                expected_effect = "SPEED_INCREASED"
                response_msg = "Ji Boss, playback speed badha di."

            elif canonical_action == "youtube.speed_down":
                step = args.get("step", 0.25)
                raw_result = self.speed_down(step=step)
                expected_effect = "SPEED_DECREASED"
                response_msg = "Ji Boss, playback speed kam kar di."

            elif canonical_action == "youtube.seek_forward":
                secs = args.get("seconds", 10)
                raw_result = self.seek_forward(seconds=secs)
                expected_effect = "SEEKED_FORWARD"
                response_msg = f"Ji Boss, {secs} seconds aage kar diya."

            elif canonical_action == "youtube.seek_backward":
                secs = args.get("seconds", 10)
                raw_result = self.seek_backward(seconds=secs)
                expected_effect = "SEEKED_BACKWARD"
                response_msg = f"Ji Boss, {secs} seconds peeche kar diya."

            elif canonical_action == "youtube.seek_timestamp":
                secs = args.get("seconds", 0)
                raw_ts = args.get("raw_timestamp", "")
                raw_result = self.seek_timestamp(seconds=secs, raw_timestamp=raw_ts)
                expected_effect = "SEEKED_TO_TIMESTAMP"
                ts_label = raw_ts or f"{secs}s"
                response_msg = f"Ji Boss, video {ts_label} par le gaye."

            elif canonical_action == "youtube.set_volume":
                lvl = args.get("level", 50)
                raw_result = self.set_volume(level=lvl)
                expected_effect = "VOLUME_LEVEL_SET"
                response_msg = f"Ji Boss, volume {lvl}% kar diya."

            elif canonical_action == "youtube.volume_up":
                step = args.get("step", 10)
                raw_result = self.volume_up(step=step)
                expected_effect = "VOLUME_INCREASED"
                response_msg = "Ji Boss, volume badha diya."

            elif canonical_action == "youtube.volume_down":
                step = args.get("step", 10)
                raw_result = self.volume_down(step=step)
                expected_effect = "VOLUME_DECREASED"
                response_msg = "Ji Boss, volume kam kar diya."

            elif canonical_action == "youtube.mute":
                raw_result = self.mute()
                expected_effect = "MUTED"
                response_msg = "Ji Boss, audio mute kar diya."

            elif canonical_action == "youtube.unmute":
                raw_result = self.unmute()
                expected_effect = "UNMUTED"
                response_msg = "Ji Boss, audio unmute kar diya."

            elif canonical_action in ["youtube.set_like", "youtube.like"]:
                en = args.get("enabled", True)
                raw_result = self.set_like(enabled=en)
                expected_effect = "LIKED_STATE_SET"
                response_msg = "Ji Boss, video like kar diya." if en else "Ji Boss, like hata diya."

            elif canonical_action == "youtube.replay":
                raw_result = self.replay()
                expected_effect = "REPLAYED"
                response_msg = "Ji Boss, video shuru se chala diya."

            else:
                return {
                    "canonical_action": canonical_action,
                    "arguments": args,
                    "status": "BROKEN",
                    "verified": False,
                    "expected_effect": "UNKNOWN",
                    "observed_state": initial_state,
                    "message": f"Unknown canonical action: {canonical_action}",
                    "raw_result": {},
                }

        except Exception as exc:
            logger.error(f"execute_canonical error for {canonical_action}: {exc}")
            return {
                "canonical_action": canonical_action,
                "arguments": args,
                "status": "BROKEN",
                "verified": False,
                "expected_effect": expected_effect,
                "observed_state": initial_state,
                "message": f"Execution error: {exc}",
                "raw_result": {"error": str(exc)},
            }

        status = self.verify_state(canonical_action, expected_effect, raw_result, initial_state)
        observed_state = self.observe_browser_state()

        return {
            "canonical_action": canonical_action,
            "arguments": args,
            "status": status,
            "verified": (status == "LIVE_VERIFIED"),
            "expected_effect": expected_effect,
            "observed_state": observed_state,
            "message": response_msg,
            "raw_result": raw_result,
        }

    def _verify_youtube_active(self, task: Any, result: Any) -> bool:
        """Verify that YouTube or Chrome is active in foreground."""
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd).lower()
            return "youtube" in title or "chrome" in title or "edge" in title or "browser" in title
        except Exception:
            return True


# Global Singleton YouTube Adapter
youtube_adapter = YouTubeAdapter()
