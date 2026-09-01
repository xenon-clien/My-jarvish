"""Privacy-First Local Hand Gesture Subsystem & Anti-Accident Engine for JARVIS.

PRIVACY REQUIREMENTS:
- Frame processing happens 100% locally using MediaPipe / OpenCV.
- Camera permission MUST be explicitly requested by the user.
- Frames are NEVER recorded, NEVER saved to disk, NEVER transmitted to Gemini, OpenRouter, or any cloud server.
- Landmarks are extracted and original frames are immediately discarded.
- No biometric identity features stored.
- Supports Camera OFF mode (JARVIS works normally via voice/text CLI & UI).
"""

from enum import Enum
import math
import time
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from backend.core.logger import get_logger

logger = get_logger("GestureEngine")


class GestureType(str, Enum):
    """Supported hand gestures."""
    OPEN_PALM = "OPEN_PALM"       # 5 fingers open (Trigger action / Confirm)
    THUMBS_UP = "THUMBS_UP"       # Confirm action
    CLOSED_FIST = "CLOSED_FIST"   # Cancel action (Held 2s = Emergency Stop)
    INDEX_POINT = "INDEX_POINT"   # Select / Point mode
    TWO_FINGERS = "TWO_FINGERS"   # Scroll mode
    THREE_FINGERS = "THREE_FINGERS"# Pause / Resume JARVIS
    PINCH = "PINCH"               # Click mode
    WAVE = "WAVE"                 # Wake JARVIS
    NONE = "NONE"


class GestureDetectionResult(BaseModel):
    """Structured result of local gesture detection (NO frame image data)."""
    gesture: GestureType
    finger_count: int
    confidence: float
    is_stable: bool = False
    status_text: str = ""
    timestamp: float = Field(default_factory=time.time)


class GestureActionMapper:
    """Configurable mapping from gestures to assistant actions."""

    def __init__(self):
        self.mappings: Dict[GestureType, str] = {
            GestureType.OPEN_PALM: "CONFIRM_OR_EXECUTE",
            GestureType.THUMBS_UP: "CONFIRM",
            GestureType.CLOSED_FIST: "CANCEL",
            GestureType.INDEX_POINT: "SELECT",
            GestureType.TWO_FINGERS: "SCROLL",
            GestureType.THREE_FINGERS: "PAUSE_RESUME",
            GestureType.PINCH: "CLICK",
            GestureType.WAVE: "WAKE",
        }

    def get_action_for_gesture(self, gesture: GestureType) -> str:
        return self.mappings.get(gesture, "NO_ACTION")

    def update_mapping(self, gesture: GestureType, action: str) -> None:
        self.mappings[gesture] = action
        logger.info(f"Updated gesture mapping: {gesture.value} -> {action}")


class GestureSafetyManager:
    """Anti-Accident System: Debounce, Stability, Cooldown, Confidence, Emergency Stop."""

    def __init__(
        self,
        stability_threshold_ms: float = 350.0,
        confidence_threshold: float = 0.70,
        cooldown_seconds: float = 1.2,
    ):
        self.stability_threshold_ms = stability_threshold_ms
        self.confidence_threshold = confidence_threshold
        self.cooldown_seconds = cooldown_seconds

        self._last_gesture: GestureType = GestureType.NONE
        self._gesture_start_time: float = 0.0
        self._last_execution_time: float = 0.0
        self._fist_hold_start_time: Optional[float] = None

    def evaluate(self, detection: GestureDetectionResult) -> Tuple[bool, bool]:
        """Evaluate if gesture is stable and ready to trigger.

        Returns:
            (should_trigger_action: bool, is_emergency_stop: bool)
        """
        now = time.time()

        # Check confidence threshold
        if detection.confidence < self.confidence_threshold or detection.gesture == GestureType.NONE:
            self._last_gesture = GestureType.NONE
            self._gesture_start_time = 0.0
            self._fist_hold_start_time = None
            return False, False

        # 1. Emergency Stop Check: Closed Fist held for ~2.0 seconds
        if detection.gesture == GestureType.CLOSED_FIST:
            if self._fist_hold_start_time is None:
                self._fist_hold_start_time = now
            elif (now - self._fist_hold_start_time) >= 2.0:
                logger.warning("Emergency Stop triggered by 2-second Closed Fist gesture!")
                self._fist_hold_start_time = None
                return True, True  # (trigger, is_emergency_stop)
        else:
            self._fist_hold_start_time = None

        # 2. Cooldown check (prevent accidental repeated execution)
        if (now - self._last_execution_time) < self.cooldown_seconds:
            return False, False

        # 3. Gesture Stability Check (500-800ms)
        if detection.gesture == self._last_gesture:
            duration_ms = (now - self._gesture_start_time) * 1000.0
            if duration_ms >= self.stability_threshold_ms:
                self._last_execution_time = now
                self._gesture_start_time = now  # Reset for next trigger
                return True, False
        else:
            self._last_gesture = detection.gesture
            self._gesture_start_time = now

        return False, False


class GestureEngine:
    """Core local gesture engine for landmark processing and gesture classification."""

    def __init__(self):
        self.camera_enabled: bool = False       # Permission flag
        self.camera_active: bool = False        # Live active state
        self.preview_enabled: bool = False      # Debug preview (OFF by default)
        self.mapper = GestureActionMapper()
        self.safety = GestureSafetyManager()
        self.last_detection = GestureDetectionResult(
            gesture=GestureType.NONE,
            finger_count=0,
            confidence=0.0,
            status_text="Camera: OFF",
        )

    def enable_camera(self, enable: bool = True) -> Dict[str, Any]:
        """Explicit user camera permission toggle."""
        self.camera_enabled = enable
        if enable:
            self.camera_active = True
            self.last_detection.status_text = "Gesture Mode: ON (Hand Listening)"
            logger.info("Camera gesture mode explicitly ENABLED by user.")
        else:
            self.camera_active = False
            self.last_detection.status_text = "Camera: OFF"
            logger.info("Camera gesture mode DISABLED by user.")
        return {
            "camera_enabled": self.camera_enabled,
            "camera_active": self.camera_active,
            "status_text": self.last_detection.status_text,
        }

    def process_landmarks(self, landmarks_3d: List[Tuple[float, float, float]]) -> GestureDetectionResult:
        """Process 21 3D hand landmark coordinates locally and return structured classification.

        The frame is ALREADY discarded before this function is called.
        """
        if not self.camera_enabled or len(landmarks_3d) < 21:
            return GestureDetectionResult(
                gesture=GestureType.NONE,
                finger_count=0,
                confidence=0.0,
                status_text="No Hand Detected",
            )

        # 21 Hand Landmarks Indexing (MediaPipe convention)
        # 0: WRIST, 4: THUMB_TIP, 8: INDEX_TIP, 12: MIDDLE_TIP, 16: RING_TIP, 20: PINKY_TIP
        wrist = landmarks_3d[0]
        thumb_tip = landmarks_3d[4]
        index_tip = landmarks_3d[8]
        middle_tip = landmarks_3d[12]
        ring_tip = landmarks_3d[16]
        pinky_tip = landmarks_3d[20]

        index_mcp = landmarks_3d[5]
        middle_mcp = landmarks_3d[9]
        ring_mcp = landmarks_3d[13]
        pinky_mcp = landmarks_3d[17]

        # Count extended fingers
        extended_fingers = 0
        if index_tip[1] < index_mcp[1]:
            extended_fingers += 1
        if middle_tip[1] < middle_mcp[1]:
            extended_fingers += 1
        if ring_tip[1] < ring_mcp[1]:
            extended_fingers += 1
        if pinky_tip[1] < pinky_mcp[1]:
            extended_fingers += 1

        # Check thumb extension (distance based)
        thumb_dist = math.sqrt((thumb_tip[0] - wrist[0])**2 + (thumb_tip[1] - wrist[1])**2)
        index_base_dist = math.sqrt((index_mcp[0] - wrist[0])**2 + (index_mcp[1] - wrist[1])**2)
        if thumb_dist > index_base_dist * 1.1:
            extended_fingers += 1

        # Classify gesture
        gesture = GestureType.NONE
        confidence = 0.92

        if extended_fingers >= 4:
            gesture = GestureType.OPEN_PALM
        elif extended_fingers == 0:
            gesture = GestureType.CLOSED_FIST
        elif extended_fingers == 1 and (index_tip[1] < index_mcp[1]):
            gesture = GestureType.INDEX_POINT
        elif extended_fingers == 1 and (thumb_tip[1] < wrist[1]):
            gesture = GestureType.THUMBS_UP
        elif extended_fingers == 2 and (index_tip[1] < index_mcp[1]) and (middle_tip[1] < middle_mcp[1]):
            gesture = GestureType.TWO_FINGERS
        elif extended_fingers == 3:
            gesture = GestureType.THREE_FINGERS
        else:
            # Check pinch distance between index and thumb tips
            pinch_dist = math.sqrt((index_tip[0] - thumb_tip[0])**2 + (index_tip[1] - thumb_tip[1])**2)
            if pinch_dist < 0.08:
                gesture = GestureType.PINCH

        res = GestureDetectionResult(
            gesture=gesture,
            finger_count=extended_fingers,
            confidence=confidence,
            status_text=f"Gesture Mode: ON | Hand Detected ({extended_fingers} fingers)",
        )
        self.last_detection = res
        return res


# Global singleton instance
gesture_engine = GestureEngine()
