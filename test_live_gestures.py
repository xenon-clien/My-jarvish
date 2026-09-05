import cv2
import numpy as np
import time
import math
import sys
sys.path.insert(0, r"c:\Users\shivam\Downloads\chatbot")

print("=== HAND GESTURE CAMERA PERMANENTLY DISABLED ===")
print("Camera access has been disabled for user privacy.")
sys.exit(0)

print("Webcam opened successfully! Hold your hand (Open Palm or Fist) in front of camera for 5 seconds...")

start = time.time()
frame_count = 0
gesture_counts = {}

while time.time() - start < 5.0:
    ret, frame = cap.read()
    if not ret:
        time.sleep(0.03)
        continue
    frame_count += 1
    h, w = frame.shape[:2]

    # Mask face area
    frame[0:int(h * 0.40), int(w * 0.25):int(w * 0.75)] = 0

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)

    # Skin masks
    mask_hsv = cv2.inRange(hsv, np.array([0, 20, 50], dtype=np.uint8), np.array([30, 255, 255], dtype=np.uint8))
    mask_ycrcb = cv2.inRange(ycrcb, np.array([0, 130, 75], dtype=np.uint8), np.array([255, 180, 135], dtype=np.uint8))
    mask = cv2.bitwise_or(mask_hsv, mask_ycrcb)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    blur = cv2.GaussianBlur(mask, (5, 5), 0)

    contours, _ = cv2.findContours(blur, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    detected = "NONE"
    max_area = 0
    if contours:
        max_c = max(contours, key=cv2.contourArea)
        max_area = cv2.contourArea(max_c)
        if max_area > 1500:
            hull = cv2.convexHull(max_c, returnPoints=False)
            if len(hull) > 3:
                defects = cv2.convexityDefects(max_c, hull)
                if defects is not None:
                    defects_count = 0
                    for i in range(defects.shape[0]):
                        s, e, f, d = defects[i, 0]
                        start_pt = tuple(max_c[s][0])
                        end_pt = tuple(max_c[e][0])
                        far_pt = tuple(max_c[f][0])
                        a = math.sqrt((end_pt[0] - start_pt[0]) ** 2 + (end_pt[1] - start_pt[1]) ** 2)
                        b = math.sqrt((far_pt[0] - start_pt[0]) ** 2 + (far_pt[1] - start_pt[1]) ** 2)
                        c = math.sqrt((end_pt[0] - far_pt[0]) ** 2 + (end_pt[1] - far_pt[1]) ** 2)
                        angle = math.acos((b ** 2 + c ** 2 - a ** 2) / (2 * b * c + 1e-5)) * 57.2958
                        if angle <= 95 and d > 1200:
                            defects_count += 1
                    
                    if defects_count == 0:
                        detected = "CLOSED_FIST"
                    elif defects_count == 1:
                        detected = "TWO_FINGERS"
                    elif defects_count == 2:
                        detected = "THREE_FINGERS"
                    elif defects_count >= 3:
                        detected = "OPEN_PALM"

    gesture_counts[detected] = gesture_counts.get(detected, 0) + 1
    if frame_count % 30 == 0:
        print(f"Frame {frame_count:3d} | Area: {max_area:5.0f} | Detected Gesture: {detected}")

cap.release()
print(f"\n=== PROCESSED {frame_count} FRAMES ===")
print("Gesture Frequency Breakdown:", gesture_counts)
