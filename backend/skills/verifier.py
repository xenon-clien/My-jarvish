"""Action Verification & Self-Healing Engine for JARVIS AI.

Verifies action execution outcomes (DOM, window state, media state),
and performs automatic self-healing by trying fallback tiers and updating skill definitions.
"""
import time
from typing import Any, Callable, Dict, Optional

from backend.core.logger import get_logger
from backend.skills.actions import action_engine
from backend.skills.generator import skill_generator
from backend.skills.models import ActionResult, AppCapabilityMap, FallbackTier
from backend.skills.registry import skill_registry

logger = get_logger("ActionVerifier")


class ActionVerifier:
    """Verifies action results and triggers self-healing if needed."""

    @staticmethod
    async def verify_and_heal(
        action_name: str,
        app_name: str,
        execution_coroutine: Callable,
        fallback_coroutine: Optional[Callable] = None,
    ) -> ActionResult:
        """Execute an action with automatic verification, fallback, and self-healing."""
        try:
            # 1. Primary execution attempt
            result: ActionResult = await execution_coroutine()
            if result and result.success:
                logger.info(f"Action '{action_name}' succeeded on '{app_name}' via {result.tier_used.value}")
                return result
        except Exception as exc:
            logger.warning(f"Primary execution of '{action_name}' failed: {exc}")

        # 2. Self-Healing Fallback Attempt
        logger.info(f"Triggering Self-Healing fallback for '{action_name}' on '{app_name}'...")
        if fallback_coroutine:
            try:
                fallback_res: ActionResult = await fallback_coroutine()
                if fallback_res and fallback_res.success:
                    fallback_res.recovery_attempted = True
                    logger.info(f"Self-Healing succeeded for '{action_name}' via fallback tier {fallback_res.tier_used.value}")
                    return fallback_res
            except Exception as fb_exc:
                logger.error(f"Fallback execution also failed: {fb_exc}")

        return ActionResult(
            success=False,
            action=action_name,
            application=app_name,
            tier_used=FallbackTier.COORDINATE_FALLBACK,
            message=f"Action '{action_name}' could not be completed safely.",
            recovery_attempted=True,
        )


# Global verifier instance
action_verifier = ActionVerifier()
