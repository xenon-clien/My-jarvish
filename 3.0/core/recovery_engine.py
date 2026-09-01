"""JARVIS 3.0 - Retry & Multi-Tier Recovery Engine.

Coordinates bounded retries, strategy switching (e.g. direct URL -> DOM -> search fallback),
and graceful failure degradation without infinite retry loops.
"""
import asyncio
import time
from typing import Any, Callable, Dict, Optional

from core.logger import get_logger
from core.models import RetryPolicy, ToolExecutionResult, VerificationResult
from core.tool_contract import BaseTool

logger = get_logger("RecoveryEngine")


class RetryRecoveryEngine:
    """Executes a tool with strict closed-loop verification, bounded retries, and fallback methods."""

    async def execute_with_recovery(
        self,
        tool: BaseTool,
        arguments: Dict[str, Any],
        verify_callback: Optional[Callable[[ToolExecutionResult], Any]] = None,
    ) -> ToolExecutionResult:
        """Execute tool, verify outcome, retry on failure, switch to fallbacks, and report truthful status."""
        policy = tool.retry_policy or RetryPolicy()
        max_retries = policy.max_retries
        total_attempts = 1 + max_retries
        current_attempt = 1

        last_result: Optional[ToolExecutionResult] = None
        last_verif: Optional[VerificationResult] = None

        while current_attempt <= total_attempts:
            is_fallback = current_attempt > 1
            strategy_name = "primary" if not is_fallback else f"fallback_tier_{current_attempt-1}"

            logger.info(f"Executing tool '{tool.name}' (Attempt {current_attempt}/{total_attempts}, Strategy: {strategy_name})")

            # 1. Execute primary or fallback method
            if not is_fallback:
                result = await tool.execute(**arguments)
            else:
                result = await tool.fallback(attempt_number=current_attempt - 1, **arguments)
                # If tool didn't implement custom fallback, retry primary method
                if not result.success and "No fallback implementation" in (result.error or ""):
                    result = await tool.execute(**arguments)

            last_result = result

            # 2. Verify Execution Outcome
            if verify_callback:
                verif = await verify_callback(result)
            else:
                verif = await tool.verify(pre_state=None, post_state=None, tool_result=result, **arguments)

            last_verif = verif

            # 3. Check for genuine verified success
            if result.success and verif.is_verified:
                logger.info(f"Tool '{tool.name}' verified successfully on attempt {current_attempt}")
                result.strategy_used = strategy_name
                return result

            logger.warning(
                f"Tool '{tool.name}' attempt {current_attempt} failed or unverified. "
                f"Result success={result.success}, Verif={verif.is_verified}, Msg='{verif.message}'"
            )

            # 4. Check if further retries allowed
            if current_attempt < total_attempts:
                # Calculate backoff delay
                delay = policy.backoff_delay_seconds
                if policy.exponential_backoff:
                    delay = delay * (2 ** (current_attempt - 1))
                logger.info(f"Waiting {delay:.2f}s before next attempt...")
                await asyncio.sleep(delay)

            current_attempt += 1

        # All attempts exhausted
        final_error = last_result.error if last_result else "Action verification failed across all attempts."
        if last_verif and not last_verif.is_verified:
            final_error = f"{final_error} (Verification failed: {last_verif.message})"

        logger.error(f"Tool '{tool.name}' failed completely after {total_attempts} attempts. Error: {final_error}")
        return ToolExecutionResult(
            success=False,
            error=final_error,
            message=f"Boss, '{tool.name}' complete nahi ho paya retries ke baad.",
            strategy_used="all_exhausted",
        )


# Global RecoveryEngine singleton
recovery_engine = RetryRecoveryEngine()
