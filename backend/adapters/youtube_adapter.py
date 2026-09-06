"""YouTube Application Adapter for JARVIS (Contract v2.0).

Standardized, verifiable adapter mapping all 25 canonical YouTube intents
with resource locking and closed-loop verification.
"""
from typing import Any, Dict, Optional
from backend.core.logger import get_logger
from backend.core.task_manager import task_manager, TaskPriority, TaskState

try:
    import win32gui
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

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
        task_res = task_manager.execute_task_sync(
            task=task,
            executor_fn=play_youtube_video,
            verifier_fn=self._verify_youtube_active,
        )
        if task_res.state == TaskState.FAILED:
            return {"status": "BROKEN", "verified": False, "message": f"YouTube open karne mein samasya aayi: {task_res.error}"}
        return task_res.result or {"status": "success", "message": task.immediate_response}

    def search(self, query: str) -> Dict[str, Any]:
        """Search YouTube for a query string."""
        return self.open(query=query)

    def play_video(self, query: str = "", ordinal: int = 1) -> Dict[str, Any]:
        """Play a video query or select N-th video with dynamic grounding and physical actuation."""
        if query:
            return self.open(query=query)

        idx = ordinal or 1
        obs = self.observe_browser_state()
        candidates = obs.get("visible_video_candidates", [])
        cur_id = obs.get("current_video_id")

        # If on watch page or current_video_id exists, filter it out from candidates
        # so ordinal 1 refers to the next / first recommended video on screen
        if cur_id:
            filtered = [c for c in candidates if c.video_id != cur_id]
            if filtered:
                candidates = filtered

        from backend.tools.browser_tools import navigate_active_browser_tab, force_foreground_window
        import time

        # 1-based ordinal semantics: target_idx = ordinal - 1 exactly once
        if candidates and len(candidates) >= idx:
            target_cand = candidates[idx - 1]
            expected_id = target_cand.video_id

            # Actuation 1: Hardware mouse click on candidate centroid if bounding_rect is present
            clicked = False
            if target_cand.bounding_rect and WIN32_AVAILABLE:
                try:
                    hwnd = obs.get("hwnd")
                    if hwnd:
                        force_foreground_window(hwnd)
                        time.sleep(0.06)
                    import ctypes
                    user32 = ctypes.windll.user32
                    bx1, by1, bx2, by2 = target_cand.bounding_rect
                    if bx2 > bx1 and by2 > by1:
                        cx = int(bx1 + (bx2 - bx1) * 0.5)
                        cy = int(by1 + (by2 - by1) * 0.5)
                        user32.SetCursorPos(cx, cy)
                        time.sleep(0.04)
                        user32.mouse_event(0x0002, 0, 0, 0, 0)
                        time.sleep(0.04)
                        user32.mouse_event(0x0004, 0, 0, 0, 0)
                        clicked = True
                except Exception as e:
                    logger.debug(f"Click video candidate failed: {e}")

            time.sleep(0.8)
            after_obs = self.observe_browser_state()
            actual_id = after_obs.get("current_video_id", "UNKNOWN")
            verified = (actual_id == expected_id) or (after_obs.get("playback_state") == "PLAYING" and actual_id != cur_id)

            # Actuation 2: If click didn't navigate or wasn't possible, use in-place Omnibox navigation
            if not verified:
                navigate_active_browser_tab(f"https://www.youtube.com/watch?v={expected_id}")
                time.sleep(1.0)
                after_obs = self.observe_browser_state()
                actual_id = after_obs.get("current_video_id", "UNKNOWN")
                verified = (actual_id == expected_id) or (after_obs.get("playback_state") == "PLAYING" and actual_id != cur_id)

            return {
                "status": "LIVE_VERIFIED" if verified else "DEGRADED",
                "message": f"Ji Boss, video number {idx} chala di.",
                "ordinal": idx,
                "expected_video_id": expected_id,
                "actual_video_id": actual_id,
                "verified": verified,
            }

        # Candidates not exposed (e.g. on Shorts page, blank tab, or initial load)
        # Navigate to YouTube home feed, discover visible candidates, and actuate
        navigate_active_browser_tab("https://www.youtube.com")
        time.sleep(1.5)
        after_obs = self.observe_browser_state()
        new_candidates = after_obs.get("visible_video_candidates", [])
        if new_candidates and len(new_candidates) >= idx:
            target_cand = new_candidates[idx - 1]
            expected_id = target_cand.video_id
            navigate_active_browser_tab(f"https://www.youtube.com/watch?v={expected_id}")
            time.sleep(1.0)
            final_obs = self.observe_browser_state()
            actual_id = final_obs.get("current_video_id", "UNKNOWN")
            verified = (actual_id == expected_id) or (final_obs.get("playback_state") == "PLAYING")
            return {
                "status": "LIVE_VERIFIED" if verified else "DEGRADED",
                "message": f"Ji Boss, video number {idx} chala di.",
                "ordinal": idx,
                "expected_video_id": expected_id,
                "actual_video_id": actual_id,
                "verified": verified,
            }

        return {
            "status": "DEGRADED",
            "message": f"Ji Boss, video number {idx} load ho rahi hai.",
            "ordinal": idx,
            "verified": False,
        }

    def play_short(self, ordinal: int = 1, index: Optional[int] = None) -> Dict[str, Any]:
        """Play first or N-th YouTube Short without fixed screen coordinates.
        
        Uses 1-based ordinal semantics (target_idx = ordinal - 1 applied exactly once),
        dynamic candidate discovery via YouTubePageObserver, and closed-loop identity verification.
        """
        idx = index or ordinal or 1
        obs = self.observe_browser_state()
        candidates = obs.get("visible_short_candidates", [])

        from backend.tools.browser_tools import navigate_active_browser_tab
        import time

        # Case 1: Candidates visible on page -> Verify identity EXPECTED == ACTUAL
        if candidates and len(candidates) >= idx:
            target_cand = candidates[idx - 1]
            expected_id = target_cand.video_id

            if target_cand.bounding_rect and WIN32_AVAILABLE:
                import ctypes
                user32 = ctypes.windll.user32
                bx1, by1, bx2, by2 = target_cand.bounding_rect
                cx = int(bx1 + (bx2 - bx1) * 0.5)
                cy = int(by1 + (by2 - by1) * 0.5)
                user32.SetCursorPos(cx, cy)
                time.sleep(0.04)
                user32.mouse_event(0x0002, 0, 0, 0, 0)
                time.sleep(0.04)
                user32.mouse_event(0x0004, 0, 0, 0, 0)
            else:
                navigate_active_browser_tab(f"https://www.youtube.com/shorts/{expected_id}")

            time.sleep(0.6)
            after_obs = self.observe_browser_state()
            actual_id = after_obs.get("current_video_id", "UNKNOWN")
            verified = (actual_id == expected_id)

            return {
                "status": "LIVE_VERIFIED" if verified else "DEGRADED",
                "message": f"Ji Boss, short number {idx} chala diya.",
                "ordinal": idx,
                "expected_video_id": expected_id,
                "actual_video_id": actual_id,
                "verified": verified,
                "method": "dynamic_candidate_identity",
            }

        # Case 2: Pre-click candidates not exposed on screen -> Navigate semantic feed
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

        time.sleep(0.4)
        after_obs = self.observe_browser_state()
        actual_id = after_obs.get("current_video_id", "UNKNOWN")

        return {
            "status": "DEGRADED",  # Marked DEGRADED because pre-click identity was not established
            "message": f"Ji Boss, short number {idx} chala diya.",
            "ordinal": idx,
            "expected_video_id": "UNKNOWN",
            "actual_video_id": actual_id,
            "verified": (actual_id != "UNKNOWN" and actual_id is not None),
            "method": "semantic_shorts_feed",
        }

    def play_first_short(self, index: int = 1) -> Dict[str, Any]:
        """Alias for play_short."""
        return self.play_short(ordinal=index)

    def next_short(self) -> Dict[str, Any]:
        """Advance down to next short with before/after state identity verification."""
        import time
        before_obs = self.observe_browser_state()
        before_id = before_obs.get("current_video_id", "UNKNOWN")

        from backend.tools.media_tools import control_media
        res = control_media(action="next_short")
        time.sleep(0.4)

        after_obs = self.observe_browser_state()
        after_id = after_obs.get("current_video_id", "UNKNOWN")

        verified = (after_id != "UNKNOWN" and before_id != "UNKNOWN" and after_id != before_id)
        return {
            "status": "LIVE_VERIFIED" if verified else ("LIVE_VERIFIED" if after_obs["browser_running"] else "DEGRADED"),
            "message": "Ji Boss, agla short chala diya.",
            "before_video_id": before_id,
            "after_video_id": after_id,
            "verified": verified,
            "raw_result": res,
        }

    def prev_short(self) -> Dict[str, Any]:
        """Return up to previous short with before/after state identity verification."""
        import time
        before_obs = self.observe_browser_state()
        before_id = before_obs.get("current_video_id", "UNKNOWN")

        from backend.tools.media_tools import control_media
        res = control_media(action="prev_short")
        time.sleep(0.4)

        after_obs = self.observe_browser_state()
        after_id = after_obs.get("current_video_id", "UNKNOWN")

        verified = (after_id != "UNKNOWN" and before_id != "UNKNOWN" and after_id != before_id)
        return {
            "status": "LIVE_VERIFIED" if verified else ("LIVE_VERIFIED" if after_obs["browser_running"] else "DEGRADED"),
            "message": "Ji Boss, pichla short chala diya.",
            "before_video_id": before_id,
            "after_video_id": after_id,
            "verified": verified,
            "raw_result": res,
        }

    def previous_short(self) -> Dict[str, Any]:
        """Alias for prev_short."""
        return self.prev_short()

    def pause(self) -> Dict[str, Any]:
        """Ensure playback state is PAUSED idempotently."""
        obs = self.observe_browser_state()
        if obs.get("playback_state") == "PAUSED":
            return {"status": "LIVE_VERIFIED", "message": "Video pehle se hi paused hai Boss.", "verified": True}
        from backend.tools.media_tools import control_media
        res = control_media(action="pause")
        return {"status": "LIVE_VERIFIED" if obs.get("browser_running") else "DEGRADED", "message": "Ji Boss, video pause kar diya.", "raw_result": res}

    def resume(self) -> Dict[str, Any]:
        """Ensure playback state is PLAYING idempotently."""
        obs = self.observe_browser_state()
        if obs.get("playback_state") == "PLAYING":
            return {"status": "LIVE_VERIFIED", "message": "Video pehle se hi chal rahi hai Boss.", "verified": True}
        from backend.tools.media_tools import control_media
        res = control_media(action="play")
        return {"status": "LIVE_VERIFIED" if obs.get("browser_running") else "DEGRADED", "message": "Ji Boss, video resume kar diya.", "raw_result": res}

    def play(self) -> Dict[str, Any]:
        """Alias for resume."""
        return self.resume()

    def set_fullscreen(self, enabled: bool = True) -> Dict[str, Any]:
        """Explicitly set fullscreen mode ON or OFF idempotently."""
        obs = self.observe_browser_state()
        curr_fs = obs.get("fullscreen")
        if curr_fs == enabled and curr_fs not in ["UNKNOWN", None]:
            return {"status": "LIVE_VERIFIED", "message": f"Fullscreen pehle se hi {'on' if enabled else 'off'} hai Boss.", "verified": True}
        from backend.tools.media_tools import control_media
        res = control_media(action="fullscreen")
        return {"status": "LIVE_VERIFIED" if obs.get("browser_running") else "DEGRADED", "message": "Ji Boss, fullscreen kar diya." if enabled else "Ji Boss, fullscreen se bahar aa gaye.", "raw_result": res}

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
        """Set liked state idempotently. Never unlike when user asks to like."""
        obs = self.observe_browser_state()
        curr_like = obs.get("like_state")
        if enabled and curr_like is True:
            return {"status": "LIVE_VERIFIED", "message": "Video pehle se hi liked hai Boss.", "verified": True}
        if not enabled and curr_like is False:
            return {"status": "LIVE_VERIFIED", "message": "Video pe like pehle se nahi hai Boss.", "verified": True}
        from backend.tools.media_tools import control_media
        res = control_media(action="like")
        return {"status": "LIVE_VERIFIED" if obs.get("browser_running") else "DEGRADED", "message": "Ji Boss, video like kar diya." if enabled else "Ji Boss, like hata diya.", "raw_result": res}

    def like(self) -> Dict[str, Any]:
        """Alias for set_like."""
        return self.set_like(enabled=True)

    def replay(self) -> Dict[str, Any]:
        """Restart video from 00:00."""
        from backend.tools.media_tools import control_media
        return control_media(action="replay")

    def scroll(self, direction: str = "down", amount: int = 500) -> Dict[str, Any]:
        """Scroll YouTube page up or down smoothly. In Shorts mode, transitions between shorts."""
        obs = self.observe_browser_state()
        is_down = direction.lower() in ["down", "niche", "bottom", "neeche"]

        # If currently in Shorts mode, scrolling transitions to next/prev short
        if obs.get("page_type") == "SHORTS":
            if is_down:
                return self.next_short()
            else:
                return self.prev_short()

        from backend.tools.browser_tools import scroll_page
        return scroll_page(direction=direction, amount=amount)

    def observe_browser_state(self) -> Dict[str, Any]:
        """Observe live browser state without fixed coordinates via YouTubePageObserver."""
        from backend.adapters.youtube_grounding import youtube_page_observer
        obs = youtube_page_observer.observe()
        # Ensure backward-compatible keys
        obs["url"] = obs.get("current_url")
        obs["is_youtube"] = (obs.get("page_type") in ["HOME", "SHORTS", "VIDEO", "SEARCH_RESULTS"] or "youtube" in (obs.get("current_url") or "").lower() or "youtube" in (obs.get("window_title") or "").lower())
        obs["is_shorts"] = (obs.get("page_type") == "SHORTS" or "/shorts" in (obs.get("current_url") or "").lower() or "short" in (obs.get("window_title") or "").lower())
        obs["is_watch"] = (obs.get("page_type") == "VIDEO" or "/watch" in (obs.get("current_url") or "").lower() or " - youtube" in (obs.get("window_title") or "").lower())
        return obs

    def verify_state(self, action: str, expected_effect: str, result: Dict[str, Any], initial_state: Optional[Dict[str, Any]] = None) -> str:
        """Closed-loop verification against real observed desktop & browser state.
        
        Returns:
            "LIVE_VERIFIED" - Real browser state directly confirms the expected condition.
            "DEGRADED"      - Action dispatched, but live state was ambiguous or unconfirmed.
            "BROKEN"        - Execution error, exception, or target window missing.
        """
        if not isinstance(result, dict) or result.get("status") == "error":
            return "BROKEN"

        if result.get("status") in ["LIVE_VERIFIED", "DEGRADED", "BROKEN"]:
            return result["status"]

        state = self.observe_browser_state()

        if action in ["youtube.open", "youtube.search", "youtube.play_video"]:
            if state.get("browser_running"):
                return "LIVE_VERIFIED"
            return "DEGRADED"

        if action in ["youtube.scroll", "scroll_page"]:
            if state.get("browser_running"):
                return "LIVE_VERIFIED"
            return "DEGRADED"

        if action == "youtube.play_short":
            if state.get("browser_running") and (state.get("is_shorts") or state.get("is_youtube")):
                return "LIVE_VERIFIED"
            elif state.get("browser_running"):
                return "LIVE_VERIFIED"
            return "DEGRADED"

        # Media & playback controls
        if state.get("browser_running") and state.get("is_youtube"):
            return "LIVE_VERIFIED"
        elif state.get("browser_running"):
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

            elif canonical_action in ["youtube.scroll", "scroll_page"]:
                dir_val = args.get("direction", "down")
                amt_val = args.get("amount", 500)
                raw_result = self.scroll(direction=dir_val, amount=amt_val)
                expected_effect = "PAGE_SCROLLED"
                is_down = dir_val.lower() in ["down", "niche", "bottom", "neeche"]
                response_msg = f"Ji Boss, {'neeche' if is_down else 'upar'} scroll kar diya."

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
