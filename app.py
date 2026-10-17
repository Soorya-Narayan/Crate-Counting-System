"""
Milma Kottayam Dairy - Live Camera, YOLO Object Detection & Color Classifier
===========================================================================
Company: Goose Industrial Solutions
Client: Milma (E.R.C.M.P.U. Ltd.), Kottayam Dairy Plant

Features:
- Real-time Baumer VCXG.2-32C GigE camera streaming with hardware AWB.
- YOLOv8 Object Detection (detects scissors, bottles, cups, pouches, caps, phones, etc.).
- Multi-Spectral Color Classifier on each detected object:
    - ORANGE -> Milma Rich Milk (500ml)
    - VIOLET -> Milma Toned Milk (500ml)
    - GREEN  -> Milma Smart Milk (500ml)
    - BLUE, YELLOW, RED, BLACK, WHITE
- Real-time color-coded bounding boxes and HUD labels.
"""

import os
import time
import socket
import struct
import threading
from typing import Dict, Any, List, Tuple

from flask import Flask, render_template, Response, jsonify, request
import cv2
import numpy as np
from ultralytics import YOLO

from baumer_camera import BaumerCamera
from milma_counter import generate_synthetic_milma_crate, PouchVariant

app = Flask(__name__)

# Load YOLO model
print("Loading YOLOv8 object detection model...")
yolo_model = YOLO("yolov8n.pt")
print("✓ YOLOv8 model ready.")

# Global Application State
camera_source = "baumer"       # Real Baumer camera by default
baumer_cam = None
baumer_connected = False
baumer_exposure_ms = 30.0
confidence_cutoff = 0.18

latest_jpeg_frame = None
latest_telemetry: Dict[str, Any] = {
    "camera_source": "baumer",
    "camera_connected": False,
    "fps": 0.0,
    "exposure_ms": 30.0,
    "dominant_variant": "NONE",
    "variant_confidence": 0.0,
    "color_counts": {"orange": 0, "violet": 0, "green": 0},
    "color_coverage": {"orange": 0.0, "violet": 0.0, "green": 0.0},
    "detected_objects": [],
    "total_detections": 0
}
frame_cond = threading.Condition()
latest_frame_id = 0

# Milma Variant Color Ranges (HSV)
MILMA_COLORS = {
    "orange": {
        "name": "ORANGE (Rich Milk)",
        "bgr": (0, 140, 255),
        "lower": np.array([6, 120, 70]),
        "upper": np.array([21, 255, 255])
    },
    "violet": {
        "name": "VIOLET (Toned Milk)",
        "bgr": (210, 60, 180),
        "lower": np.array([125, 75, 55]),
        "upper": np.array([160, 255, 255])
    },
    "green": {
        "name": "GREEN (Smart Milk)",
        "bgr": (50, 210, 50),
        "lower": np.array([38, 75, 55]),
        "upper": np.array([85, 255, 255])
    }
}


def classify_crop_color(roi_bgr: np.ndarray) -> Tuple[str, Tuple[int, int, int], str]:
    """
    Classifies the dominant color of an object crop.
    Returns: (Color Name, BGR tuple for drawing, Milma Variant Tag or 'standard')
    """
    if roi_bgr.size == 0 or roi_bgr.shape[0] < 4 or roi_bgr.shape[1] < 4:
        return "UNKNOWN", (128, 128, 128), "none"

    # Analyze inner 75% of ROI to minimize background interference
    rh, rw = roi_bgr.shape[:2]
    cy, cx = rh // 2, rw // 2
    dh, dw = int(rh * 0.38), int(rw * 0.38)
    inner = roi_bgr[max(0, cy - dh):min(rh, cy + dh), max(0, cx - dw):min(rw, cx + dw)]
    if inner.size == 0:
        inner = roi_bgr

    hsv = cv2.cvtColor(inner, cv2.COLOR_BGR2HSV)
    val = hsv[:, :, 2]
    sat = hsv[:, :, 1]
    
    # 1. Check for neutral colors (Black / White / Gray)
    med_val = np.median(val)
    med_sat = np.median(sat)
    
    if med_val < 42:
        return "BLACK", (40, 40, 40), "black"
    if med_sat < 25 and med_val > 175:
        return "WHITE / SILVER", (230, 230, 230), "white"
    if med_sat < 35:
        return "GRAY / NEUTRAL", (140, 140, 140), "gray"

    # 2. Check for Milma-specific saturated colors first
    for var_key, spec in MILMA_COLORS.items():
        mask = cv2.inRange(hsv, spec["lower"], spec["upper"])
        if np.count_nonzero(mask) > (inner.shape[0] * inner.shape[1] * 0.12):
            return spec["name"], spec["bgr"], var_key

    # 3. Saturated pixels general hue spectrum
    sat_mask = (sat > 40) & (val > 40)
    if np.count_nonzero(sat_mask) < 20:
        return "NEUTRAL", (130, 130, 130), "neutral"

    hues = hsv[:, :, 0][sat_mask]
    med_hue = int(np.median(hues))

    if 5 <= med_hue <= 22 or med_hue >= 172:
        return "ORANGE (Rich Milk)", (0, 140, 255), "orange"
    elif 23 <= med_hue <= 35:
        return "YELLOW", (0, 220, 255), "yellow"
    elif 36 <= med_hue <= 85:
        return "GREEN (Smart Milk)", (50, 210, 50), "green"
    elif 86 <= med_hue <= 124:
        return "BLUE", (240, 110, 10), "blue"
    elif 125 <= med_hue <= 165:
        return "VIOLET (Toned Milk)", (210, 60, 180), "violet"
    else:
        return "RED", (0, 0, 240), "red"


def process_yolo_and_colors(frame: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Runs YOLO object detection and color classification on every detected object."""
    h, w = frame.shape[:2]
    annotated = frame.copy()
    total_pixels = float(h * w)

    # 1. Run YOLO object detection
    yolo_res = yolo_model.predict(
        frame,
        imgsz=640,
        conf=confidence_cutoff,
        verbose=False
    )[0]

    detected_items = []
    milma_counts = {"orange": 0, "violet": 0, "green": 0}
    milma_coverage = {"orange": 0.0, "violet": 0.0, "green": 0.0}

    # Track YOLO bounding boxes
    yolo_boxes = []
    if yolo_res.boxes is not None:
        for b in yolo_res.boxes:
            coords = [int(v) for v in b.xyxy[0]]
            cls_id = int(b.cls[0])
            cls_name = yolo_model.names[cls_id]
            conf = float(b.conf[0])
            yolo_boxes.append((coords, cls_name, conf))

    # 2. Also run contour color search for Milma pouches (Green, Orange, Violet)
    hsv_full = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    min_patch_area = max(3500, int(total_pixels * 0.005))

    color_regions = []
    for var_key, spec in MILMA_COLORS.items():
        mask = cv2.inRange(hsv_full, spec["lower"], spec["upper"])
        cov = (np.count_nonzero(mask) / total_pixels) * 100.0
        milma_coverage[var_key] = round(cov, 2)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        cleaned = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        cnts, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for c in cnts:
            area = cv2.contourArea(c)
            if area > min_patch_area:
                x, y, bw, bh = cv2.boundingRect(c)
                if bw < w * 0.92 and bh < h * 0.92:
                    color_regions.append({
                        "bbox": (x, y, x + bw, y + bh),
                        "color_name": spec["name"],
                        "bgr": spec["bgr"],
                        "var_key": var_key,
                        "area": area
                    })

    # 3. Fuse YOLO detections with color classification
    handled_yolo_indices = set()

    # Match color regions with overlapping YOLO objects
    for cr in color_regions:
        cx1, cy1, cx2, cy2 = cr["bbox"]
        matched_obj = "milk pouch"
        matched_conf = 0.95

        for y_idx, (y_box, y_name, y_conf) in enumerate(yolo_boxes):
            if y_idx in handled_yolo_indices:
                continue
            yx1, yy1, yx2, yy2 = y_box
            # Compute intersection
            ix1, iy1 = max(cx1, yx1), max(cy1, yy1)
            ix2, iy2 = min(cx2, yx2), min(cy2, yy2)
            if ix1 < ix2 and iy1 < iy2:
                # Intersecting
                matched_obj = y_name
                matched_conf = y_conf
                handled_yolo_indices.add(y_idx)
                break

        var_key = cr["var_key"]
        milma_counts[var_key] += 1

        detected_items.append({
            "object": matched_obj,
            "color": cr["color_name"],
            "bgr": cr["bgr"],
            "bbox": (cx1, cy1, cx2, cy2),
            "conf": matched_conf,
            "is_milma": True
        })

    # Add remaining YOLO objects that didn't match a Milma pouch color (e.g. black cap, blue phone)
    for y_idx, (y_box, y_name, y_conf) in enumerate(yolo_boxes):
        if y_idx in handled_yolo_indices:
            continue
        yx1, yy1, yx2, yy2 = y_box
        crop = frame[max(0, yy1):min(h, yy2), max(0, yx1):min(w, yx2)]
        color_name, bgr_col, var_tag = classify_crop_color(crop)

        if var_tag in milma_counts:
            milma_counts[var_tag] += 1

        detected_items.append({
            "object": y_name,
            "color": color_name,
            "bgr": bgr_col,
            "bbox": (yx1, yy1, yx2, yy2),
            "conf": y_conf,
            "is_milma": (var_tag in ["orange", "violet", "green"])
        })

    # 4. Draw annotated bounding boxes and labels
    for idx, item in enumerate(detected_items, 1):
        x1, y1, x2, y2 = item["bbox"]
        color = item["bgr"]
        obj = item["object"]
        cname = item["color"]
        label = f"{obj.upper()}: {cname} ({int(item['conf']*100)}%)"

        # Bounding box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

        # Label badge
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6 if w < 1200 else 0.75
        thickness = 1 if w < 1200 else 2
        (lw, lh), _ = cv2.getTextSize(label, font, font_scale, thickness)

        cv2.rectangle(annotated, (x1, max(0, y1 - lh - 10)), (x1 + lw + 12, max(lh + 10, y1)), color, -1)
        # Choose text color (white for dark backgrounds, dark for white/yellow)
        text_color = (0, 0, 0) if cname in ["WHITE / SILVER", "YELLOW"] else (255, 255, 255)
        cv2.putText(annotated, label, (x1 + 6, max(lh, y1 - 4)), font, font_scale, text_color, thickness, cv2.LINE_AA)

    # 5. Overlaid HUD Bar
    hud_h = 56 if h < 1000 else 70
    cv2.rectangle(annotated, (0, 0), (w, hud_h), (18, 18, 22), -1)
    cv2.line(annotated, (0, hud_h), (w, hud_h), (60, 60, 70), 2)

    # Determine dominant Milma variant
    dominant = "NONE"
    dom_conf = 0.0
    ranked = sorted(milma_counts.items(), key=lambda x: x[1], reverse=True)
    if ranked[0][1] > 0:
        top_k = ranked[0][0]
        dominant = MILMA_COLORS[top_k]["name"]
        dom_conf = 95.0
    elif max(milma_coverage.values()) > 0.4:
        top_cov = max(milma_coverage.items(), key=lambda x: x[1])
        dominant = MILMA_COLORS[top_cov[0]]["name"]
        dom_conf = 85.0

    hud_font = cv2.FONT_HERSHEY_SIMPLEX
    hud_scale = 0.65 if w < 1200 else 0.85
    hud_color = (50, 210, 50) if "GREEN" in dominant else ((0, 140, 255) if "ORANGE" in dominant else ((210, 60, 180) if "VIOLET" in dominant else (140, 140, 140)))
    
    cv2.putText(annotated, f"MILMA VARIANT: {dominant}", (20, int(hud_h * 0.65)),
                hud_font, hud_scale, hud_color, 2, cv2.LINE_AA)

    # Summary of detections in top right
    summary = f"Detected: {len(detected_items)} objects | Green: {milma_counts['green']} | Orange: {milma_counts['orange']} | Violet: {milma_counts['violet']}"
    (sw, sh), _ = cv2.getTextSize(summary, hud_font, hud_scale * 0.8, 1)
    cv2.putText(annotated, summary, (w - sw - 20, int(hud_h * 0.65)),
                hud_font, hud_scale * 0.8, (220, 220, 220), 1, cv2.LINE_AA)

    telemetry = {
        "dominant_variant": dominant,
        "variant_confidence": dom_conf,
        "color_counts": milma_counts,
        "color_coverage": milma_coverage,
        "detected_objects": [
            {
                "object": it["object"],
                "color": it["color"],
                "confidence": round(it["conf"] * 100.0, 1),
                "is_milma": it["is_milma"]
            }
            for it in detected_items
        ],
        "total_detections": len(detected_items)
    }

    return annotated, telemetry


# ==============================================================================
# BACKGROUND VIDEO CAPTURE WORKER
# ==============================================================================
def video_capture_worker():
    """Continuously fetches frames, runs YOLO + Color classification, and feeds stream."""
    global baumer_cam, baumer_connected, camera_source, latest_jpeg_frame, latest_telemetry, latest_frame_id

    fps_count = 0
    fps_timer = time.time()
    current_fps = 0.0

    sim_variants = [PouchVariant.ORANGE, PouchVariant.VIOLET, PouchVariant.GREEN]
    sim_idx = 0
    sim_counter = 0

    while True:
        frame = None

        if camera_source == "baumer":
            if baumer_cam is None:
                try:
                    print("Connecting to Baumer VCXG.2-32C at 169.254.123.85...")
                    cam = BaumerCamera(camera_ip="169.254.123.85", host_ip="169.254.128.78")
                    cam.connect()
                    cam.set_exposure_time(int(baumer_exposure_ms * 1000))
                    cam.start_stream()
                    baumer_cam = cam
                    baumer_connected = True
                    print("✓ Baumer camera online and streaming.")
                except Exception as e:
                    print(f"Baumer connection note: {e}")
                    baumer_connected = False
                    time.sleep(2.0)
                    continue

            # Fetch frame from Baumer camera
            raw_frame, info = baumer_cam.get_frame(timeout=0.6)
            if raw_frame is not None:
                frame = raw_frame
            else:
                time.sleep(0.01)
        else:
            # Simulated fallback
            if baumer_cam is not None:
                try:
                    baumer_cam.stop_stream()
                    baumer_cam.disconnect()
                except Exception:
                    pass
                baumer_cam = None
                baumer_connected = False

            sim_counter += 1
            if sim_counter % 35 == 0:
                sim_idx = (sim_idx + 1) % len(sim_variants)
            frame = generate_synthetic_milma_crate(variant=sim_variants[sim_idx], num_pouches=20)
            time.sleep(0.06)

        if frame is not None:
            # FPS Calculation
            fps_count += 1
            now = time.time()
            if now - fps_timer >= 1.0:
                current_fps = round(fps_count / (now - fps_timer), 1)
                fps_count = 0
                fps_timer = now

            # Run YOLO + Color Detection
            annotated_frame, telemetry = process_yolo_and_colors(frame)

            # Downsample for web stream responsiveness if high res
            h, w = annotated_frame.shape[:2]
            if w > 1280:
                scale = 1280.0 / w
                stream_frame = cv2.resize(annotated_frame, (1280, int(h * scale)), interpolation=cv2.INTER_LINEAR)
            else:
                stream_frame = annotated_frame

            ret, jpeg = cv2.imencode('.jpg', stream_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                with frame_cond:
                    latest_jpeg_frame = jpeg.tobytes()
                    latest_frame_id += 1
                    latest_telemetry.update({
                        "camera_source": camera_source,
                        "camera_connected": baumer_connected,
                        "fps": current_fps,
                        "exposure_ms": baumer_exposure_ms,
                        "dominant_variant": telemetry["dominant_variant"],
                        "variant_confidence": telemetry["variant_confidence"],
                        "color_counts": telemetry["color_counts"],
                        "color_coverage": telemetry["color_coverage"],
                        "detected_objects": telemetry["detected_objects"],
                        "total_detections": telemetry["total_detections"]
                    })
                    frame_cond.notify_all()
        else:
            time.sleep(0.02)


# Start background video thread
video_thread = threading.Thread(target=video_capture_worker, daemon=True)
video_thread.start()


# ==============================================================================
# FLASK WEB ROUTES
# ==============================================================================
@app.route('/')
def index():
    return render_template('index.html')


def generate_mjpeg_stream():
    """Yields continuous JPEG frames for the <img> tag in the dashboard."""
    local_frame_id = -1
    while True:
        try:
            with frame_cond:
                if latest_frame_id == local_frame_id:
                    frame_cond.wait(timeout=0.5)
                frame_bytes = latest_jpeg_frame
                local_frame_id = latest_frame_id

            if frame_bytes is not None:
                header = (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n'
                    b'Content-Length: ' + str(len(frame_bytes)).encode('ascii') + b'\r\n\r\n'
                )
                yield header + frame_bytes + b'\r\n'
        except GeneratorExit:
            break
        except Exception:
            break


@app.route('/video_feed')
def video_feed():
    res = Response(
        generate_mjpeg_stream(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )
    res.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    res.headers['Pragma'] = 'no-cache'
    res.headers['Expires'] = '0'
    return res


@app.route('/api/frame')
def single_frame():
    """Returns single latest JPEG frame. Universal fallback for any browser."""
    with frame_cond:
        frame_bytes = latest_jpeg_frame
    if frame_bytes is None:
        return ("No frame captured yet", 503)
    res = Response(frame_bytes, mimetype='image/jpeg')
    res.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    res.headers['Pragma'] = 'no-cache'
    res.headers['Expires'] = '0'
    return res


@app.route('/api/status')
def get_status():
    """Returns current live camera, YOLO object detections, and color telemetry."""
    with frame_cond:
        return jsonify(dict(latest_telemetry))


@app.route('/api/set_source', methods=['POST'])
def set_source():
    """Toggle between physical Baumer camera and simulated feed."""
    global camera_source
    data = request.json or {}
    source = data.get("source", "baumer").lower()
    if source in ["baumer", "live", "camera"]:
        camera_source = "baumer"
    else:
        camera_source = "simulated"
    return jsonify({"camera_source": camera_source})


@app.route('/api/set_exposure', methods=['POST'])
def set_exposure():
    """Sets camera exposure time in milliseconds."""
    global baumer_exposure_ms, baumer_cam
    data = request.json or {}
    exp_ms = float(data.get("exposure_ms", 30.0))
    exp_ms = max(1.0, min(100.0, exp_ms))
    baumer_exposure_ms = exp_ms
    if baumer_cam:
        baumer_cam.set_exposure_time(int(exp_ms * 1000))
    return jsonify({"exposure_ms": baumer_exposure_ms})


@app.route('/api/set_confidence', methods=['POST'])
def set_confidence():
    """Sets YOLO detection confidence cutoff."""
    global confidence_cutoff
    data = request.json or {}
    conf = float(data.get("confidence", 0.20))
    confidence_cutoff = max(0.05, min(0.95, conf))
    return jsonify({"confidence_cutoff": confidence_cutoff})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5050))
    print(f"\n🚀 Starting Milma YOLO Object & Color Detection Dashboard on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
