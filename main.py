"""
main.py - ElderFall: camera-only fall detection using OpenCV + MediaPipe Pose.
Modified to incorporate a Queue (deque) for rolling-window movement smoothing.
"""
import os

# Hide the endless MediaPipe / TensorFlow Lite log warnings (harmless).
os.environ["GLOG_minloglevel"] = "2"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import math
import time
from collections import deque


import cv2
import mediapipe as mp

import alert_service
import config

mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils
L = mp_pose.PoseLandmark


def _mid(a, b):
    return ((a.x + b.x) / 2, (a.y + b.y) / 2)


def extract_features(landmarks):
    pts = {name: landmarks[name.value] for name in (
        L.LEFT_SHOULDER, L.RIGHT_SHOULDER, L.LEFT_HIP, L.RIGHT_HIP,
        L.LEFT_ANKLE, L.RIGHT_ANKLE)}

    key = [pts[L.LEFT_SHOULDER], pts[L.RIGHT_SHOULDER], pts[L.LEFT_HIP], pts[L.RIGHT_HIP]]
    if sum(p.visibility > config.MIN_VISIBILITY for p in key) < 3:
        return None

    sx, sy = _mid(pts[L.LEFT_SHOULDER], pts[L.RIGHT_SHOULDER])
    hx, hy = _mid(pts[L.LEFT_HIP], pts[L.RIGHT_HIP])

    dx, dy = abs(sx - hx), abs(sy - hy)
    torso_angle = math.degrees(math.atan2(dx, dy + 1e-6))

    visible = [p for p in landmarks if p.visibility > config.MIN_VISIBILITY]
    xs, ys = [p.x for p in visible], [p.y for p in visible]
    width, height = max(xs) - min(xs), max(ys) - min(ys)
    aspect = width / (height + 1e-6)

    return torso_angle, aspect, hy


def draw_status(frame, text, color):
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 36), (0, 0, 0), -1)
    cv2.putText(frame, text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)


def main():
    cap = cv2.VideoCapture(config.CAMERA_SOURCE)
    if not cap.isOpened():
        raise SystemExit("Could not open camera / video source.")

    state = "NORMAL"
    down_since = None
    last_alert_time = 0

    # QUEUE DATA STRUCTURE: A fixed-size FIFO sliding window queue 
    # to store recent (hip_y, timestamp) tuples for smooth velocity tracking.
    window_size = 5
    hip_queue = deque(maxlen=window_size)

    with mp_pose.Pose(min_detection_confidence=0.5,
                      min_tracking_confidence=0.5,
                      model_complexity=1) as pose:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.resize(frame, (config.FRAME_WIDTH, config.FRAME_HEIGHT))
            now = time.time()

            result = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            status, color = "No person detected", (200, 200, 200)

            if result.pose_landmarks:
                mp_draw.draw_landmarks(frame, result.pose_landmarks, mp_pose.POSE_CONNECTIONS)
                feats = extract_features(result.pose_landmarks.landmark)

                if feats:
                    angle, aspect, hip_y = feats

                    # Push the newest frame's hip position into the queue (FIFO)
                    hip_queue.append((hip_y, now))

                    drop_speed = 0.0
                    # If the queue is full, calculate drop speed across the sliding window span
                    if len(hip_queue) == window_size:
                        oldest_y, oldest_time = hip_queue[0]  # Oldest element in queue
                        newest_y, newest_time = hip_queue[-1] # Newest element in queue
                        time_span = newest_time - oldest_time
                        if time_span > 0:
                            drop_speed = (newest_y - oldest_y) / time_span

                    lying = (angle > config.TORSO_ANGLE_LYING
                             or aspect > config.ASPECT_RATIO_LYING)
                    sudden_drop = drop_speed > config.DROP_SPEED_THRESHOLD

                    if state == "NORMAL":
                        status, color = "Monitoring: OK", (0, 255, 0)
                        if lying and (sudden_drop or angle > 75):
                            state, down_since = "CONFIRMING", now

                    elif state == "CONFIRMING":
                        if not lying:
                            state, down_since = "NORMAL", None
                        else:
                            remaining = config.CONFIRM_SECONDS - (now - down_since)
                            status = f"FALL? Press 'o' if OK - alert in {max(0, remaining):.0f}s"
                            color = (0, 165, 255)
                            if remaining <= 0 and now - last_alert_time > config.ALERT_COOLDOWN:
                                alert_service.send_emergency_alert(frame)
                                last_alert_time = now
                                state = "ALERTED"

                    elif state == "ALERTED":
                        status, color = "ALERT SENT - help requested", (0, 0, 255)
                        if not lying:
                            state, down_since = "NORMAL", None
                else:
                    status = "Body not fully visible"
            else:
                # Clear queue when person is lost so stale history isn't used
                hip_queue.clear()

            draw_status(frame, status, color)
            cv2.imshow("ElderFall", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("o") and state == "CONFIRMING":
                alert_service.log_cancelled()
                state, down_since = "NORMAL", None

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()