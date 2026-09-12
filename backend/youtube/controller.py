"""Authoritative Single YouTube Controller for JARVIS YouTube Runtime V3.

Coordinates the unified, closed-loop pipeline:
VOICE / TEXT
    ↓
YOUTUBE NLU
    ↓
FRESH YOUTUBE PERCEPTION
    ↓
YOUTUBE PLANNER
    ↓
YOUTUBE EXECUTOR
    ↓
FRESH YOUTUBE PERCEPTION
    ↓
INTENT-SPECIFIC VERIFIER
    ↓
TRUTHFUL ACTION_RESULT
"""
import time
from typing import Any, Dict, List, Optional

from backend.core.logger import get_logger
from backend.youtube.diagnostics import youtube_diagnostics
from backend.youtube.executor import youtube_executor
from backend.youtube.models import (
    ActionResult,
    ActionStatus,
    PerceptionSnapshot,
)
from backend.youtube.perception import youtube_perception
from backend.youtube.planner import youtube_planner
from backend.youtube.session import youtube_session
from backend.youtube.verifier import youtube_verifier

logger = get_logger("YouTubeControllerV3")


class YouTubeController:
    """Master controller owning the authoritative single YouTube runtime."""

    def __init__(self):
        self.session = youtube_session
        self.perception = youtube_perception
        self.planner = youtube_planner
        self.executor = youtube_executor
        self.verifier = youtube_verifier
        self.diagnostics = youtube_diagnostics

    def execute_canonical(
        self,
        canonical_action: str,
        arguments: Optional[Dict[str, Any]] = None,
        raw_text: str = "",
    ) -> Dict[str, Any]:
        """Execute canonical action through the authoritative closed-loop pipeline."""
        args = arguments or {}
        start_t = time.time()
        logger.info(f"YouTubeController executing: {canonical_action} with args={args}")

        # ── 1. Plan Action Grounded in Fresh Perception ─────────────────────
        plan = self.planner.plan(canonical_action, args)
        snapshot_before = plan.snapshot_before

        # Handle early aborted plan (e.g. TARGET_NOT_VISIBLE)
        if plan.aborted_status:
            res = ActionResult(
                status=plan.aborted_status,
                verified=False,
                action=canonical_action,
                message=plan.abort_message or "Target not visible.",
                expected=plan.target_ordinal,
                observed=None,
                error=str(plan.aborted_status.value),
                generation=snapshot_before.generation,
                snapshot_before=snapshot_before.to_dict(),
            )
            self.diagnostics.log_structured_trace(
                command=raw_text,
                canonical_action=canonical_action,
                arguments=args,
                snapshot_before=snapshot_before,
                selected_target_id=None,
                execution_method="plan_aborted",
                snapshot_after=snapshot_before,
                verification_status=res.status.value,
            )
            return res.to_dict()

        # ── 2. Handle Read-Only Diagnostic Observation (Phase 24) ───────────
        if canonical_action == "youtube.observe":
            max_items = args.get("max_items", 5)
            summary = self.diagnostics.format_diagnostic_summary(snapshot_before, max_items=max_items)
            res = ActionResult(
                status=ActionStatus.LIVE_VERIFIED,
                verified=True,
                action=canonical_action,
                message=summary,
                expected="PAGE_OBSERVED",
                observed=snapshot_before.page_type.value,
                generation=snapshot_before.generation,
                snapshot_before=snapshot_before.to_dict(),
                snapshot_after=snapshot_before.to_dict(),
            )
            return res.to_dict()

        # ── 3. Execute Action Exclusively Through Browser/DOM ───────────────
        actuation_result = self.executor.execute(plan)
        exec_method = actuation_result.get("method", "DOM_CDP")

        # Invalidate perception cache after execution
        self.perception.invalidate_cache()
        time.sleep(0.3)

        # ── 4. Fresh Perception Observation Post-Action ─────────────────────
        snapshot_after = self.perception.observe_fresh(force_refresh=True)

        # ── 5. Intent-Specific Verification (Phase 17) ──────────────────────
        status, verified, message = self.verifier.verify(
            action=canonical_action,
            arguments=args,
            actuation_result=actuation_result,
            snapshot_before=snapshot_before,
            snapshot_after=snapshot_after,
        )

        selected_id = getattr(plan.target_video, "video_id", None) if plan.target_video else actuation_result.get("expected_video_id")

        action_res = ActionResult(
            status=status,
            verified=verified,
            action=canonical_action,
            message=message,
            expected=selected_id or actuation_result.get("expected"),
            observed=snapshot_after.current_video.video_id,
            error=actuation_result.get("error"),
            source="CDP",
            generation=snapshot_after.generation,
            snapshot_before=snapshot_before.to_dict(),
            snapshot_after=snapshot_after.to_dict(),
        )

        # ── 6. Log Structured Safe Operational Trace (Phase 25) ─────────────
        self.diagnostics.log_structured_trace(
            command=raw_text,
            canonical_action=canonical_action,
            arguments=args,
            snapshot_before=snapshot_before,
            selected_target_id=selected_id,
            execution_method=exec_method,
            snapshot_after=snapshot_after,
            verification_status=action_res.status.value,
        )

        out_dict = action_res.to_dict()
        out_dict["execution_time_ms"] = round((time.time() - start_t) * 1000, 1)
        out_dict["before_video_id"] = snapshot_before.current_video.video_id
        out_dict["after_video_id"] = snapshot_after.current_video.video_id
        return out_dict

    # ── Convenience Forwarding Methods ──────────────────────────────────────

    def open(self, query: str = "") -> Dict[str, Any]:
        return self.execute_canonical("youtube.open", {"query": query})

    def search(self, query: str) -> Dict[str, Any]:
        return self.execute_canonical("youtube.search", {"query": query})

    def play_video(self, query: str = "", ordinal: int = 1) -> Dict[str, Any]:
        return self.execute_canonical("youtube.play_video", {"query": query, "ordinal": ordinal})

    def play_first_video(self, ordinal: int = 1) -> Dict[str, Any]:
        return self.play_video(ordinal=ordinal)

    def play_short(self, ordinal: int = 1) -> Dict[str, Any]:
        return self.execute_canonical("youtube.play_short", {"ordinal": ordinal})

    def play_first_short(self, ordinal: int = 1) -> Dict[str, Any]:
        return self.play_short(ordinal=ordinal)

    def next_short(self) -> Dict[str, Any]:
        return self.execute_canonical("youtube.next_short")

    def prev_short(self) -> Dict[str, Any]:
        return self.execute_canonical("youtube.prev_short")

    def previous_short(self) -> Dict[str, Any]:
        return self.execute_canonical("youtube.previous_short")

    def pause(self) -> Dict[str, Any]:
        return self.execute_canonical("youtube.pause")

    def resume(self) -> Dict[str, Any]:
        return self.execute_canonical("youtube.resume")

    def play(self) -> Dict[str, Any]:
        return self.resume()

    def set_fullscreen(self, enabled: bool = True) -> Dict[str, Any]:
        return self.execute_canonical("youtube.set_fullscreen", {"enabled": enabled})

    def toggle_fullscreen(self) -> Dict[str, Any]:
        return self.set_fullscreen(True)

    def set_theater_mode(self, enabled: bool = True) -> Dict[str, Any]:
        return self.execute_canonical("youtube.set_theater_mode", {"enabled": enabled})

    def toggle_theater(self) -> Dict[str, Any]:
        return self.set_theater_mode(True)

    def set_miniplayer(self, enabled: bool = True) -> Dict[str, Any]:
        return self.execute_canonical("youtube.set_miniplayer", {"enabled": enabled})

    def toggle_miniplayer(self) -> Dict[str, Any]:
        return self.set_miniplayer(True)

    def set_captions(self, enabled: bool = True) -> Dict[str, Any]:
        return self.execute_canonical("youtube.set_captions", {"enabled": enabled})

    def toggle_captions(self) -> Dict[str, Any]:
        return self.set_captions(True)

    def set_playback_speed(self, rate: float = 1.0) -> Dict[str, Any]:
        return self.execute_canonical("youtube.set_playback_speed", {"rate": rate})

    def speed_up(self, step: float = 0.25) -> Dict[str, Any]:
        return self.execute_canonical("youtube.speed_up", {"step": step})

    def speed_down(self, step: float = 0.25) -> Dict[str, Any]:
        return self.execute_canonical("youtube.speed_down", {"step": step})

    def seek_forward(self, seconds: int = 10) -> Dict[str, Any]:
        return self.execute_canonical("youtube.seek_forward", {"seconds": seconds})

    def seek_backward(self, seconds: int = 10) -> Dict[str, Any]:
        return self.execute_canonical("youtube.seek_backward", {"seconds": seconds})

    def seek_timestamp(self, seconds: int = 0, raw_timestamp: str = "") -> Dict[str, Any]:
        return self.execute_canonical("youtube.seek_timestamp", {"seconds": seconds, "raw_timestamp": raw_timestamp})

    def set_volume(self, level: int = 50) -> Dict[str, Any]:
        return self.execute_canonical("youtube.set_volume", {"level": level})

    def volume_up(self, step: int = 10) -> Dict[str, Any]:
        return self.execute_canonical("youtube.volume_up", {"step": step})

    def volume_down(self, step: int = 10) -> Dict[str, Any]:
        return self.execute_canonical("youtube.volume_down", {"step": step})

    def mute(self) -> Dict[str, Any]:
        return self.execute_canonical("youtube.mute")

    def unmute(self) -> Dict[str, Any]:
        return self.execute_canonical("youtube.unmute")

    def set_like(self, enabled: bool = True) -> Dict[str, Any]:
        return self.execute_canonical("youtube.set_like", {"enabled": enabled})

    def like(self) -> Dict[str, Any]:
        return self.set_like(enabled=True)

    def replay(self) -> Dict[str, Any]:
        return self.execute_canonical("youtube.replay")

    def scroll(self, direction: str = "down", amount: int = 500) -> Dict[str, Any]:
        return self.execute_canonical("youtube.scroll", {"direction": direction, "amount": amount})

    def observe(self, max_items: int = 5, target: Optional[str] = None) -> Dict[str, Any]:
        return self.execute_canonical("youtube.observe", {"max_items": max_items, "target": target})

    execute = execute_canonical


# Global singleton instance
youtube_controller = YouTubeController()


def get_youtube_controller() -> YouTubeController:
    """Return the global YouTubeController singleton."""
    return youtube_controller

