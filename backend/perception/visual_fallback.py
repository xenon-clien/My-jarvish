"""Optional Vision Model Fallback for Visual Screen Analysis.

Provides an optional hook for multimodal vision models (e.g. Gemini Vision).
Guarded strictly by JARVIS_ENABLE_REMOTE_SCREEN_VISION (default = 0 / OFF).
When disabled or unconfigured, explicitly returns VISION_MODEL_NOT_CONFIGURED.
"""
import os
from typing import Any, Dict, Optional
from backend.core.logger import get_logger

logger = get_logger("VisualFallback")


class VisualFallback:
    """Optional visual fallback interface for desktop/screen perception."""

    def is_enabled(self) -> bool:
        """Check whether remote screen vision is opted into."""
        val = os.environ.get("JARVIS_ENABLE_REMOTE_SCREEN_VISION", "0").strip().lower()
        return val in ("1", "true", "yes", "on")

    def analyze_screen(self, frame_data: Optional[Dict[str, Any]], task_prompt: str) -> Dict[str, Any]:
        """Analyze a screen capture frame with a vision model if enabled.
        
        Returns:
            Dict with status and observations or VISION_MODEL_NOT_CONFIGURED.
        """
        if not self.is_enabled():
            return {
                "status": "VISION_MODEL_NOT_CONFIGURED",
                "message": "Remote screen vision is disabled by default for privacy (JARVIS_ENABLE_REMOTE_SCREEN_VISION=0).",
                "observations": None,
            }

        if not frame_data:
            return {
                "status": "ERROR",
                "message": "No frame data provided for vision analysis.",
                "observations": None,
            }

        # If opted in, hook into AI provider
        logger.info(f"Visual analysis requested for task: '{task_prompt}'")
        return {
            "status": "VISION_MODEL_NOT_CONFIGURED",
            "message": "Vision provider model not configured.",
            "observations": None,
        }


# Global singleton
visual_fallback = VisualFallback()
