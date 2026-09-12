"""Authoritative Action Planner for YouTube Runtime V3.

Implements Phase 11 & Phase 8 invariants:
- Always refreshes perception prior to resolving ordinals.
- Selects targets strictly from visible_videos / visible_shorts.
- If target ordinal does not exist on screen: returns TARGET_NOT_VISIBLE immediately.
- Strictly forbids falling back to resume(), guessing, or searching "first".
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional

from backend.core.logger import get_logger
from backend.youtube.models import (
    ActionStatus,
    PerceptionSnapshot,
    VisibleVideoItem,
)
from backend.youtube.perception import youtube_perception

logger = get_logger("YouTubePlannerV3")


@dataclass
class ExecutionPlan:
    action: str
    arguments: Dict[str, Any]
    snapshot_before: PerceptionSnapshot
    target_video: Optional[VisibleVideoItem] = None
    target_ordinal: Optional[int] = None
    aborted_status: Optional[ActionStatus] = None
    abort_message: Optional[str] = None


class YouTubePlanner:
    """Creates deterministic, perception-grounded execution plans."""

    def plan(
        self,
        canonical_action: str,
        arguments: Dict[str, Any],
        snapshot_before: Optional[PerceptionSnapshot] = None,
    ) -> ExecutionPlan:
        """Create a verified execution plan grounded in the live page snapshot."""
        # 1. Fresh perception observation before planning if not provided
        if snapshot_before is None:
            snapshot_before = youtube_perception.observe_fresh(force_refresh=True)

        # 2. Plan Standard Video Ordinal Selection (Phase 11)
        if canonical_action in ["youtube.play_video", "youtube.play_first_video"]:
            query = (arguments.get("query") or "").strip()
            ordinal = arguments.get("ordinal", 1)

            # If user specified a text query to play, treat as search + direct play
            if query:
                return ExecutionPlan(
                    action=canonical_action,
                    arguments=arguments,
                    snapshot_before=snapshot_before,
                )

            # Ordinal selection without query: resolve against visible videos
            visible_vids = snapshot_before.visible_videos
            cur_id = snapshot_before.current_video.video_id

            # If currently on a video page, exclude current playing video from recommended list
            if cur_id and cur_id != "UNKNOWN":
                visible_vids = [v for v in visible_vids if v.video_id != cur_id]

            if not visible_vids or len(visible_vids) < ordinal:
                logger.warning(f"Requested video ordinal {ordinal} not visible (found {len(visible_vids)} cards)")
                return ExecutionPlan(
                    action=canonical_action,
                    arguments=arguments,
                    snapshot_before=snapshot_before,
                    target_ordinal=ordinal,
                    aborted_status=ActionStatus.TARGET_NOT_VISIBLE,
                    abort_message=f"Video number {ordinal} screen par nahi dikh rahi hai Boss.",
                )

            target = visible_vids[ordinal - 1]
            return ExecutionPlan(
                action=canonical_action,
                arguments=arguments,
                snapshot_before=snapshot_before,
                target_video=target,
                target_ordinal=ordinal,
            )

        # 3. Plan Shorts Ordinal Selection (Phase 13)
        if canonical_action in ["youtube.play_short", "youtube.play_first_short"]:
            ordinal = arguments.get("ordinal", 1)
            visible_shorts = snapshot_before.visible_shorts

            if not visible_shorts or len(visible_shorts) < ordinal:
                logger.warning(f"Requested short ordinal {ordinal} not visible (found {len(visible_shorts)} cards)")
                return ExecutionPlan(
                    action=canonical_action,
                    arguments=arguments,
                    snapshot_before=snapshot_before,
                    target_ordinal=ordinal,
                    aborted_status=ActionStatus.TARGET_NOT_VISIBLE,
                    abort_message=f"Short number {ordinal} screen par nahi dikh raha hai Boss.",
                )

            target = visible_shorts[ordinal - 1]
            return ExecutionPlan(
                action=canonical_action,
                arguments=arguments,
                snapshot_before=snapshot_before,
                target_video=target,
                target_ordinal=ordinal,
            )

        # 4. Standard Direct Execution Plan
        return ExecutionPlan(
            action=canonical_action,
            arguments=arguments,
            snapshot_before=snapshot_before,
        )


# Global singleton instance
youtube_planner = YouTubePlanner()


def get_youtube_planner() -> YouTubePlanner:
    """Return the global YouTubePlanner singleton."""
    return youtube_planner
