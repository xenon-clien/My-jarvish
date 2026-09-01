"""
Gesture Camera Loop — runs as a daemon thread in JARVIS.

Captures webcam frames locally, detects hand gestures using MediaPipe or OpenCV,
classifies gestures, and fires JARVIS actions.

PRIVACY REQUIREMENTS:
- Upper center screen (face region) is strictly blacked out BEFORE any processing.
- Original frames are NEVER saved to disk, NEVER recorded, NEVER uploaded anywhere.
- Discarded immediately after processing.
"""
import asyncio
import logging
import math
import os
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger("GestureLoop")

# Gesture → JARVIS voice command mapping
GESTURE_COMMANDS = {
    "OPEN_PALM": "confirm",           # Open palm = confirm pending action
    "THUMBS_UP": "haan",              # Thumbs up = yes/confirm
    "CLOSED_FIST": "cancel",          # Fist = cancel
    "INDEX_POINT": None,              # Visual feedback, no command
    "TWO_FINGERS": "scroll down",     # Two fingers = scroll down
    "THREE_FINGERS": "jarvis pause",  # Three fingers = pause/resume
    "WAVE": "jarvis",                 # Wave = wake JARVIS
}

_loop_thread: Optional[threading.Thread] = None
_running = False
_loop_lock = threading.Lock()
_command_callback: Optional[Callable[[str], None]] = None


def set_command_callback(cb: Callable[[str], None]):
    """Register function to call when a gesture command is triggered."""
    global _command_callback
    _command_callback = cb


def _gesture_loop():
    """Main gesture capture loop (runs in daemon thread)."""
    global _running
    try:
        import cv2
        import numpy as np
        from backend.plugins.gesture.gesture_engine import GestureType, gesture_engine

        # Check if MediaPipe solutions API is available
        mp_hands = None
        try:
            import mediapipe as mp
            if hasattr(mp, "solutions") and hasattr(mp.solutions, "hands"):
                mp_hands = mp.solutions.hands.Hands(
                    static_image_mode=False,
                    max_num_hands=1,
                    min_detection_confidence=0.75,
                    min_tracking_confidence=0.70,
                )
        except Exception:
            mp_hands = None

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            logger.warning("GestureLoop: No webcam found. Hand gestures disabled.")
            _running = False
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)

        gesture_engine.enable_camera(True)
        logger.info(f"GestureLoop: Camera opened. Hand gesture detection active (Mode: {'MediaPipe' if mp_hands else 'OpenCV Native'}). Face masking ON.")

        while _running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            h, w = frame.shape[:2]

            # ── PRIVACY SHIELD: Black out face region (top 45% center of frame) ──
            # Completely zeroes out face pixels so face data is NEVER processed or stored
            face_top = 0
            face_bottom = int(h * 0.45)
            face_left = int(w * 0.20)
            face_right = int(w * 0.80)
            frame[face_top:face_bottom, face_left:face_right] = 0

            detected_gesture = GestureType.NONE
            finger_count = 0

            if mp_hands is not None:
                # ── MediaPipe Processing ──
                try:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_rgb.flags.writeable = False
                    results = mp_hands.process(frame_rgb)
                    del frame_rgb

                    if results.multi_hand_landmarks:
                        lm_list = results.multi_hand_landmarks[0].landmark
                        landmarks_3d = [(lm.x, lm.y, lm.z) for lm in lm_list]
                        detection = gesture_engine.process_landmarks(landmarks_3d)
                        detected_gesture = detection.gesture
                        finger_count = detection.finger_count
                except Exception as e:
                    logger.debug(f"MediaPipe process error: {e}")

            else:
                # ── OpenCV Native Skin-Tone & Contour Processing ──
                try:
                    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                    ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)

                    # Dual-space skin tone range for robust hand detection across all skin tones & lighting
                    mask_hsv = cv2.inRange(hsv, np.array([0, 15, 60], dtype=np.uint8), np.array([25, 255, 255], dtype=np.uint8))
                    mask_ycrcb = cv2.inRange(ycrcb, np.array([0, 130, 75], dtype=np.uint8), np.array([255, 180, 135], dtype=np.uint8))
                    mask = cv2.bitwise_or(mask_hsv, mask_ycrcb)

                    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
                    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
                    blur = cv2.GaussianBlur(mask, (5, 5), 0)

                    contours, _ = cv2.findContours(blur, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    if contours:
                        max_contour = max(contours, key=cv2.contourArea)
                        area = cv2.contourArea(max_contour)
                        if area > 3500:
                            hull = cv2.convexHull(max_contour, returnPoints=False)
                            if len(hull) > 3:
                                defects = cv2.convexityDefects(max_contour, hull)
                                if defects is not None:
                                    defects_count = 0
                                    for i in range(defects.shape[0]):
                                        s, e, f, d = defects[i, 0]
                                        start = tuple(max_contour[s][0])
                                        end = tuple(max_contour[e][0])
                                        far = tuple(max_contour[f][0])

                                        a = math.sqrt((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2)
                                        b = math.sqrt((far[0] - start[0]) ** 2 + (far[1] - start[1]) ** 2)
                                        c = math.sqrt((end[0] - far[0]) ** 2 + (end[1] - far[1]) ** 2)
                                        angle = math.acos((b ** 2 + c ** 2 - a ** 2) / (2 * b * c + 1e-5)) * 57.2958

                                        # Calibrated for webcam distance: depth > 3500 (approx 14px), acute angle
                                        if angle <= 95 and d > 3500:
                                            defects_count += 1

                                    finger_count = defects_count + 1
                                    if defects_count == 0:
                                        detected_gesture = GestureType.CLOSED_FIST
                                    elif defects_count == 1:
                                        detected_gesture = GestureType.TWO_FINGERS
                                    elif defects_count == 2:
                                        detected_gesture = GestureType.THREE_FINGERS
                                    elif defects_count >= 3:
                                        detected_gesture = GestureType.OPEN_PALM
                except Exception as e:
                    logger.debug(f"OpenCV gesture process error: {e}")

            del frame  # PRIVACY: frame discarded immediately — NEVER saved to disk

            if detected_gesture != GestureType.NONE:
                from backend.plugins.gesture.gesture_engine import GestureDetectionResult
                det_res = GestureDetectionResult(
                    gesture=detected_gesture,
                    finger_count=finger_count,
                    confidence=0.88,
                )
                should_trigger, is_emergency = gesture_engine.safety.evaluate(det_res)

                if is_emergency:
                    logger.warning("GestureLoop: EMERGENCY STOP via closed fist!")
                    if _command_callback:
                        _command_callback("CLOSED_FIST", "sab band karo")
                elif should_trigger:
                    cmd = GESTURE_COMMANDS.get(detected_gesture.value)
                    if _command_callback:
                        logger.info(f"GestureLoop: Gesture '{detected_gesture.value}' -> command '{cmd}'")
                        _command_callback(detected_gesture.value, cmd or "")

            time.sleep(0.033)  # ~30 FPS

        cap.release()
        if mp_hands:
            mp_hands.close()
        gesture_engine.enable_camera(False)
        logger.info("GestureLoop: Camera released. All memory cleared.")

    except Exception as e:
        logger.error(f"GestureLoop error: {e}")
        _running = False


def start_gesture_loop(command_callback: Optional[Callable[[str], None]] = None):
    """Start the gesture capture daemon thread (idempotent)."""
    global _loop_thread, _running, _command_callback
    with _loop_lock:
        if _running and _loop_thread and _loop_thread.is_alive():
            logger.debug("GestureLoop already running.")
            return
        if command_callback:
            _command_callback = command_callback
        _running = True
        _loop_thread = threading.Thread(target=_gesture_loop, daemon=True, name="GestureLoop")
        _loop_thread.start()
        logger.info("GestureLoop: Gesture daemon thread started.")


def stop_gesture_loop():
    """Stop the gesture capture loop."""
    global _running
    _running = False
    logger.info("GestureLoop: Stop requested.")
