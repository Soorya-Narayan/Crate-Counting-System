#!/usr/bin/env python3
"""
Milma Kottayam - Live Mac Camera AI Testing Utility
====================================================
Runs real-time Milma pouch detection and crate counting directly on the
built-in Mac FaceTime HD camera using the custom-trained YOLOv8 weights (milma_best.pt).

Usage:
    python3 live_mac_camera.py
    python3 live_mac_camera.py --conf 0.25 --camera 0

Keys:
    'q' / ESC : Quit
    's'       : Save current annotated snapshot
    '+' / '=' : Increase confidence cutoff (+0.05)
    '-'       : Decrease confidence cutoff (-0.05)
    'r'       : Reset pouch tally
"""

import os
import sys
import time
import argparse
from datetime import datetime
import cv2
import numpy as np
from ultralytics import YOLO

# Class mapping with Milma corporate visual scheme
CLASS_CONFIG = {
    "crate": {"bgr": (240, 110, 20), "name": "Crate (Outer Frame)"},
    "empty_tray": {"bgr": (0, 215, 245), "name": "Empty Tray"},
    "pouch_green": {"bgr": (40, 205, 50), "name": "Green Milk Pouch"},
    "pouch_orange": {"bgr": (0, 135, 245), "name": "Orange Milk Pouch"},
    "pouch_purple": {"bgr": (210, 60, 175), "name": "Purple Milk Pouch"}
}

def parse_args():
    parser = argparse.ArgumentParser(description="Milma Live Mac Camera Inference")
    parser.add_argument("--model", type=str, default="milma_best.pt", help="Path to trained weights")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (0 is usually Mac built-in)")
    parser.add_argument("--conf", type=float, default=0.38, help="Confidence threshold (0.05 - 0.95)")
    parser.add_argument("--iou", type=float, default=0.45, help="NMS IoU threshold for overlapping pouches")
    parser.add_argument("--device", type=str, default="mps", help="Device: 'mps', 'cpu', or '0'")
    return parser.parse_args()


def main():
    args = parse_args()

    model_path = os.path.abspath(args.model)
    if not os.path.exists(model_path):
        print(f"❌ Error: Model weights not found at: {model_path}")
        print("Please verify milma_best.pt exists.")
        sys.exit(1)

    print(f"================================================================")
    print(f"  MILMA LIVE MACHINE VISION - MAC FACETIME HD CAMERA TEST")
    print(f"================================================================")
    print(f"• Model Weights: {model_path}")
    print(f"• Camera Index : {args.camera}")
    print(f"• Initial Conf : {args.conf:.2f}")
    print(f"• NMS IoU      : {args.iou:.2f}")
    print(f"• Device       : {args.device}")
    print("Loading YOLOv8 neural network...")

    try:
        model = YOLO(model_path)
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        sys.exit(1)

    print("Opening Mac camera stream...")
    cap = cv2.VideoCapture(args.camera)

    # Set 720p / 1080p
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    if not cap.isOpened():
        print(f"❌ Could not access Mac camera index {args.camera}.")
        print("Ensure Camera permissions are granted in macOS System Settings > Privacy & Security > Camera.")
        sys.exit(1)

    print("✓ Mac Camera connected successfully!")
    print("Press 'q' to quit, 's' to snapshot, '+/-' to tune confidence.")

    conf_thresh = args.conf
    iou_thresh = args.iou
    fps_history = []
    prev_time = time.time()
    snapshot_dir = "snapshots"
    os.makedirs(snapshot_dir, exist_ok=True)

    cv2.namedWindow("Milma AI - Mac Camera Live Detection", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Milma AI - Mac Camera Live Detection", 1280, 720)

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("Warning: Empty camera frame received.")
                time.sleep(0.05)
                continue

            # Calculate FPS
            curr_time = time.time()
            fps = 1.0 / max(curr_time - prev_time, 1e-5)
            prev_time = curr_time
            fps_history.append(fps)
            if len(fps_history) > 20:
                fps_history.pop(0)
            avg_fps = sum(fps_history) / len(fps_history)

            # Inference with calibrated NMS IoU
            results = model.predict(
                frame,
                conf=conf_thresh,
                iou=iou_thresh,
                imgsz=640,
                device=args.device,
                verbose=False
            )[0]

            annotated = frame.copy()
            h, w = annotated.shape[:2]

            counts = {k: 0 for k in CLASS_CONFIG.keys()}
            total_pouches = 0

            raw_boxes = []
            if results.boxes is not None:
                for b in results.boxes:
                    x1, y1, x2, y2 = [int(v) for v in b.xyxy[0]]
                    cls_id = int(b.cls[0])
                    conf = float(b.conf[0])
                    class_name = model.names[cls_id]
                    area = (x2 - x1) * (y2 - y1)
                    raw_boxes.append({
                        "bbox": (x1, y1, x2, y2),
                        "conf": conf,
                        "class_name": class_name,
                        "area": area
                    })

            # Sort descending by confidence
            raw_boxes.sort(key=lambda x: x["conf"], reverse=True)

            # IoS Containment Deduplication (prunes internal fold / logo sub-boxes)
            filtered_boxes = []
            for candidate in raw_boxes:
                cx1, cy1, cx2, cy2 = candidate["bbox"]
                c_area = candidate["area"]
                is_pouch = "pouch" in candidate["class_name"]

                is_dup = False
                if is_pouch:
                    for kept in filtered_boxes:
                        if "pouch" not in kept["class_name"]:
                            continue
                        kx1, ky1, kx2, ky2 = kept["bbox"]
                        k_area = kept["area"]
                        ix1, iy1 = max(cx1, kx1), max(cy1, ky1)
                        ix2, iy2 = min(cx2, kx2), min(cy2, ky2)
                        if ix2 > ix1 and iy2 > iy1:
                            inter = (ix2 - ix1) * (iy2 - iy1)
                            ios = inter / min(c_area, k_area)
                            if ios > 0.50:
                                is_dup = True
                                break
                if not is_dup:
                    filtered_boxes.append(candidate)

            # Draw boxes
            for item in filtered_boxes:
                x1, y1, x2, y2 = item["bbox"]
                class_name = item["class_name"]
                conf = item["conf"]

                cfg = CLASS_CONFIG.get(class_name, {"bgr": (200, 200, 200), "name": class_name})
                bgr = cfg["bgr"]

                if class_name in counts:
                    counts[class_name] += 1
                if "pouch" in class_name:
                    total_pouches += 1

                # Bounding Box
                cv2.rectangle(annotated, (x1, y1), (x2, y2), bgr, 2)

                    # Badge
                    label = f"{class_name.upper()} {int(conf * 100)}%"
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    (lw, lh), _ = cv2.getTextSize(label, font, 0.55, 1)
                    badge_y1 = max(0, y1 - lh - 8)
                    cv2.rectangle(annotated, (x1, badge_y1), (x1 + lw + 8, y1), bgr, -1)
                    cv2.putText(annotated, label, (x1 + 4, y1 - 4), font, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

            # --- HUD OVERLAYS ---
            # Top Banner
            hud_h = 56
            overlay = annotated.copy()
            cv2.rectangle(overlay, (0, 0), (w, hud_h), (18, 20, 24), -1)
            cv2.addWeighted(overlay, 0.85, annotated, 0.15, 0, annotated)
            cv2.line(annotated, (0, hud_h), (w, hud_h), (60, 68, 80), 1)

            # Titles & FPS
            cv2.putText(annotated, "MILMA AI VISION • LIVE MAC CAMERA", (16, 36),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 215, 255), 2, cv2.LINE_AA)

            hud_right = f"FPS: {avg_fps:.1f} | Conf: {int(conf_thresh * 100)}% | Model: milma_best.pt"
            (rw, _), _ = cv2.getTextSize(hud_right, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            cv2.putText(annotated, hud_right, (w - rw - 16, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 210, 225), 1, cv2.LINE_AA)

            # Bottom Tally Strip
            tally_h = 44
            tally_y = h - tally_h
            t_overlay = annotated.copy()
            cv2.rectangle(t_overlay, (0, tally_y), (w, h), (18, 20, 24), -1)
            cv2.addWeighted(t_overlay, 0.85, annotated, 0.15, 0, annotated)
            cv2.line(annotated, (0, tally_y), (w, tally_y), (60, 68, 80), 1)

            tally_txt = (
                f"TOTAL POUCHES: {total_pouches}  |  "
                f"Orange: {counts['pouch_orange']}  |  "
                f"Green: {counts['pouch_green']}  |  "
                f"Purple: {counts['pouch_purple']}  |  "
                f"Crates: {counts['crate']}  |  "
                f"Empty Trays: {counts['empty_tray']}"
            )
            cv2.putText(annotated, tally_txt, (16, h - 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 255, 255), 2, cv2.LINE_AA)

            cv2.imshow("Milma AI - Mac Camera Live Detection", annotated)

            key = cv2.waitKey(1) & 0xFF
            if key == 27 or key == ord('q'):
                print("Exiting live stream...")
                break
            elif key == ord('s'):
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                snap_path = os.path.join(snapshot_dir, f"mac_camera_snap_{ts}.jpg")
                cv2.imwrite(snap_path, annotated)
                print(f"📸 Snapshot saved: {snap_path}")
            elif key == ord('+') or key == ord('='):
                conf_thresh = min(0.95, conf_thresh + 0.05)
                print(f"Confidence threshold increased: {conf_thresh:.2f}")
            elif key == ord('-') or key == ord('_'):
                conf_thresh = max(0.05, conf_thresh - 0.05)
                print(f"Confidence threshold decreased: {conf_thresh:.2f}")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("✓ Mac camera released.")

if __name__ == "__main__":
    main()
