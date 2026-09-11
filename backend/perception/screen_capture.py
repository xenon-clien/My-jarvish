"""Secondary Screen Capture Layer for JARVIS EYES V1.

Provides on-demand single frame capture using mss (with fallback to PIL/Win32)
to inspect overlays, popups, cookie consent dialogs, or rendering failures.
Frames are transient, kept purely in-memory, and never recorded or saved to disk.
"""
from typing import Any, Dict, Optional, Tuple
from backend.core.logger import get_logger

logger = get_logger("ScreenCapture")

try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False


class ScreenCapture:
    """On-demand screen perception provider."""

    def __init__(self):
        self._sct = None

    def capture_frame(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[Dict[str, Any]]:
        """Capture a single instantaneous frame in-memory.
        
        Args:
            region: Optional (left, top, right, bottom) bounding rectangle.
                    If None, captures primary monitor.
        
        Returns:
            Dict containing width, height, raw RGB bytes or None on error.
        """
        # Primary: mss
        if MSS_AVAILABLE:
            try:
                with mss.mss() as sct:
                    if region:
                        l, t, r, b = region
                        bbox = {"left": int(l), "top": int(t), "width": int(r - l), "height": int(b - t)}
                        shot = sct.grab(bbox)
                    else:
                        shot = sct.grab(sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0])
                    return {
                        "width": shot.width,
                        "height": shot.height,
                        "rgb_bytes": shot.rgb,
                        "format": "RGB",
                        "source": "mss",
                    }
            except Exception as exc:
                logger.debug(f"mss screen capture failed: {exc}")

        # Secondary: PIL ImageGrab fallback
        try:
            from PIL import ImageGrab
            bbox = (region[0], region[1], region[2], region[3]) if region else None
            img = ImageGrab.grab(bbox=bbox)
            return {
                "width": img.width,
                "height": img.height,
                "rgb_bytes": img.convert("RGB").tobytes(),
                "format": "RGB",
                "source": "PIL",
            }
        except Exception as exc:
            logger.debug(f"PIL ImageGrab fallback failed: {exc}")

        return None


# Global singleton
screen_capture = ScreenCapture()
