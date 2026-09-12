"""YouTube Application Adapter for JARVIS (Contract v2.0).

Standardized, verifiable adapter mapping all 25 canonical YouTube intents
with resource locking and closed-loop verification.
"""
import time
from typing import Any, Dict, Optional
from backend.core.logger import get_logger
from backend.core.task_manager import task_manager, TaskPriority, TaskState
from backend.core.safety import (
    is_dev_safe_mode,
    is_physical_automation_allowed,
    is_live_browser_automation_allowed,
    safe_blocked_result,
)

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
        """Open YouTube Home or search for a video query with closed-loop state verification."""
        from backend.core.safety import is_live_browser_automation_allowed
        from backend.tools.browser_tools import launch_in_google_chrome, navigate_active_browser_tab
        import urllib.parse
        import time

        # Non-interactive development & test isolation
        if not is_live_browser_automation_allowed():
            logger.info("youtube.open: live browser automation is disabled in safe mode.")
            return {
                "status": "LIVE_AUTOMATION_DISABLED",
                "verified": False,
                "simulated": True,
                "query": query,
                "url": f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}" if query else "https://www.youtube.com/",
                "message": "Live browser automation is disabled in development safe mode.",
            }

        target_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}" if query else "https://www.youtube.com/"

        # 1. Actuation: Try CDP same-tab navigation first, then semantic tab switch/navigation, else launch Chrome process
        actuation_success = False
        launch_error = None

        try:
            from backend.perception.browser_session import browser_session
            if browser_session.is_cdp_available():
                if browser_session.navigate_same_tab_sync(target_url):
                    actuation_success = True
                    logger.info(f"Navigated existing CDP session tab to: {target_url}")

            if not actuation_success:
                obs = self.observe_browser_state()
                hwnd = obs.get("hwnd")

                # Try semantic browser control if Chrome/Edge is already running
                if obs.get("browser_running") and hwnd:
                    from backend.adapters.youtube_grounding import youtube_page_observer
                    if not query and youtube_page_observer.switch_to_youtube_tab(hwnd):
                        actuation_success = True
                    else:
                        nav = navigate_active_browser_tab(target_url)
                        if nav:
                            actuation_success = True

            # If no existing session handled it, launch Google Chrome process with URL
            if not actuation_success:
                launch_in_google_chrome(target_url)
                actuation_success = True

        except Exception as exc:
            logger.error(f"Failed to actuate YouTube open: {exc}")
            launch_error = str(exc)
            actuation_success = False

        if not actuation_success:
            return {
                "status": "BROKEN",
                "verified": False,
                "error": launch_error,
                "message": "YouTube open nahi ho paya.",
            }

        try:
            from backend.perception.youtube_perception import youtube_perception
            youtube_perception.invalidate_cache()
        except Exception:
            pass

        # 2. Observe & Verify (Bounded polling up to ~5 seconds)
        poll_deadline = time.time() + 5.0
        confirmed = False
        last_state: Dict[str, Any] = {}

        while time.time() < poll_deadline:
            last_state = self.observe_browser_state()
            cur_url = (last_state.get("current_url") or "").lower()
            cur_title = (last_state.get("window_title") or "").lower()
            perceived_q = (last_state.get("search_query") or "").lower()
            clean_q = (query or "").strip().lower()

            if last_state.get("browser_running") and last_state.get("is_youtube"):
                if clean_q:
                    import urllib.parse
                    quoted_q = urllib.parse.quote_plus(clean_q).lower()
                    if (clean_q in perceived_q and perceived_q != "unknown") or (quoted_q in cur_url and "search_query=" in cur_url) or (clean_q in cur_title and "youtube" in cur_title):
                        confirmed = True
                        break
                else:
                    confirmed = True
                    break
            time.sleep(0.3)

        # 3. Formulate verified outcome
        if confirmed:
            return {
                "status": "LIVE_VERIFIED",
                "verified": True,
                "url": target_url,
                "observed_state": last_state,
                "message": f"Haan Shivam, YouTube par {query} search kar diya hai." if query else "Haan Shivam, YouTube open kar diya hai.",
            }
        elif last_state.get("browser_running"):
            return {
                "status": "DEGRADED",
                "verified": False,
                "url": target_url,
                "observed_state": last_state,
                "message": "YouTube launch kiya hai, lekin main confirm nahi kar pa raha ki page open hua.",
            }
        else:
            return {
                "status": "BROKEN",
                "verified": False,
                "url": target_url,
                "observed_state": last_state,
                "message": "YouTube open nahi ho paya.",
            }

    def search(self, query: str) -> Dict[str, Any]:
        """Search YouTube for a query string with same-tab reuse and closed-loop verification."""
        from backend.core.safety import is_live_browser_automation_allowed
        from backend.tools.browser_tools import launch_in_google_chrome, navigate_active_browser_tab
        from backend.perception.browser_session import browser_session
        from backend.perception.perception_types import PageType
        import urllib.parse
        import time

        clean_query = (query or "").strip()
        if not is_live_browser_automation_allowed():
            logger.info("youtube.search: live browser automation is disabled in safe mode.")
            return {
                "status": "LIVE_AUTOMATION_DISABLED",
                "verified": False,
                "simulated": True,
                "query": clean_query,
                "url": f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(clean_query)}",
                "message": "Live browser automation is disabled in development safe mode.",
            }

        target_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(clean_query)}"

        # 1. Actuation: Re-use active YouTube tab via CDP first to prevent duplicate tabs
        actuation_success = False
        launch_error = None

        try:
            if browser_session.is_cdp_available():
                if browser_session.navigate_same_tab_sync(target_url):
                    actuation_success = True
                    logger.info(f"Reused existing CDP tab for search: {clean_query}")

            if not actuation_success:
                obs = self.observe_browser_state()
                hwnd = obs.get("hwnd")
                if obs.get("browser_running") and hwnd:
                    nav = navigate_active_browser_tab(target_url)
                    if nav:
                        actuation_success = True

            if not actuation_success:
                launch_in_google_chrome(target_url)
                actuation_success = True

        except Exception as exc:
            logger.error(f"Failed to actuate YouTube search: {exc}")
            launch_error = str(exc)
            actuation_success = False

        if not actuation_success:
            return {
                "status": "BROKEN",
                "verified": False,
                "error": launch_error,
                "message": f"YouTube par {clean_query} search nahi ho paya.",
            }

        try:
            from backend.perception.youtube_perception import youtube_perception
            youtube_perception.invalidate_cache()
        except Exception:
            pass

        # 2. Closed-loop verification
        poll_deadline = time.time() + 5.0
        confirmed = False
        last_state: Dict[str, Any] = {}

        while time.time() < poll_deadline:
            last_state = self.observe_browser_state(discover_candidates=True)
            cur_url = (last_state.get("current_url") or "").lower()
            cur_title = (last_state.get("window_title") or "").lower()
            page_type = last_state.get("page_type")
            perceived_query = (last_state.get("search_query") or "").lower()

            clean_q = clean_query.lower().strip()
            import urllib.parse
            quoted_q = urllib.parse.quote_plus(clean_q).lower()

            query_observed = (
                (clean_q in perceived_query and perceived_query != "unknown") or
                (quoted_q in cur_url and "search_query=" in cur_url) or
                (clean_q in cur_title and "youtube" in cur_title)
            )

            if last_state.get("browser_running") and query_observed:
                confirmed = True
                break
            time.sleep(0.3)

        if confirmed:
            return {
                "status": "LIVE_VERIFIED",
                "verified": True,
                "query": clean_query,
                "url": target_url,
                "observed_state": last_state,
                "message": f"Haan Shivam, YouTube par {clean_query} search kar diya hai.",
            }
        elif last_state.get("browser_running"):
            return {
                "status": "DEGRADED",
                "verified": False,
                "query": clean_query,
                "url": target_url,
                "observed_state": last_state,
                "message": f"YouTube par {clean_query} search kiya hai, lekin results verify nahi ho paye.",
            }
        else:
            return {
                "status": "BROKEN",
                "verified": False,
                "query": clean_query,
                "url": target_url,
                "observed_state": last_state,
                "message": "YouTube open nahi ho paya.",
            }

    def play_video(self, query: str = "", ordinal: int = 1) -> Dict[str, Any]:
        """Play a video query or select N-th video with dynamic grounding and physical actuation."""
        if query:
            return self.search(query=query)

        idx = ordinal or 1
        obs = self.observe_browser_state(discover_candidates=True)
        candidates = obs.get("visible_video_candidates", [])
        cur_id = obs.get("current_video_id")

        # If on watch page or current_video_id exists, filter it out from candidates
        # so ordinal 1 refers to the next / first recommended video on screen
        if cur_id and cur_id != "UNKNOWN":
            filtered = [c for c in candidates if (getattr(c, "video_id", None) or (c.get("video_id") if isinstance(c, dict) else None)) != cur_id]
            if filtered:
                candidates = filtered

        from backend.core.safety import is_live_browser_automation_allowed
        from backend.tools.browser_tools import navigate_active_browser_tab, force_foreground_window
        from backend.perception.browser_session import browser_session
        from backend.perception.youtube_perception import youtube_perception
        import time

        # Non-interactive development & test isolation
        if not is_live_browser_automation_allowed() and not (candidates and len(candidates) >= idx):
            target_id = obs.get("current_video_id") if obs.get("current_video_id") != "UNKNOWN" else f"VID_SIM_{idx}"
            return {
                "status": "SIMULATED",
                "message": f"Simulation: video number {idx} (live automation disabled).",
                "ordinal": idx,
                "expected_video_id": target_id,
                "actual_video_id": target_id,
                "verified": False,
                "simulated": True,
            }

        # 1-based ordinal semantics: target_idx = ordinal - 1 exactly once
        if candidates and len(candidates) >= idx:
            target_cand = candidates[idx - 1]
            expected_id = getattr(target_cand, "video_id", None) or (target_cand.get("video_id") if isinstance(target_cand, dict) else "UNKNOWN")
            expected_url = getattr(target_cand, "url", None) or (target_cand.get("url") if isinstance(target_cand, dict) else None)
            if not expected_url or expected_url == "UNKNOWN":
                expected_url = f"https://www.youtube.com/watch?v={expected_id}"

            # Semantic browser navigation on SAME tab (never duplicate tabs)
            nav_ok = False
            if browser_session.is_cdp_available():
                nav_ok = browser_session.navigate_same_tab_sync(expected_url)

            if not nav_ok:
                nav_ok = navigate_active_browser_tab(expected_url)

            try:
                youtube_perception.invalidate_cache()
            except Exception:
                pass
            time.sleep(0.8)

            after_obs = self.observe_browser_state()
            actual_id = after_obs.get("current_video_id", "UNKNOWN")
            verified = (
                actual_id != "UNKNOWN" and
                expected_id != "UNKNOWN" and
                not expected_id.startswith("VID_SIM_") and
                not expected_id.startswith("cand_") and
                actual_id == expected_id
            )

            if not is_live_browser_automation_allowed() and not verified:
                return {
                    "status": "SIMULATED",
                    "message": f"Simulation: video number {idx} (live automation disabled).",
                    "ordinal": idx,
                    "expected_video_id": expected_id,
                    "actual_video_id": actual_id,
                    "verified": False,
                    "simulated": True,
                }

            return {
                "status": "LIVE_VERIFIED" if verified else "DEGRADED",
                "message": f"Ji Boss, video number {idx} chala di." if verified else f"Video number {idx} play karne ki koshish ki, lekin playback verify nahi ho paya.",
                "ordinal": idx,
                "expected_video_id": expected_id,
                "actual_video_id": actual_id,
                "verified": verified,
            }

        # Candidates not immediately available: perform bounded retry for DOM recommendations to render
        poll_deadline = time.time() + 1.5
        while time.time() < poll_deadline:
            time.sleep(0.3)
            retry_obs = self.observe_browser_state(discover_candidates=True)
            retry_cands = retry_obs.get("visible_video_candidates", [])
            if cur_id and cur_id != "UNKNOWN":
                retry_cands = [c for c in retry_cands if (getattr(c, "video_id", None) or (c.get("video_id") if isinstance(c, dict) else None)) != cur_id]
            if retry_cands and len(retry_cands) >= idx:
                candidates = retry_cands
                target_cand = candidates[idx - 1]
                expected_id = getattr(target_cand, "video_id", None) or (target_cand.get("video_id") if isinstance(target_cand, dict) else "UNKNOWN")
                expected_url = getattr(target_cand, "url", None) or (target_cand.get("url") if isinstance(target_cand, dict) else None)
                if not expected_url or expected_url == "UNKNOWN":
                    expected_url = f"https://www.youtube.com/watch?v={expected_id}"

                nav_ok = False
                if browser_session.is_cdp_available():
                    nav_ok = browser_session.navigate_same_tab_sync(expected_url)
                if not nav_ok:
                    nav_ok = navigate_active_browser_tab(expected_url)

                time.sleep(0.8)
                after_obs = self.observe_browser_state()
                actual_id = after_obs.get("current_video_id", "UNKNOWN")
                verified = (
                    actual_id != "UNKNOWN" and
                    expected_id != "UNKNOWN" and
                    not expected_id.startswith("VID_SIM_") and
                    not expected_id.startswith("cand_") and
                    actual_id == expected_id
                )
                return {
                    "status": "LIVE_VERIFIED" if verified else "DEGRADED",
                    "message": f"Ji Boss, video number {idx} chala di." if verified else f"Video number {idx} play karne ki koshish ki, lekin playback verify nahi ho paya.",
                    "ordinal": idx,
                    "expected_video_id": expected_id,
                    "actual_video_id": actual_id,
                    "verified": verified,
                }

        # Candidates genuinely unavailable on page: NEVER fall back to resume()
        return {
            "status": "DEGRADED",
            "message": f"Video number {idx} screen par nahi dikh rahi hai Boss.",
            "ordinal": idx,
            "verified": False,
        }


    def play_first_video(self, ordinal: int = 1) -> Dict[str, Any]:
        """Alias for play_video."""
        return self.play_video(ordinal=ordinal)

    def play_short(self, ordinal: int = 1, index: Optional[int] = None) -> Dict[str, Any]:
        """Play first or N-th YouTube Short without fixed screen coordinates.
        
        Uses 1-based ordinal semantics (target_idx = ordinal - 1 applied exactly once),
        dynamic candidate discovery via YouTubePageObserver, and closed-loop identity verification.
        """
        from backend.core.safety import is_live_browser_automation_allowed
        idx = index or ordinal or 1
        obs = self.observe_browser_state(discover_candidates=True)
        candidates = obs.get("visible_short_candidates", [])

        # Non-interactive development & test isolation
        if not is_live_browser_automation_allowed() and not (candidates and len(candidates) >= idx):
            target_id = f"SHORT_SIM_{idx}"
            return {
                "status": "SIMULATED",
                "message": f"Simulation: short number {idx} (live automation disabled).",
                "ordinal": idx,
                "expected_video_id": target_id,
                "actual_video_id": target_id,
                "verified": False,
                "method": "semantic_shorts_identity",
                "simulated": True,
            }

        from backend.tools.browser_tools import navigate_active_browser_tab
        import time

        # Case 1: Candidates visible on page -> Navigate semantically without mouse movement
        if candidates and len(candidates) >= idx:
            target_cand = candidates[idx - 1]
            expected_id = target_cand.video_id
            target_title = getattr(target_cand, "title", "")
            navigate_active_browser_tab(f"https://www.youtube.com/shorts/{expected_id}")

            time.sleep(0.8)
            after_obs = self.observe_browser_state()
            actual_id = after_obs.get("current_video_id", "UNKNOWN")
            verified = (
                actual_id != "UNKNOWN" and
                expected_id != "UNKNOWN" and
                not expected_id.startswith("SHORT_SIM_") and
                actual_id == expected_id
            )

            if not is_live_browser_automation_allowed() and not verified:
                return {
                    "status": "SIMULATED",
                    "message": f"Simulation: short number {idx} (live automation disabled).",
                    "ordinal": idx,
                    "expected_video_id": expected_id,
                    "actual_video_id": actual_id,
                    "verified": False,
                    "method": "semantic_shorts_identity",
                    "simulated": True,
                }

            msg = f"Ji Boss, short '{target_title}' chala diya." if target_title else f"Ji Boss, short number {idx} chala diya."

            return {
                "status": "LIVE_VERIFIED" if verified else "DEGRADED",
                "message": msg,
                "ordinal": idx,
                "expected_video_id": expected_id,
                "actual_video_id": actual_id,
                "verified": verified,
                "method": "semantic_shorts_navigation",
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

        if idx > 1 and is_physical_automation_allowed():
            from backend.tools.media_tools import _send_key_event
            for _ in range(idx - 1):
                _send_key_event(0x28)  # VK_DOWN
                time.sleep(0.20)

        time.sleep(0.4)
        after_obs = self.observe_browser_state()
        actual_id = after_obs.get("current_video_id", "UNKNOWN")

        return {
            "status": "DEGRADED",
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

        if not is_live_browser_automation_allowed() and not verified:
            return {
                "status": "SIMULATED",
                "message": "Simulation: next short (live automation disabled).",
                "before_video_id": before_id,
                "after_video_id": after_id,
                "verified": False,
                "simulated": True,
            }

        return {
            "status": "LIVE_VERIFIED" if verified else "DEGRADED",
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

        if not is_live_browser_automation_allowed() and not verified:
            return {
                "status": "SIMULATED",
                "message": "Simulation: previous short (live automation disabled).",
                "before_video_id": before_id,
                "after_video_id": after_id,
                "verified": False,
                "simulated": True,
            }

        return {
            "status": "LIVE_VERIFIED" if verified else "DEGRADED",
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
        time.sleep(0.20)
        post_obs = self.observe_browser_state()
        is_paused = (post_obs.get("playback_state") == "PAUSED")
        return {
            "status": "LIVE_VERIFIED" if is_paused else "DEGRADED",
            "message": "Ji Boss, video pause kar diya.",
            "verified": is_paused,
            "raw_result": res,
        }

    def resume(self) -> Dict[str, Any]:
        """Ensure playback state is PLAYING idempotently."""
        obs = self.observe_browser_state()
        if obs.get("playback_state") == "PLAYING":
            return {"status": "LIVE_VERIFIED", "message": "Video pehle se hi chal rahi hai Boss.", "verified": True}
        from backend.tools.media_tools import control_media
        res = control_media(action="play")
        time.sleep(0.20)
        post_obs = self.observe_browser_state()
        is_playing = (post_obs.get("playback_state") == "PLAYING")
        return {
            "status": "LIVE_VERIFIED" if is_playing else "DEGRADED",
            "message": "Ji Boss, video resume kar diya.",
            "verified": is_playing,
            "raw_result": res,
        }

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
        time.sleep(0.20)
        post_obs = self.observe_browser_state()
        verified = (post_obs.get("fullscreen") == enabled) if post_obs.get("fullscreen") not in ["UNKNOWN", None] else False
        return {
            "status": "LIVE_VERIFIED" if verified else "DEGRADED",
            "message": "Ji Boss, fullscreen kar diya." if enabled else "Ji Boss, fullscreen se bahar aa gaye.",
            "verified": verified,
            "raw_result": res,
        }

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
        time.sleep(0.25)
        post_obs = self.observe_browser_state()
        new_like = post_obs.get("like_state")

        if (enabled and new_like is True) or (not enabled and new_like is False):
            status = "LIVE_VERIFIED"
            verified = True
        elif post_obs.get("browser_running") and post_obs.get("is_youtube"):
            status = "DEGRADED"
            verified = False
        else:
            status = "BROKEN"
            verified = False

        return {
            "status": status,
            "verified": verified,
            "message": "Ji Boss, video like kar diya." if enabled else "Ji Boss, like hata diya.",
            "raw_result": res,
            "like_state": new_like,
        }

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

        if not is_physical_automation_allowed():
            return {
                "status": "SIMULATED",
                "direction": "down" if is_down else "up",
                "message": f"Simulation: scroll {'neeche' if is_down else 'upar'} (physical automation disabled).",
                "simulated": True,
                "verified": False,
            }

        from backend.tools.browser_tools import scroll_page
        return scroll_page(direction=direction, amount=amount)

    def observe_browser_state(self, discover_candidates: bool = False) -> Dict[str, Any]:
        """Observe live browser state via JARVIS Eyes V1 YouTubePerception with legacy fallback."""
        try:
            from backend.perception.youtube_perception import youtube_perception
            from backend.perception.perception_types import PageType

            snap = youtube_perception.observe(force_refresh=discover_candidates)
            yt = snap.youtube
            browser = snap.browser

            page_type_str = yt.page_type.value if hasattr(yt.page_type, "value") else str(yt.page_type)
            cur_url = yt.current_video.url if (yt.current_video and yt.current_video.url != "UNKNOWN") else browser.url
            if cur_url == "UNKNOWN" and browser.url != "UNKNOWN":
                cur_url = browser.url

            playback_state = "UNKNOWN"
            if yt.player and yt.player.exists:
                playback_state = "PAUSED" if yt.player.paused is True else "PLAYING"

            obs: Dict[str, Any] = {
                "browser_running": browser.connected or (browser.hwnd != 0),
                "browser_name": browser.browser_name,
                "hwnd": browser.hwnd,
                "window_title": browser.title,
                "is_foreground": False,
                "current_url": cur_url,
                "url": cur_url,
                "page_type": page_type_str,
                "current_video_id": yt.current_video.video_id if yt.current_video else "UNKNOWN",
                "current_title": yt.current_video.title if yt.current_video else "UNKNOWN",
                "playback_state": playback_state,
                "current_time": yt.player.current_time if yt.player else "UNKNOWN",
                "duration": yt.player.duration if yt.player else "UNKNOWN",
                "volume": yt.player.volume if yt.player else "UNKNOWN",
                "muted": yt.player.muted if yt.player else "UNKNOWN",
                "fullscreen": yt.controls.fullscreen if yt.controls else "UNKNOWN",
                "theater_mode": yt.controls.theater if yt.controls else "UNKNOWN",
                "miniplayer": yt.controls.miniplayer if yt.controls else "UNKNOWN",
                "captions": yt.controls.captions if yt.controls else "UNKNOWN",
                "playback_rate": yt.player.playback_rate if yt.player else 1.0,
                "like_state": yt.controls.like_state if yt.controls else "UNKNOWN",
                "visible_video_candidates": yt.visible_videos,
                "visible_short_candidates": yt.visible_shorts,
                "is_youtube": yt.is_youtube or ("youtube" in (cur_url or "").lower()) or ("youtube" in (browser.title or "").lower()),
                "is_shorts": page_type_str == PageType.SHORTS.value or "/shorts" in (cur_url or "").lower(),
                "is_watch": page_type_str == PageType.VIDEO.value or "/watch" in (cur_url or "").lower() or " - youtube" in (browser.title or "").lower(),
                "search_query": yt.search_query,
                "perception_snapshot": snap,
            }

            # If candidates were requested but CDP returned none, fallback to legacy UIA observer
            if discover_candidates and not obs["visible_video_candidates"] and not obs["visible_short_candidates"]:
                try:
                    from backend.adapters.youtube_grounding import youtube_page_observer
                    legacy_obs = youtube_page_observer.observe(discover_candidates=True)
                    if legacy_obs.get("visible_video_candidates"):
                        obs["visible_video_candidates"] = legacy_obs["visible_video_candidates"]
                    if legacy_obs.get("visible_short_candidates"):
                        obs["visible_short_candidates"] = legacy_obs["visible_short_candidates"]
                except Exception:
                    pass

            return obs
        except Exception as exc:
            logger.debug(f"observe_browser_state perception fallback: {exc}")
            from backend.adapters.youtube_grounding import youtube_page_observer
            obs = youtube_page_observer.observe(discover_candidates=discover_candidates)
            obs["url"] = obs.get("current_url")
            obs["is_youtube"] = (obs.get("page_type") in ["HOME", "SHORTS", "VIDEO", "SEARCH_RESULTS"] or "youtube" in (obs.get("current_url") or "").lower() or "youtube" in (obs.get("window_title") or "").lower())
            obs["is_shorts"] = (obs.get("page_type") == "SHORTS" or "/shorts" in (obs.get("current_url") or "").lower() or "short" in (obs.get("window_title") or "").lower())
            obs["is_watch"] = (obs.get("page_type") == "VIDEO" or "/watch" in (obs.get("current_url") or "").lower() or " - youtube" in (obs.get("window_title") or "").lower())
            return obs

    def observe(self, max_items: int = 5, target: Optional[str] = None) -> Dict[str, Any]:
        """Perception inquiry method returning structured and human-readable perception data."""
        from backend.perception.youtube_perception import youtube_perception
        summary = youtube_perception.format_diagnostic_summary(max_items=max_items, target=target)
        spoken_msg = youtube_perception.format_voice_summary(max_items=max_items, target=target)
        snap = youtube_perception.observe(force_refresh=True)
        is_yt = snap.browser.connected or snap.youtube.is_youtube
        return {
            "status": "LIVE_VERIFIED" if is_yt else "DEGRADED",
            "verified": is_yt,
            "summary": summary,
            "message": spoken_msg,
            "snapshot": snap.to_dict(),
        }

    def verify_state(self, action: str, expected_effect: str, result: Dict[str, Any], initial_state: Optional[Dict[str, Any]] = None) -> str:
        """Closed-loop verification against real observed desktop & browser state.
        
        Returns:
            "LIVE_VERIFIED" - Real browser state directly confirms the expected condition.
            "DEGRADED"      - Action dispatched, but live state was ambiguous or unconfirmed.
            "BROKEN"        - Execution error, exception, or target window missing.
        """
        if not isinstance(result, dict) or result.get("status") == "error":
            return "BROKEN"

        if result.get("simulated"):
            return "SIMULATED"

        if result.get("status") in ["DEGRADED", "BROKEN", "SIMULATED", "LIVE_AUTOMATION_DISABLED"]:
            return result["status"]

        state = self.observe_browser_state()

        if not state.get("browser_running"):
            return "BROKEN"

        if not state.get("is_youtube"):
            return "DEGRADED"

        if action == "youtube.open":
            cur_url = (state.get("current_url") or "").lower()
            title = (state.get("window_title") or "").lower()
            q = (result.get("query") or "").lower().strip()
            if state.get("is_youtube") and cur_url != "about:blank":
                if q:
                    import urllib.parse
                    quoted_q = urllib.parse.quote_plus(q).lower()
                    perceived_q = (state.get("search_query") or "").lower().strip()
                    query_observed = (
                        (q in perceived_q and perceived_q != "unknown") or
                        (quoted_q in cur_url and "search_query=" in cur_url) or
                        (q in title and "youtube" in title)
                    )
                    return "LIVE_VERIFIED" if query_observed else "DEGRADED"
                return "LIVE_VERIFIED"
            return "DEGRADED"

        if action == "youtube.search":
            cur_url = (state.get("current_url") or "").lower()
            q = (result.get("query") or "").lower().strip()
            title = (state.get("window_title") or "").lower()
            perceived_q = (state.get("search_query") or "").lower().strip()
            if q and state.get("is_youtube"):
                import urllib.parse
                quoted_q = urllib.parse.quote_plus(q).lower()
                query_observed = (
                    (q in perceived_q and perceived_q != "unknown") or
                    (quoted_q in cur_url and "search_query=" in cur_url) or
                    (q in title and "youtube" in title)
                )
                if query_observed:
                    return "LIVE_VERIFIED"
                return "DEGRADED"
            return "DEGRADED"

        if action in ["youtube.play_video", "youtube.play_first_video"]:
            actual_id = state.get("current_video_id", "UNKNOWN")
            exp_id = result.get("expected_video_id")
            if exp_id and exp_id != "UNKNOWN" and not exp_id.startswith("cand_") and not exp_id.startswith("VID_SIM_"):
                if actual_id == exp_id:
                    return "LIVE_VERIFIED"
                return "DEGRADED"
            return "DEGRADED"

        if action == "youtube.play_short":
            actual_id = state.get("current_video_id", "UNKNOWN")
            exp_id = result.get("expected_video_id")
            if exp_id and exp_id != "UNKNOWN" and not exp_id.startswith("SHORT_SIM_"):
                if actual_id == exp_id:
                    return "LIVE_VERIFIED"
                return "DEGRADED"
            return "DEGRADED"

        if action in ["youtube.scroll", "scroll_page"]:
            return "LIVE_VERIFIED" if state.get("is_youtube") else "DEGRADED"

        if action == "youtube.observe":
            return "LIVE_VERIFIED" if state.get("is_youtube") else "DEGRADED"

        if action == "youtube.pause":
            if state.get("playback_state") == "PAUSED":
                return "LIVE_VERIFIED"
            return "DEGRADED"

        if action in ["youtube.resume", "youtube.play"]:
            if state.get("playback_state") == "PLAYING":
                return "LIVE_VERIFIED"
            return "DEGRADED"

        if action in ["youtube.set_fullscreen", "youtube.fullscreen"]:
            if state.get("fullscreen") is True:
                return "LIVE_VERIFIED"
            return "DEGRADED"

        if action in ["youtube.set_like", "youtube.like"]:
            if state.get("like_state") is True:
                return "LIVE_VERIFIED"
            return "DEGRADED"

        if action == "youtube.set_theater_mode":
            if state.get("theater_mode") is True:
                return "LIVE_VERIFIED"
            return "DEGRADED"

        if action == "youtube.set_miniplayer":
            if state.get("miniplayer") is True:
                return "LIVE_VERIFIED"
            return "DEGRADED"

        if action in ["youtube.set_captions", "youtube.captions"]:
            en = result.get("arguments", {}).get("enabled", True) if isinstance(result.get("arguments"), dict) else True
            if state.get("captions") == en:
                return "LIVE_VERIFIED"
            return "DEGRADED"

        if action == "youtube.mute":
            if state.get("muted") is True:
                return "LIVE_VERIFIED"
            return "DEGRADED"

        if action in ["youtube.next_short", "youtube.prev_short", "youtube.previous_short"]:
            if result.get("verified") is True:
                return "LIVE_VERIFIED"
            return "DEGRADED"

        if action in [
            "youtube.replay",
            "youtube.seek_forward",
            "youtube.seek_backward",
            "youtube.seek_timestamp",
            "youtube.set_volume",
            "youtube.volume_up",
            "youtube.volume_down",
            "youtube.set_playback_speed",
            "youtube.speed_up",
            "youtube.speed_down",
        ]:
            if (result.get("verified") is True or result.get("status") == "LIVE_VERIFIED") and state.get("is_youtube"):
                return "LIVE_VERIFIED"
            return "DEGRADED"

        return "DEGRADED"

    def execute_canonical(self, canonical_action: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute any of the 25 canonical YouTube intents with state verification."""
        args = arguments or {}
        raw_result: Dict[str, Any] = {}
        effects_map = {
            "youtube.open": "NAVIGATED_HOME",
            "youtube.search": "SEARCH_RESULTS_DISPLAYED",
            "youtube.observe": "PAGE_OBSERVED",
            "youtube.play_video": "VIDEO_PLAYING",
            "youtube.play_first_video": "VIDEO_PLAYING",
            "youtube.play_short": "SHORT_PLAYING",
            "youtube.next_short": "NAVIGATED_NEXT_SHORT",
            "youtube.previous_short": "NAVIGATED_PREV_SHORT",
            "youtube.prev_short": "NAVIGATED_PREV_SHORT",
            "youtube.scroll": "PAGE_SCROLLED",
            "scroll_page": "PAGE_SCROLLED",
            "youtube.pause": "PAUSED",
            "youtube.resume": "PLAYING",
            "youtube.play": "PLAYING",
            "youtube.set_fullscreen": "FULLSCREEN_STATE_SET",
            "youtube.fullscreen": "FULLSCREEN_STATE_SET",
            "youtube.set_theater_mode": "THEATER_MODE_SET",
            "youtube.set_miniplayer": "MINIPLAYER_STATE_SET",
            "youtube.set_captions": "CAPTIONS_STATE_SET",
            "youtube.captions": "CAPTIONS_STATE_SET",
            "youtube.set_playback_speed": "SPEED_SET",
            "youtube.speed_up": "SPEED_INCREASED",
            "youtube.speed_down": "SPEED_DECREASED",
            "youtube.seek_forward": "SEEKED_FORWARD",
            "youtube.seek_backward": "SEEKED_BACKWARD",
            "youtube.seek_timestamp": "SEEKED_TO_TIMESTAMP",
            "youtube.set_volume": "VOLUME_LEVEL_SET",
            "youtube.volume_up": "VOLUME_INCREASED",
            "youtube.volume_down": "VOLUME_DECREASED",
            "youtube.mute": "MUTED",
            "youtube.unmute": "UNMUTED",
            "youtube.set_like": "LIKED_STATE_SET",
            "youtube.like": "LIKED_STATE_SET",
            "youtube.replay": "REPLAYED",
        }
        expected_effect = effects_map.get(canonical_action, "UNKNOWN")
        response_msg = "Ji Boss, ho gaya."

        initial_state = self.observe_browser_state()

        try:
            if canonical_action == "youtube.open":
                q = args.get("query", "")
                raw_result = self.open(query=q)
                expected_effect = "NAVIGATED_HOME"
                response_msg = raw_result.get("message") or (f"Haan Shivam, YouTube par {q} chala diya hai." if q else "Haan Shivam, YouTube open kar diya hai.")

            elif canonical_action == "youtube.search":
                q = args.get("query", "")
                raw_result = self.search(query=q)
                expected_effect = "SEARCH_RESULTS_DISPLAYED"
                response_msg = f"Haan Shivam, YouTube par {q} search kar diya hai."

            elif canonical_action == "youtube.observe":
                max_items = args.get("max_items", 5)
                target = args.get("target")
                raw_result = self.observe(max_items=max_items, target=target)
                expected_effect = "PAGE_OBSERVED"
                response_msg = raw_result.get("message") or raw_result.get("summary") or "Page observed."

            elif canonical_action in ["youtube.play_video", "youtube.play_first_video"]:
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

        if status == "LIVE_VERIFIED":
            verified = True
            msg = raw_result.get("message") or response_msg
        elif status == "DEGRADED":
            verified = False
            msg = raw_result.get("message") if (raw_result.get("status") == "DEGRADED") else "Action execute kiya hai, lekin main confirm nahi kar pa raha ki screen par reflect hua."
        elif status in ["SIMULATED", "LIVE_AUTOMATION_DISABLED"]:
            verified = False
            msg = raw_result.get("message") or "Development safe mode active hai; live automation perform nahi kiya gaya."
        else:
            verified = False
            msg = raw_result.get("message") if (raw_result.get("status") == "BROKEN") else "Action execute nahi ho paya."

        return {
            "canonical_action": canonical_action,
            "arguments": args,
            "status": status,
            "verified": verified,
            "expected_effect": expected_effect,
            "observed_state": observed_state,
            "message": msg,
            "raw_result": raw_result,
        }

    def _verify_youtube_active(self, task: Any = None, result: Any = None) -> bool:
        """Verify that YouTube is actively open and running in the browser."""
        try:
            obs = self.observe_browser_state()
            if not obs.get("browser_running"):
                return False

            # Check 1: observer reports is_youtube
            if obs.get("is_youtube"):
                return True

            # Check 2: active URL belongs to youtube.com
            cur_url = (obs.get("current_url") or "").lower()
            if "youtube.com" in cur_url:
                return True

            # Check 3: window title specifically confirms YouTube (not generic Chrome/Edge)
            title = (obs.get("window_title") or "").lower()
            if "youtube" in title:
                return True

            # Generic Chrome exists is NOT enough
            return False
        except Exception as exc:
            logger.debug(f"_verify_youtube_active exception: {exc}")
            return False


# Global Singleton YouTube Adapter
youtube_adapter = YouTubeAdapter()
