"""Authoritative DOM & CDP Executor for YouTube Runtime V3.

Implements Phase 10, 12, 13, 14, and 15 invariants:
- Zero screen coordinates, zero physical mouse movement, zero physical keyboard automation.
- Same-tab navigation guarantee (before.page_id == after.page_id).
- Pure DOM HTMLMediaElement player execution (no Windows master volume manipulation).
- Pure DOM UI button control execution.
"""
import time
import urllib.parse
from typing import Any, Dict, Optional

from backend.core.logger import get_logger
from backend.core import safety
from backend.youtube.dom import (
    DOM_MEDIA_PAUSE_SCRIPT,
    DOM_MEDIA_PLAY_SCRIPT,
    DOM_MEDIA_REPLAY_SCRIPT,
    get_dom_card_click_script,
    get_dom_mute_script,
    get_dom_playback_rate_script,
    get_dom_scroll_script,
    get_dom_seek_script,
    get_dom_set_captions_script,
    get_dom_set_fullscreen_script,
    get_dom_set_like_script,
    get_dom_set_miniplayer_script,
    get_dom_set_theater_script,
    get_dom_volume_script,
)
from backend.youtube.models import ActionStatus
from backend.youtube.planner import ExecutionPlan
from backend.youtube.session import youtube_session

logger = get_logger("YouTubeExecutorV3")


class YouTubeExecutor:
    """Executes validated execution plans directly against the browser DOM."""

    def execute(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Execute plan and return actuation result dictionary."""
        # Check if plan was aborted during planning (e.g. TARGET_NOT_VISIBLE)
        if plan.aborted_status:
            return {
                "actuation_status": plan.aborted_status,
                "message": plan.abort_message,
                "error": str(plan.aborted_status.value),
            }

        action = plan.action
        args = plan.arguments

        # Safe Development Mode / Live Automation Safety Guard
        from backend.youtube.perception import youtube_perception
        if not safety.is_live_browser_automation_allowed() and not youtube_perception.is_override_active():
            logger.info(f"Safe mode: Live browser execution blocked for {action}")
            return {
                "actuation_status": ActionStatus.SIMULATED,
                "message": "Development safe mode active; live automation perform nahi kiya gaya.",
                "simulated": True,
            }

        # ── 1. Action: youtube.open ─────────────────────────────────────────
        if action == "youtube.open":
            q = (args.get("query") or "").strip()
            target_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}" if q else "https://www.youtube.com/"
            from backend.youtube.perception import youtube_perception
            if youtube_perception.is_override_active():
                return {"actuation_status": ActionStatus.LIVE_VERIFIED, "target_url": target_url}

            page = youtube_session.execute_async_safe(youtube_session.ensure_youtube_page(target_url=target_url, launch_if_needed=True))
            if not page:
                return {"actuation_status": ActionStatus.CDP_UNAVAILABLE, "error": "Could not connect to Chrome CDP"}
            return {"actuation_status": ActionStatus.LIVE_VERIFIED, "target_url": target_url}

        # Ensure active controlled page exists for all other actions
        if not youtube_perception.is_override_active() and not youtube_session.is_cdp_available():
            return {"actuation_status": ActionStatus.CDP_UNAVAILABLE, "error": "No controlled YouTube tab found over CDP"}

        # ── 2. Action: youtube.search (Phase 10 Same Tab Guarantee) ─────────
        if action == "youtube.search":
            q = (args.get("query") or "").strip()
            target_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}"
            page_id_before = youtube_session.page_id
            nav_ok = youtube_session.navigate_same_tab_sync(target_url)
            page_id_after = youtube_session.page_id

            if not nav_ok:
                return {"actuation_status": ActionStatus.DEGRADED, "error": "Same tab navigation failed"}
            if page_id_before != "UNKNOWN" and page_id_after != page_id_before:
                return {"actuation_status": ActionStatus.DEGRADED, "error": "Navigation violated same-tab guarantee"}
            return {"actuation_status": ActionStatus.LIVE_VERIFIED, "query": q, "url": target_url}

        # ── 3. Action: youtube.play_video (Phase 12 Video Execution) ────────
        if action in ["youtube.play_video", "youtube.play_first_video"]:
            q = (args.get("query") or "").strip()
            ordinal = args.get("ordinal", 1)
            target_video = plan.target_video

            if q:
                # 1. Direct query search navigation
                target_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}"
                nav_ok = youtube_session.navigate_sync(target_url)
                if not nav_ok and not youtube_perception.is_override_active():
                    return {"actuation_status": ActionStatus.DEGRADED, "error": "Navigation to search failed"}
                time.sleep(0.5)

                # 2. Observe fresh rendered cards on search results page
                search_snapshot = youtube_perception.observe_fresh(force_refresh=True)
                visible_vids = search_snapshot.visible_videos
                if not visible_vids or len(visible_vids) < ordinal:
                    return {
                        "actuation_status": ActionStatus.TARGET_NOT_VISIBLE,
                        "error": f"Search results for '{q}' did not show video ordinal {ordinal}",
                        "ordinal": ordinal,
                    }
                target_video = visible_vids[ordinal - 1]

            if not target_video:
                return {"actuation_status": ActionStatus.TARGET_NOT_VISIBLE, "error": "No visible target video"}

            target_url = target_video.url
            vid_id = target_video.video_id

            # Preferred: exact DOM card click or same-page navigation
            clicked = youtube_session.evaluate_sync(get_dom_card_click_script(vid_id))
            if not clicked:
                youtube_session.navigate_sync(target_url)
            time.sleep(0.5)
            return {
                "actuation_status": ActionStatus.LIVE_VERIFIED,
                "expected_video_id": vid_id,
                "ordinal": ordinal if q else plan.target_ordinal,
            }

        # ── 4. Action: youtube.play_short (Phase 13 Shorts Execution) ───────
        if action in ["youtube.play_short", "youtube.play_first_short"]:
            if not plan.target_video:
                return {"actuation_status": ActionStatus.TARGET_NOT_VISIBLE, "error": "No visible target short"}

            target_url = plan.target_video.url
            sid = plan.target_video.video_id
            youtube_session.navigate_sync(target_url)
            time.sleep(0.5)
            return {
                "actuation_status": ActionStatus.LIVE_VERIFIED,
                "expected_video_id": sid,
                "ordinal": plan.target_ordinal,
            }

        # ── 5. Action: Player Controls (Phase 14 Pure DOM Execution) ────────
        if action == "youtube.pause":
            youtube_session.evaluate_sync(DOM_MEDIA_PAUSE_SCRIPT)
            return {"actuation_status": ActionStatus.LIVE_VERIFIED}

        if action in ["youtube.resume", "youtube.play"]:
            youtube_session.evaluate_sync(DOM_MEDIA_PLAY_SCRIPT)
            return {"actuation_status": ActionStatus.LIVE_VERIFIED}

        if action == "youtube.replay":
            youtube_session.evaluate_sync(DOM_MEDIA_REPLAY_SCRIPT)
            return {"actuation_status": ActionStatus.LIVE_VERIFIED}

        if action == "youtube.seek_forward":
            secs = args.get("seconds", 10)
            cur_t = plan.snapshot_before.player.current_time
            if cur_t != "UNKNOWN":
                target_t = float(cur_t) + float(secs)
                youtube_session.evaluate_sync(get_dom_seek_script(target_t))
                return {"actuation_status": ActionStatus.LIVE_VERIFIED, "target_time": target_t}
            return {"actuation_status": ActionStatus.DEGRADED}

        if action == "youtube.seek_backward":
            secs = args.get("seconds", 10)
            cur_t = plan.snapshot_before.player.current_time
            if cur_t != "UNKNOWN":
                target_t = max(0.0, float(cur_t) - float(secs))
                youtube_session.evaluate_sync(get_dom_seek_script(target_t))
                return {"actuation_status": ActionStatus.LIVE_VERIFIED, "target_time": target_t}
            return {"actuation_status": ActionStatus.DEGRADED}

        if action == "youtube.seek_timestamp":
            secs = args.get("seconds", 0)
            youtube_session.evaluate_sync(get_dom_seek_script(secs))
            return {"actuation_status": ActionStatus.LIVE_VERIFIED, "target_time": secs}

        if action == "youtube.set_volume":
            lvl = args.get("level", 50)
            vol_float = float(lvl) / 100.0
            youtube_session.evaluate_sync(get_dom_volume_script(vol_float))
            return {"actuation_status": ActionStatus.LIVE_VERIFIED, "target_volume": vol_float}

        if action == "youtube.volume_up":
            step = args.get("step", 10)
            cur_v = plan.snapshot_before.player.volume
            cur_f = float(cur_v) if cur_v != "UNKNOWN" else 0.5
            target_f = min(1.0, cur_f + (float(step) / 100.0))
            youtube_session.evaluate_sync(get_dom_volume_script(target_f))
            return {"actuation_status": ActionStatus.LIVE_VERIFIED, "target_volume": target_f}

        if action == "youtube.volume_down":
            step = args.get("step", 10)
            cur_v = plan.snapshot_before.player.volume
            cur_f = float(cur_v) if cur_v != "UNKNOWN" else 0.5
            target_f = max(0.0, cur_f - (float(step) / 100.0))
            youtube_session.evaluate_sync(get_dom_volume_script(target_f))
            return {"actuation_status": ActionStatus.LIVE_VERIFIED, "target_volume": target_f}

        if action == "youtube.mute":
            youtube_session.evaluate_sync(get_dom_mute_script(True))
            return {"actuation_status": ActionStatus.LIVE_VERIFIED, "target_muted": True}

        if action == "youtube.unmute":
            youtube_session.evaluate_sync(get_dom_mute_script(False))
            return {"actuation_status": ActionStatus.LIVE_VERIFIED, "target_muted": False}

        if action == "youtube.set_playback_speed":
            rate = args.get("rate", 1.0)
            youtube_session.evaluate_sync(get_dom_playback_rate_script(rate))
            return {"actuation_status": ActionStatus.LIVE_VERIFIED, "target_rate": rate}

        if action == "youtube.speed_up":
            cur_r = plan.snapshot_before.player.playback_rate
            cur_f = float(cur_r) if cur_r != "UNKNOWN" else 1.0
            target_r = min(3.0, cur_f + float(args.get("step", 0.25)))
            youtube_session.evaluate_sync(get_dom_playback_rate_script(target_r))
            return {"actuation_status": ActionStatus.LIVE_VERIFIED, "target_rate": target_r}

        if action == "youtube.speed_down":
            cur_r = plan.snapshot_before.player.playback_rate
            cur_f = float(cur_r) if cur_r != "UNKNOWN" else 1.0
            target_r = max(0.25, cur_f - float(args.get("step", 0.25)))
            youtube_session.evaluate_sync(get_dom_playback_rate_script(target_r))
            return {"actuation_status": ActionStatus.LIVE_VERIFIED, "target_rate": target_r}

        # ── 6. Action: UI Controls (Phase 15 Pure DOM Controls) ─────────────
        if action in ["youtube.set_fullscreen", "youtube.fullscreen"]:
            en = args.get("enabled", True)
            youtube_session.evaluate_sync(get_dom_set_fullscreen_script(en))
            return {"actuation_status": ActionStatus.LIVE_VERIFIED, "target_fullscreen": en}

        if action == "youtube.set_theater_mode":
            en = args.get("enabled", True)
            youtube_session.evaluate_sync(get_dom_set_theater_script(en))
            return {"actuation_status": ActionStatus.LIVE_VERIFIED, "target_theater": en}

        if action == "youtube.set_miniplayer":
            en = args.get("enabled", True)
            youtube_session.evaluate_sync(get_dom_set_miniplayer_script(en))
            return {"actuation_status": ActionStatus.LIVE_VERIFIED, "target_miniplayer": en}

        if action in ["youtube.set_captions", "youtube.captions"]:
            en = args.get("enabled", True)
            youtube_session.evaluate_sync(get_dom_set_captions_script(en))
            return {"actuation_status": ActionStatus.LIVE_VERIFIED, "target_captions": en}

        if action in ["youtube.set_like", "youtube.like"]:
            en = args.get("enabled", True)
            youtube_session.evaluate_sync(get_dom_set_like_script(en))
            return {"actuation_status": ActionStatus.LIVE_VERIFIED, "target_like": en}

        if action in ["youtube.scroll", "scroll_page"]:
            dir_val = args.get("direction", "down")
            is_down = dir_val.lower() in ["down", "niche", "bottom", "neeche"]
            amt = int(args.get("amount", 500))
            delta = amt if is_down else -amt
            youtube_session.evaluate_sync(get_dom_scroll_script(delta))
            return {"actuation_status": ActionStatus.LIVE_VERIFIED, "scroll_delta": delta}

        if action in ["youtube.next_short", "next_short"]:
            youtube_session.evaluate_sync("""() => {
                const btn = document.querySelector('#navigation-button-down button, ytd-shorts [aria-label="Next video"], button[aria-label="Next short"]');
                if (btn) { btn.click(); return true; }
                window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', code: 'ArrowDown', keyCode: 40, bubbles: true }));
                return true;
            }""")
            return {"actuation_status": ActionStatus.LIVE_VERIFIED}

        if action in ["youtube.prev_short", "youtube.previous_short", "prev_short", "previous_short"]:
            youtube_session.evaluate_sync("""() => {
                const btn = document.querySelector('#navigation-button-up button, ytd-shorts [aria-label="Previous video"], button[aria-label="Previous short"]');
                if (btn) { btn.click(); return true; }
                window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowUp', code: 'ArrowUp', keyCode: 38, bubbles: true }));
                return true;
            }""")
            return {"actuation_status": ActionStatus.LIVE_VERIFIED}

        if action == "youtube.observe":
            return {"actuation_status": ActionStatus.LIVE_VERIFIED}

        return {"actuation_status": ActionStatus.UNSUPPORTED, "error": f"Action '{action}' unsupported"}


# Global singleton instance
youtube_executor = YouTubeExecutor()


def get_youtube_executor() -> YouTubeExecutor:
    """Return the global YouTubeExecutor singleton."""
    return youtube_executor
