"""
Baumer VCXG.2-32C Live Camera Viewer & Lens Focus Tool
======================================================
Company: Goose Industrial Solutions
Client: Milma Kottayam Dairy

Usage:
    python live_baumer_stream.py

Controls:
    [ : Decrease Exposure (-5ms)
    ] : Increase Exposure (+5ms)
    s : Save Snapshot (JPEG)
    q / ESC : Exit
"""

import os
import sys
import time
import datetime
import cv2
import numpy as np
from baumer_camera import BaumerCamera

SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), "snapshots")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)


def calculate_focus_sharpness(img):
    """Calculates image sharpness using Laplacian variance."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()


def run_live_viewer():
    print("=" * 68)
    print("  BAUMER VCXG.2-32C LIVE FOOTAGE & FOCUS TUNER")
    print("  Goose Industrial Solutions - Milma Kottayam Dairy")
    print("=" * 68)
    print("\nStarting camera driver...")

    cam = BaumerCamera(camera_ip="169.254.123.85", host_ip="169.254.128.78")
    try:
        cam.connect()
        cam.set_exposure_time(30000)  # Start at 30 ms
        cam.start_stream()
    except Exception as e:
        print(f"\n❌ Error starting camera: {e}")
        print("Please check Ethernet cable and power supply.")
        return

    window_name = "Milma Kottayam - Baumer VCXG.2-32C Live Stream"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1024, 768)

    print("\n[Controls in Video Window]:")
    print("  '[' : Decrease Exposure (-5ms)")
    print("  ']' : Increase Exposure (+5ms)")
    print("  's' : Save Snapshot")
    print("  'q' or ESC : Exit")
    print("\nStreaming live footage...")

    frame_count = 0
    fps = 0.0
    fps_timer = time.time()
    last_msg = ""
    last_msg_time = 0

    try:
        while True:
            t0 = time.time()
            frame, info = cam.get_frame(timeout=1.0)

            if frame is None:
                # If frame drop, wait a bit
                time.sleep(0.01)
                continue

            frame_count += 1
            if time.time() - fps_timer >= 1.0:
                fps = frame_count / (time.time() - fps_timer)
                frame_count = 0
                fps_timer = time.time()

            # Calculate sharpness score (for optical focus adjustment)
            sharpness = calculate_focus_sharpness(frame)

            # Display copy
            display = frame.copy()
            h, w = display.shape[:2]

            # Draw HUD bar at top
            cv2.rectangle(display, (0, 0), (w, 64), (18, 18, 24), -1)
            cv2.line(display, (0, 64), (w, 64), (0, 180, 255), 2)

            # Status indicators
            exp_ms = cam.current_exposure_us / 1000.0
            status_text = (
                f"BAUMER VCXG.2-32C (Sony Pregius) | Res: {w}x{h} | "
                f"FPS: {fps:.1f} | Exp: {exp_ms:.1f}ms | Focus Sharpness: {sharpness:.1f}"
            )
            cv2.putText(display, status_text, (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)

            # Crosshair in center for alignment
            cx, cy = w // 2, h // 2
            cv2.line(display, (cx - 30, cy), (cx + 30, cy), (0, 255, 128), 2)
            cv2.line(display, (cx, cy - 30), (cx, cy + 30), (0, 255, 128), 2)
            cv2.circle(display, (cx, cy), 15, (0, 255, 128), 1)

            # Temporary message banner (e.g. Snapshot Saved)
            if time.time() - last_msg_time < 2.5:
                cv2.rectangle(display, (20, h - 70), (450, h - 20), (0, 120, 0), -1)
                cv2.putText(display, last_msg, (30, h - 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            cv2.imshow(window_name, display)

            key = cv2.waitKey(1) & 0xFF
            if key in [ord('q'), 27]:  # 'q' or ESC
                print("\nExiting live viewer...")
                break
            elif key == ord(']'):  # Increase exposure
                cam.set_exposure_time(cam.current_exposure_us + 5000)
                last_msg = f"Exposure: {cam.current_exposure_us/1000.0:.1f} ms"
                last_msg_time = time.time()
            elif key == ord('['):  # Decrease exposure
                cam.set_exposure_time(cam.current_exposure_us - 5000)
                last_msg = f"Exposure: {cam.current_exposure_us/1000.0:.1f} ms"
                last_msg_time = time.time()
            elif key == ord('s'):  # Save snapshot
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(SNAPSHOT_DIR, f"baumer_snap_{ts}.jpg")
                cv2.imwrite(filename, frame)
                last_msg = f"Saved: {os.path.basename(filename)}"
                last_msg_time = time.time()
                print(f"Snapshot saved: {filename}")

    finally:
        cam.stop_stream()
        cam.disconnect()
        cv2.destroyAllWindows()
        print("Done. Camera released.")


if __name__ == "__main__":
    run_live_viewer()
