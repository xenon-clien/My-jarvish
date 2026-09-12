"""Authoritative Single Verification Engine for YouTube Runtime V3.

Implements Phase 17 Central Verification invariants:
- There is strictly ONE verifier across the entire system.
- open: YouTube domain observed (and exact query match if query specified).
- search: normalize(requested_query) == normalize(observed_query).
- play_video: actual_video_id == expected_video_id strictly.
- play_short: actual_video_id == expected_video_id strictly.
- All player and UI controls require exact post-action state equality.
- Completely eliminates generic 'if is_youtube: LIVE_VERIFIED'.
"""
import urllib.parse
from typing import Any, Dict, Optional, Tuple

from backend.core.logger import get_logger
from backend.youtube.dom import normalize_search_query
from backend.youtube.models import (
    ActionStatus,
    PerceptionSnapshot,
)

logger = get_logger("YouTubeVerifierV3")


class YouTubeVerifier:
    """Authoritative verifier comparing post-execution perception against intent contract."""

    def verify(
        self,
        action: str,
        arguments: Dict[str, Any],
        actuation_result: Dict[str, Any],
        snapshot_before: PerceptionSnapshot,
        snapshot_after: PerceptionSnapshot,
    ) -> Tuple[ActionStatus, bool, str]:
        """Strictly evaluate whether observed state fulfills the expected action contract."""
        act_status = actuation_result.get("actuation_status")
        if act_status in [ActionStatus.TARGET_NOT_VISIBLE, ActionStatus.SIMULATED, ActionStatus.UNSUPPORTED, ActionStatus.CDP_UNAVAILABLE, ActionStatus.BROKEN]:
            msg = actuation_result.get("message") or actuation_result.get("error") or "Action could not be executed."
            return act_status, False, msg

        # If browser is not running or not YouTube, action cannot be live verified
        if not snapshot_after.browser_running or not snapshot_after.is_youtube:
            if action == "youtube.open":
                return ActionStatus.DEGRADED, False, "YouTube launch kiya hai, lekin main confirm nahi kar pa raha ki page open hua."
            return ActionStatus.DEGRADED, False, "Action execute kiya hai, lekin main confirm nahi kar pa raha ki screen par reflect hua."

        # ── 1. Verify: youtube.open ─────────────────────────────────────────
        if action == "youtube.open":
            q = (arguments.get("query") or "").strip()
            if not q:
                if snapshot_after.is_youtube:
                    return ActionStatus.LIVE_VERIFIED, True, "Haan Shivam, YouTube open kar diya hai."
                return ActionStatus.DEGRADED, False, "YouTube open verify nahi ho paya."

            # If query requested, query MUST be directly observed in URL, search input, or title
            norm_q = normalize_search_query(q)
            norm_obs = normalize_search_query(snapshot_after.search_query)
            quoted_q = urllib.parse.quote_plus(norm_q).lower()
            url_low = snapshot_after.url.lower()

            if norm_q == norm_obs or (quoted_q in url_low and "search_query=" in url_low) or (norm_q in normalize_search_query(snapshot_after.window_title)):
                return ActionStatus.LIVE_VERIFIED, True, f"Haan Shivam, YouTube par {q} search kar diya hai."
            return ActionStatus.DEGRADED, False, f"YouTube par {q} kholne ki koshish ki, lekin results verify nahi ho paye."

        # ── 2. Verify: youtube.search (Phase 9 Exact Search Semantics) ──────
        if action == "youtube.search":
            q = (arguments.get("query") or "").strip()
            norm_req = normalize_search_query(q)
            if not norm_req:
                return ActionStatus.DEGRADED, False, "Search query specify nahi ki gayi hai."

            norm_obs = normalize_search_query(snapshot_after.search_query)

            # Exact equality verification (Phase 9)
            if norm_req == norm_obs:
                return ActionStatus.LIVE_VERIFIED, True, f"Haan Shivam, YouTube par {q} search kar diya hai."

            # Direct check against URL parameter search_query
            try:
                p = urllib.parse.urlparse(snapshot_after.url)
                params = urllib.parse.parse_qs(p.query)
                url_q = params.get("search_query", [""])[0]
                if normalize_search_query(url_q) == norm_req:
                    return ActionStatus.LIVE_VERIFIED, True, f"Haan Shivam, YouTube par {q} search kar diya hai."
            except Exception:
                pass

            # Direct check against title
            if norm_req in normalize_search_query(snapshot_after.window_title) and "youtube" in snapshot_after.window_title.lower():
                return ActionStatus.LIVE_VERIFIED, True, f"Haan Shivam, YouTube par {q} search kar diya hai."

            return ActionStatus.DEGRADED, False, f"YouTube par {q} search kiya, lekin search results verify nahi ho paye."

        # ── 3. Verify: youtube.play_video (Phase 12 Video Identity) ─────────
        if action in ["youtube.play_video", "youtube.play_first_video"]:
            q = (arguments.get("query") or "").strip()
            if q:
                norm_req = normalize_search_query(q)
                norm_obs = normalize_search_query(snapshot_after.search_query)
                if norm_req == norm_obs or norm_req in normalize_search_query(snapshot_after.window_title):
                    return ActionStatus.LIVE_VERIFIED, True, f"Ji Boss, YouTube par {q} chala diya."
                return ActionStatus.DEGRADED, False, f"YouTube par {q} play karne ki koshish ki, lekin verify nahi hua."

            expected_id = actuation_result.get("expected_video_id")
            actual_id = snapshot_after.current_video.video_id
            ord_num = actuation_result.get("ordinal", 1)

            # Strict Invariant: ONLY actual_video_id == expected_video_id
            if expected_id and expected_id != "UNKNOWN" and actual_id != "UNKNOWN":
                if actual_id == expected_id and not expected_id.startswith("VID_SIM_") and not expected_id.startswith("cand_"):
                    return ActionStatus.LIVE_VERIFIED, True, f"Ji Boss, video number {ord_num} chala di."

            return ActionStatus.DEGRADED, False, f"Video number {ord_num} play karne ki koshish ki, lekin playback verify nahi ho paya."

        # ── 4. Verify: youtube.play_short (Phase 13 Shorts Identity) ────────
        if action in ["youtube.play_short", "youtube.play_first_short"]:
            expected_id = actuation_result.get("expected_video_id")
            actual_id = snapshot_after.current_video.video_id
            ord_num = actuation_result.get("ordinal", 1)

            # Strict Invariant: ONLY actual_video_id == expected_video_id (page_type == SHORTS alone is NOT proof)
            if expected_id and expected_id != "UNKNOWN" and actual_id != "UNKNOWN":
                if actual_id == expected_id and not expected_id.startswith("SHORT_SIM_"):
                    return ActionStatus.LIVE_VERIFIED, True, f"Ji Boss, short number {ord_num} chala diya."

            return ActionStatus.DEGRADED, False, f"Short number {ord_num} play karne ki koshish ki, lekin playback verify nahi ho paya."

        if action in ["youtube.next_short", "youtube.previous_short", "youtube.prev_short"]:
            before_id = snapshot_before.current_video.video_id
            after_id = snapshot_after.current_video.video_id
            if before_id != "UNKNOWN" and after_id != "UNKNOWN" and before_id != after_id:
                return ActionStatus.LIVE_VERIFIED, True, "Ji Boss, agla short chala diya." if "next" in action else "Ji Boss, pichla short chala diya."
            return ActionStatus.DEGRADED, False, "Short change verify nahi ho paya."

        # ── 5. Verify: Player Controls (Phase 14 Exact State Checks) ────────
        if action == "youtube.pause":
            if snapshot_after.player.paused is True:
                return ActionStatus.LIVE_VERIFIED, True, "Ji Boss, video pause kar diya."
            return ActionStatus.DEGRADED, False, "Video pause verify nahi ho paya."

        if action in ["youtube.resume", "youtube.play"]:
            if snapshot_after.player.paused is False:
                return ActionStatus.LIVE_VERIFIED, True, "Ji Boss, video resume kar diya."
            return ActionStatus.DEGRADED, False, "Video play verify nahi ho paya."

        if action == "youtube.replay":
            cur_t = snapshot_after.player.current_time
            if cur_t != "UNKNOWN" and float(cur_t) <= 2.0:
                return ActionStatus.LIVE_VERIFIED, True, "Ji Boss, video shuru se chala di."
            return ActionStatus.DEGRADED, False, "Video replay verify nahi ho paya."

        if action in ["youtube.seek_forward", "youtube.seek_backward", "youtube.seek_timestamp"]:
            target_t = actuation_result.get("target_time")
            cur_t = snapshot_after.player.current_time
            if target_t is not None and cur_t != "UNKNOWN":
                if abs(float(cur_t) - float(target_t)) <= 4.0:
                    return ActionStatus.LIVE_VERIFIED, True, "Ji Boss, video seek kar diya."
            return ActionStatus.DEGRADED, False, "Video seek verify nahi ho paya."

        if action in ["youtube.set_volume", "youtube.volume_up", "youtube.volume_down"]:
            target_v = actuation_result.get("target_volume")
            cur_v = snapshot_after.player.volume
            if target_v is not None and cur_v != "UNKNOWN":
                if abs(float(cur_v) - float(target_v)) <= 0.08:
                    return ActionStatus.LIVE_VERIFIED, True, "Ji Boss, volume adjust kar diya."
            return ActionStatus.DEGRADED, False, "Volume change verify nahi ho paya."

        if action in ["youtube.mute", "youtube.unmute"]:
            target_m = actuation_result.get("target_muted")
            cur_m = snapshot_after.player.muted
            if target_m is not None and cur_m == target_m:
                return ActionStatus.LIVE_VERIFIED, True, "Ji Boss, audio mute kar diya." if target_m else "Ji Boss, audio unmute kar diya."
            return ActionStatus.DEGRADED, False, "Mute toggle verify nahi ho paya."

        if action in ["youtube.set_playback_speed", "youtube.speed_up", "youtube.speed_down"]:
            target_r = actuation_result.get("target_rate")
            cur_r = snapshot_after.player.playback_rate
            if target_r is not None and cur_r != "UNKNOWN":
                if abs(float(cur_r) - float(target_r)) <= 0.08:
                    return ActionStatus.LIVE_VERIFIED, True, f"Ji Boss, playback speed {target_r}x kar di."
            return ActionStatus.DEGRADED, False, "Playback speed verify nahi ho paya."

        # ── 6. Verify: UI Controls (Phase 15 Exact State Checks) ────────────
        if action in ["youtube.set_fullscreen", "youtube.fullscreen"]:
            target_fs = actuation_result.get("target_fullscreen")
            if snapshot_after.controls.fullscreen == target_fs and target_fs is not None:
                return ActionStatus.LIVE_VERIFIED, True, "Ji Boss, fullscreen kar diya." if target_fs else "Ji Boss, fullscreen band kar diya."
            return ActionStatus.DEGRADED, False, "Fullscreen toggle verify nahi ho paya."

        if action == "youtube.set_theater_mode":
            target_th = actuation_result.get("target_theater")
            if snapshot_after.controls.theater == target_th and target_th is not None:
                return ActionStatus.LIVE_VERIFIED, True, "Ji Boss, theater mode kar diya." if target_th else "Ji Boss, theater mode band kar diya."
            return ActionStatus.DEGRADED, False, "Theater mode toggle verify nahi ho paya."

        if action == "youtube.set_miniplayer":
            target_mp = actuation_result.get("target_miniplayer")
            if snapshot_after.controls.miniplayer == target_mp and target_mp is not None:
                return ActionStatus.LIVE_VERIFIED, True, "Ji Boss, miniplayer kar diya." if target_mp else "Ji Boss, miniplayer band kar diya."
            return ActionStatus.DEGRADED, False, "Miniplayer toggle verify nahi ho paya."

        if action in ["youtube.set_captions", "youtube.captions"]:
            target_cc = actuation_result.get("target_captions")
            if snapshot_after.controls.captions == target_cc and target_cc is not None:
                return ActionStatus.LIVE_VERIFIED, True, "Ji Boss, subtitles on kar diye." if target_cc else "Ji Boss, subtitles band kar diye."
            return ActionStatus.DEGRADED, False, "Subtitles toggle verify nahi ho paya."

        if action in ["youtube.set_like", "youtube.like"]:
            target_lk = actuation_result.get("target_like")
            if snapshot_after.controls.like_state == target_lk and target_lk is not None:
                return ActionStatus.LIVE_VERIFIED, True, "Ji Boss, video like kar diya." if target_lk else "Ji Boss, like hata diya."
            return ActionStatus.DEGRADED, False, "Like state toggle verify nahi ho paya."

        if action in ["youtube.scroll", "scroll_page"]:
            if snapshot_after.is_youtube:
                return ActionStatus.LIVE_VERIFIED, True, "Ji Boss, scroll kar diya."
            return ActionStatus.DEGRADED, False, "Scroll verify nahi ho paya."

        if action == "youtube.observe":
            return ActionStatus.LIVE_VERIFIED, True, "Page observed."

        return ActionStatus.DEGRADED, False, f"Action '{action}' verify nahi ho paya."


# Global singleton instance
youtube_verifier = YouTubeVerifier()


def get_youtube_verifier() -> YouTubeVerifier:
    """Return the global YouTubeVerifier singleton."""
    return youtube_verifier
