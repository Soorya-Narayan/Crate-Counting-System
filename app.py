"""
Milma Kottayam Dairy - Live Camera View & Milk Variant Color Detector
====================================================================
Company: Goose Industrial Solutions
Client: Milma (E.R.C.M.P.U. Ltd.), Kottayam Dairy Plant

Focus:
- Full-screen/prominent live camera stream from Baumer VCXG.2-32C (GigE Vision 2.0).
- Real-time multi-spectral color detection for Milma Milk Variants:
    1. ORANGE (Rich Milk 500ml - High Fat)
    2. VIOLET (Toned Milk 500ml - Standard Fat)
    3. GREEN (Smart Milk 500ml - Double Toned)
- Clean, minimal UI with zero clutter.
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

from baumer_camera import BaumerCamera
from milma_counter import generate_synthetic_milma_crate, PouchVariant

app = Flask(__name__)

# ==============================================================================
# GLOBAL STATE
# ==============================================================================
camera_source = "baumer"       # Default to real Baumer camera
baumer_cam = None
baumer_connected = False
baumer_exposure_ms = 30.0

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
    "total_detections": 0
}
state_lock = threading.Lock()

# ==============================================================================
# COLOR DETECTION CONFIGURATIONS (MILMA VARIANTS)
# ==============================================================================
COLOR_SPECS = [
    {
        "id": "orange",
        "name": "ORANGE (Rich Milk)",
        "bgr_color": (0, 140, 255),       # Vivid Orange
        "ranges": [
            (np.array([5, 70, 50]), np.array([22, 255, 255])),
            (np.array([172, 70, 50]), np.array([180, 255, 255]))
        ]
    },
    {
        "id": "violet",
        "name": "VIOLET (Toned Milk)",
        "bgr_color": (210, 60, 180),     # Violet / Purple
        "ranges": [
            (np.array([125, 45, 45]), np.array([165, 255, 255]))
        ]
    },
    {
        "id": "green",
        "name": "GREEN (Smart Milk)",
        "bgr_color": (50, 210, 50),      # Bright Green
        "ranges": [
            (np.array([35, 45, 45]), np.array([88, 255, 255]))
        ]
    }
]


def process_color_detection(frame: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Detects Milma milk variants (Orange, Violet, Green) in the input frame,
    draws bounding boxes and HUD overlays, and computes live color stats.
    """
    h, w = frame.shape[:2]
    annotated = frame.copy()
    total_frame_pixels = float(h * w)

    # Convert to HSV color space
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    counts = {"orange": 0, "violet": 0, "green": 0}
    coverage = {"orange": 0.0, "violet": 0.0, "green": 0.0}
    total_detections = 0
    all_detections = []

    # Minimum contour area for valid pouch or color patch (scale with resolution)
    min_area = max(500, int(total_frame_pixels * 0.001))

    for spec in COLOR_SPECS:
        cid = spec["id"]
        cname = spec["name"]
        color_bgr = spec["bgr_color"]

        # Combined multi-range mask
        combined_mask = np.zeros((h, w), dtype=np.uint8)
        for lower, upper in spec["ranges"]:
            in_range = cv2.inRange(hsv, lower, upper)
            combined_mask = cv2.bitwise_or(combined_mask, in_range)

        # Morphological opening and closing to remove noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        cleaned_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        cleaned_mask = cv2.morphologyEx(cleaned_mask, cv2.MORPH_CLOSE, kernel, iterations=1)

        # Calculate coverage %
        color_pixel_count = np.count_nonzero(cleaned_mask)
        cov_pct = (color_pixel_count / total_frame_pixels) * 100.0
        coverage[cid] = round(cov_pct, 2)

        # Find individual color contours
        contours, _ = cv2.findContours(cleaned_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > min_area:
                x, y, bw, bh = cv2.boundingRect(cnt)
                # Avoid full screen borders or lighting glare
                if bw < w * 0.95 and bh < h * 0.95:
                    counts[cid] += 1
                    total_detections += 1
                    all_detections.append({
                        "id": cid,
                        "name": cname,
                        "bbox": (x, y, bw, bh),
                        "color": color_bgr,
                        "area": area
                    })

    # Draw detected color bounding boxes & badges
    for idx, det in enumerate(all_detections, 1):
        x, y, bw, bh = det["bbox"]
        color = det["color"]
        label = f"{det['name']} #{idx}"

        # Bounding box with glow / corner markers
        cv2.rectangle(annotated, (x, y), (x + bw, y + bh), color, 2)

        # Label badge background
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6 if w < 1200 else 0.8
        thickness = 1 if w < 1200 else 2
        (lw, lh), _ = cv2.getTextSize(label, font, font_scale, thickness)
        
        cv2.rectangle(annotated, (x, max(0, y - lh - 10)), (x + lw + 12, max(lh + 10, y)), color, -1)
        cv2.putText(annotated, label, (x + 6, max(lh, y - 4)), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

    # Determine dominant variant based on counts and coverage
    dominant = "NONE"
    dom_conf = 0.0

    scored_variants = [
        ("ORANGE (Rich Milk)", coverage["orange"], counts["orange"]),
        ("VIOLET (Toned Milk)", coverage["violet"], counts["violet"]),
        ("GREEN (Smart Milk)", coverage["green"], counts["green"]),
    ]
    # Sort by coverage and counts
    scored_variants.sort(key=lambda item: (item[1], item[2]), reverse=True)
    best_name, best_cov, best_count = scored_variants[0]

    if best_cov > 0.4 or best_count > 0:
        dominant = best_name
        sum_cov = sum(coverage.values())
        dom_conf = round((best_cov / sum_cov * 100.0) if sum_cov > 0 else 85.0, 1)

    # Overlaid Top HUD Bar
    hud_h = 56 if h < 1000 else 72
    cv2.rectangle(annotated, (0, 0), (w, hud_h), (18, 18, 22), -1)
    cv2.line(annotated, (0, hud_h), (w, hud_h), (60, 60, 70), 2)

    # Variant pill in HUD
    hud_font = cv2.FONT_HERSHEY_SIMPLEX
    hud_scale = 0.65 if w < 1200 else 0.85
    
    if "ORANGE" in dominant:
        badge_col = (0, 140, 255)
    elif "VIOLET" in dominant:
        badge_col = (210, 60, 180)
    elif "GREEN" in dominant:
        badge_col = (50, 210, 50)
    else:
        badge_col = (120, 120, 120)

    cv2.putText(annotated, f"MILMA VARIANT: {dominant}", (20, int(hud_h * 0.65)),
                hud_font, hud_scale, badge_col, 2, cv2.LINE_AA)

    # Right-aligned color counts in HUD
    counts_text = f"Orange: {counts['orange']}  |  Violet: {counts['violet']}  |  Green: {counts['green']}"
    (tw, th), _ = cv2.getTextSize(counts_text, hud_font, hud_scale * 0.85, 1)
    cv2.putText(annotated, counts_text, (w - tw - 20, int(hud_h * 0.65)),
                hud_font, hud_scale * 0.85, (220, 220, 220), 1, cv2.LINE_AA)

    telemetry = {
        "dominant_variant": dominant,
        "variant_confidence": dom_conf,
        "color_counts": counts,
        "color_coverage": coverage,
        "total_detections": total_detections
    }

    return annotated, telemetry


# ==============================================================================
# BACKGROUND VIDEO ACQUISITION WORKER
# ==============================================================================
def video_capture_worker():
    """Background worker continuously fetching frames, running color detection, and updating stream."""
    global baumer_cam, baumer_connected, camera_source, latest_jpeg_frame, latest_telemetry

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

            # Fetch frame from physical camera
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
            if sim_counter % 30 == 0:
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

            # Run real-time Milma color detection
            annotated_frame, telemetry = process_color_detection(frame)

            # Downsample display copy for ultra-low latency web streaming if high res
            h, w = annotated_frame.shape[:2]
            if w > 1280:
                scale = 1280.0 / w
                stream_frame = cv2.resize(annotated_frame, (1280, int(h * scale)), interpolation=cv2.INTER_LINEAR)
            else:
                stream_frame = annotated_frame

            ret, jpeg = cv2.imencode('.jpg', stream_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                with state_lock:
                    latest_jpeg_frame = jpeg.tobytes()
                    latest_telemetry.update({
                        "camera_source": camera_source,
                        "camera_connected": baumer_connected,
                        "fps": current_fps,
                        "exposure_ms": baumer_exposure_ms,
                        "dominant_variant": telemetry["dominant_variant"],
                        "variant_confidence": telemetry["variant_confidence"],
                        "color_counts": telemetry["color_counts"],
                        "color_coverage": telemetry["color_coverage"],
                        "total_detections": telemetry["total_detections"]
                    })
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
    while True:
        with state_lock:
            frame_bytes = latest_jpeg_frame

        if frame_bytes is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.035)  # ~28 FPS


@app.route('/video_feed')
def video_feed():
    return Response(
        generate_mjpeg_stream(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/api/status')
def get_status():
    """Returns current live camera and color detection telemetry."""
    with state_lock:
        return jsonify(latest_telemetry)


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


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5050))
    print(f"\n🚀 Starting Milma Kottayam Camera & Color Detection Dashboard on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
