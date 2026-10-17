#!/usr/bin/env python3
"""
Goose Industrial Solutions - Vision AI Object & Color Classifier
Milma Kottayam Dairy Project
Baumer GigE Machine Vision Camera + Ultralytics YOLOv8 + Lens ISP Pipeline
"""

import os
import sys
import time
import json
import logging
import threading
from typing import Dict, Any, List, Tuple, Optional

import cv2
import numpy as np
from flask import Flask, render_template, Response, jsonify, request
from ultralytics import YOLO

from baumer_camera import BaumerCamera

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MilmaVision")

app = Flask(__name__)

# ==============================================================================
# GLOBAL CONFIGURATION & TUNING PARAMETERS
# ==============================================================================
# YOLO Model
print("Loading YOLOv8 object detection model...")
yolo_model = YOLO("yolov8n.pt")
print("✓ YOLOv8 model ready.")

# Detection cutoff
confidence_cutoff = 0.20

# Hardware Camera & Lens ISP Settings
baumer_cam: Optional[BaumerCamera] = None
baumer_connected = False
camera_source = "baumer"  # 'baumer' or 'simulated'
baumer_exposure_ms = 30.0

# Live Lens ISP Adjustments
lens_settings = {
    "brightness": 5,        # -50 to +50
    "contrast": 1.18,       # 0.5 to 2.0
    "saturation": 1.35,     # 0.5 to 2.5
    "gamma": 0.85,          # 0.5 to 1.5
    "auto_wb": True         # Auto white balance (Gray World)
}

# Stream Frame & Telemetry State
latest_jpeg_frame: Optional[bytes] = None
latest_telemetry: Dict[str, Any] = {
    "camera_source": "baumer",
    "camera_connected": False,
    "fps": 0.0,
    "exposure_ms": 30.0,
    "lens_settings": lens_settings,
    "detected_objects": [],
    "color_distribution": {},
    "total_detections": 0
}

frame_cond = threading.Condition()
latest_frame_id = 0

# ==============================================================================
# LENS ISP COLOR ENHANCEMENT ENGINE
# ==============================================================================
def enhance_lens_frame(frame: np.ndarray) -> np.ndarray:
    """
    Transforms linear raw sensor output into a vibrant, color-accurate image.
    Applies Auto White Balance, Gamma correction, Brightness/Contrast, and Saturation boost.
    """
    if frame is None or frame.size == 0:
        return frame

    # 1. White Balance (Gray World Color Constancy)
    scale_b, scale_g, scale_r = 1.0, 1.0, 1.0
    if lens_settings.get("auto_wb", True):
        b, g, r = cv2.split(frame)
        m_b, m_g, m_r = float(np.mean(b)), float(np.mean(g)), float(np.mean(r))
        m_gray = (m_b + m_g + m_r) / 3.0
        scale_b = float(np.clip(m_gray / (m_b + 1e-5), 0.75, 1.40))
        scale_g = float(np.clip(m_gray / (m_g + 1e-5), 0.75, 1.40))
        scale_r = float(np.clip(m_gray / (m_r + 1e-5), 0.75, 1.40))

    # 2. Build 3-channel LUT for Gamma + Contrast + Brightness + Channel Scales
    gamma = max(0.4, min(2.0, float(lens_settings.get("gamma", 0.85))))
    inv_gamma = 1.0 / gamma
    contrast = max(0.5, min(2.0, float(lens_settings.get("contrast", 1.18))))
    brightness = float(lens_settings.get("brightness", 5))

    lut = np.zeros((256, 1, 3), dtype=np.uint8)
    for i in range(256):
        v = ((i / 255.0) ** inv_gamma) * 255.0
        v = (v - 128.0) * contrast + 128.0 + brightness
        lut[i, 0, 0] = np.clip(v * scale_b, 0, 255)  # Blue
        lut[i, 0, 1] = np.clip(v * scale_g, 0, 255)  # Green
        lut[i, 0, 2] = np.clip(v * scale_r, 0, 255)  # Red

    enhanced = np.empty_like(frame)
    enhanced[:, :, 0] = cv2.LUT(frame[:, :, 0], lut[:, 0, 0])
    enhanced[:, :, 1] = cv2.LUT(frame[:, :, 1], lut[:, 0, 1])
    enhanced[:, :, 2] = cv2.LUT(frame[:, :, 2], lut[:, 0, 2])

    # 3. Saturation / Vibrancy in HSV space
    sat_scale = max(0.5, min(2.5, float(lens_settings.get("saturation", 1.35))))
    if abs(sat_scale - 1.0) > 0.05:
        hsv = cv2.cvtColor(enhanced, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * sat_scale, 0, 255)
        enhanced = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    return enhanced


# ==============================================================================
# MULTI-SPECTRAL COLOR CLASSIFIER
# ==============================================================================
COLOR_PALETTE = {
    "RED": {"bgr": (30, 30, 235), "hex": "#ef4444"},
    "ORANGE": {"bgr": (0, 135, 245), "hex": "#f97316"},
    "YELLOW": {"bgr": (0, 215, 245), "hex": "#eab308"},
    "GREEN": {"bgr": (40, 205, 50), "hex": "#22c55e"},
    "CYAN": {"bgr": (220, 190, 0), "hex": "#06b6d4"},
    "BLUE": {"bgr": (240, 110, 20), "hex": "#3b82f6"},
    "PURPLE": {"bgr": (210, 60, 175), "hex": "#a855f7"},
    "PINK": {"bgr": (190, 90, 240), "hex": "#ec4899"},
    "BROWN": {"bgr": (25, 75, 140), "hex": "#854d0e"},
    "BLACK": {"bgr": (35, 35, 35), "hex": "#1e293b"},
    "WHITE": {"bgr": (240, 240, 240), "hex": "#f8fafc"},
    "GRAY": {"bgr": (140, 140, 140), "hex": "#94a3b8"}
}


def classify_roi_color(roi_bgr: np.ndarray) -> Tuple[str, Tuple[int, int, int], str]:
    """
    Classifies the dominant physical color of an object bounding box ROI.
    Returns: (Color Name, BGR Tuple, Hex Code)
    """
    if roi_bgr is None or roi_bgr.size == 0 or roi_bgr.shape[0] < 4 or roi_bgr.shape[1] < 4:
        return "UNKNOWN", (128, 128, 128), "#64748b"

    # Analyze inner core (70%) to avoid background edge bleed
    rh, rw = roi_bgr.shape[:2]
    ch_start, ch_end = int(rh * 0.15), int(rh * 0.85)
    cw_start, cw_end = int(rw * 0.15), int(rw * 0.85)
    core = roi_bgr[ch_start:ch_end, cw_start:cw_end]
    if core.size == 0:
        core = roi_bgr

    hsv = cv2.cvtColor(core, cv2.COLOR_BGR2HSV)
    h_chan = hsv[:, :, 0]
    s_chan = hsv[:, :, 1]
    v_chan = hsv[:, :, 2]

    med_v = float(np.median(v_chan))
    med_s = float(np.median(s_chan))
    med_h = float(np.median(h_chan))

    # 1. Achromatic checks (Black / White / Gray)
    if med_v < 46 or (med_v < 60 and med_s < 45):
        c = "BLACK"
    elif med_s < 30 and med_v > 165:
        c = "WHITE"
    elif med_s < 42 and 46 <= med_v <= 165:
        c = "GRAY"
    # 2. Brown check
    elif 8 <= med_h < 25 and med_s >= 40 and 45 <= med_v < 125:
        c = "BROWN"
    # 3. Chromatic Hues
    elif med_h < 8 or med_h >= 168:
        c = "RED"
    elif 8 <= med_h < 24:
        c = "ORANGE"
    elif 24 <= med_h < 36:
        c = "YELLOW"
    elif 36 <= med_h < 85:
        c = "GREEN"
    elif 85 <= med_h < 102:
        c = "CYAN"
    elif 102 <= med_h < 135:
        c = "BLUE"
    elif 135 <= med_h < 155:
        c = "PURPLE"
    elif 155 <= med_h < 168:
        c = "PINK"
    else:
        c = "GRAY"

    meta = COLOR_PALETTE.get(c, {"bgr": (128, 128, 128), "hex": "#64748b"})
    return c, meta["bgr"], meta["hex"]


# ==============================================================================
# YOLO OBJECT DETECTION & COLOR ANNOTATION
# ==============================================================================
def process_frame_detections(frame: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Runs YOLO object detection on the enhanced frame and classifies object colors."""
    h, w = frame.shape[:2]
    annotated = frame.copy()

    # Run YOLOv8 inference
    results = yolo_model.predict(
        frame,
        imgsz=640,
        conf=confidence_cutoff,
        verbose=False
    )[0]

    detected_items = []
    color_dist: Dict[str, int] = {}

    if results.boxes is not None:
        for b in results.boxes:
            x1, y1, x2, y2 = [int(v) for v in b.xyxy[0]]
            cls_id = int(b.cls[0])
            obj_name = yolo_model.names[cls_id]
            conf = float(b.conf[0])

            # Clamp bounding box
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            if x2 <= x1 or y2 <= y1:
                continue

            # Crop object and classify its color
            crop = frame[y1:y2, x1:x2]
            color_name, bgr_color, hex_color = classify_roi_color(crop)

            color_dist[color_name] = color_dist.get(color_name, 0) + 1

            detected_items.append({
                "object": obj_name,
                "color": color_name,
                "color_hex": hex_color,
                "bgr": bgr_color,
                "confidence": round(conf * 100.0, 1),
                "bbox": [x1, y1, x2, y2]
            })

            # Draw visual annotation
            cv2.rectangle(annotated, (x1, y1), (x2, y2), bgr_color, 2)

            label = f"{obj_name.upper()} • {color_name} ({int(conf * 100)}%)"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.55 if w < 1200 else 0.70
            thickness = 1 if w < 1200 else 2
            (lw, lh), _ = cv2.getTextSize(label, font, font_scale, thickness)

            # Badge background
            badge_y1 = max(0, y1 - lh - 8)
            badge_y2 = max(lh + 8, y1)
            cv2.rectangle(annotated, (x1, badge_y1), (x1 + lw + 12, badge_y2), bgr_color, -1)

            # Text color (contrast-aware)
            text_color = (0, 0, 0) if color_name in ["WHITE", "YELLOW", "CYAN", "PINK"] else (255, 255, 255)
            cv2.putText(annotated, label, (x1 + 6, max(lh + 2, y1 - 3)), font, font_scale, text_color, thickness, cv2.LINE_AA)

    # Top HUD Bar
    hud_h = 50 if h < 1000 else 64
    cv2.rectangle(annotated, (0, 0), (w, hud_h), (16, 18, 22), -1)
    cv2.line(annotated, (0, hud_h), (w, hud_h), (50, 55, 65), 1)

    hud_font = cv2.FONT_HERSHEY_SIMPLEX
    hud_scale = 0.6 if w < 1200 else 0.75
    cv2.putText(annotated, "VISION AI • OBJECT & COLOR DETECTOR", (18, int(hud_h * 0.65)),
                hud_font, hud_scale, (0, 210, 255), 2, cv2.LINE_AA)

    # Tally in HUD
    tally_items = [f"{k}: {v}" for k, v in sorted(color_dist.items())]
    tally_str = f"Objects: {len(detected_items)}" + (f" | {' • '.join(tally_items)}" if tally_items else " | Scanning...")
    (tw, th), _ = cv2.getTextSize(tally_str, hud_font, hud_scale * 0.75, 1)
    cv2.putText(annotated, tally_str, (w - tw - 18, int(hud_h * 0.65)),
                hud_font, hud_scale * 0.75, (220, 220, 220), 1, cv2.LINE_AA)

    telemetry = {
        "detected_objects": [
            {
                "object": it["object"],
                "color": it["color"],
                "color_hex": it["color_hex"],
                "confidence": it["confidence"],
                "bbox": it["bbox"]
            }
            for it in detected_items
        ],
        "color_distribution": color_dist,
        "total_detections": len(detected_items)
    }

    return annotated, telemetry


# ==============================================================================
# BACKGROUND VIDEO CAPTURE WORKER
# ==============================================================================
def video_capture_worker():
    """Continuously fetches frames, enhances lens colors, runs YOLO detection, and feeds stream."""
    global baumer_cam, baumer_connected, camera_source, latest_jpeg_frame, latest_telemetry, latest_frame_id

    fps_count = 0
    fps_timer = time.time()
    current_fps = 0.0

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
                    logger.warning(f"Baumer connection: {e}")
                    baumer_connected = False
                    time.sleep(2.0)
                    continue

            # Fetch raw frame from Baumer camera
            raw_frame, info = baumer_cam.get_frame(timeout=0.6)
            if raw_frame is not None:
                # Run Lens Color Enhancement (White Balance + Tone Mapping + Vibrancy)
                frame = enhance_lens_frame(raw_frame)
            else:
                time.sleep(0.01)
        else:
            # Simulated Feed fallback
            if baumer_cam is not None:
                try:
                    baumer_cam.stop_stream()
                    baumer_cam.disconnect()
                except Exception:
                    pass
                baumer_cam = None
                baumer_connected = False

            # Synthetic colorful test frame
            sim_frame = np.full((720, 1280, 3), (25, 28, 34), dtype=np.uint8)
            cv2.circle(sim_frame, (320, 360), 90, (240, 60, 40), -1)   # Blue
            cv2.rectangle(sim_frame, (520, 270), (700, 450), (40, 205, 50), -1) # Green
            cv2.circle(sim_frame, (900, 360), 90, (30, 30, 235), -1)   # Red
            frame = sim_frame
            time.sleep(0.05)

        if frame is not None:
            # FPS Calculation
            fps_count += 1
            now = time.time()
            if now - fps_timer >= 1.0:
                current_fps = round(fps_count / (now - fps_timer), 1)
                fps_count = 0
                fps_timer = now

            # Run Object Detection & Color Classification
            annotated_frame, telemetry = process_frame_detections(frame)

            # Downsample for responsive web streaming if very high res
            h, w = annotated_frame.shape[:2]
            if w > 1280:
                scale = 1280.0 / w
                stream_frame = cv2.resize(annotated_frame, (1280, int(h * scale)), interpolation=cv2.INTER_LINEAR)
            else:
                stream_frame = annotated_frame

            ret, jpeg = cv2.imencode('.jpg', stream_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret:
                with frame_cond:
                    latest_jpeg_frame = jpeg.tobytes()
                    latest_frame_id += 1
                    latest_telemetry.update({
                        "camera_source": camera_source,
                        "camera_connected": baumer_connected,
                        "fps": current_fps,
                        "exposure_ms": baumer_exposure_ms,
                        "lens_settings": dict(lens_settings),
                        "detected_objects": telemetry["detected_objects"],
                        "color_distribution": telemetry["color_distribution"],
                        "total_detections": telemetry["total_detections"]
                    })
                    frame_cond.notify_all()
        else:
            time.sleep(0.02)


# Launch video worker thread
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
    """Returns live telemetry, lens adjustments, detected objects, and color counts."""
    with frame_cond:
        return jsonify(dict(latest_telemetry))


@app.route('/api/set_source', methods=['POST'])
def set_source():
    """Toggle between physical Baumer camera and simulated feed."""
    global camera_source
    data = request.json or {}
    source = data.get("source", "baumer").lower()
    if source in ["baumer", "simulated"]:
        camera_source = source
        print(f"Switched camera source to: {camera_source}")
    return jsonify({"camera_source": camera_source})


@app.route('/api/set_exposure', methods=['POST'])
def set_exposure():
    """Adjusts exposure time of the Baumer GigE camera in milliseconds."""
    global baumer_exposure_ms
    data = request.json or {}
    exp = float(data.get("exposure_ms", 30.0))
    baumer_exposure_ms = max(1.0, min(100.0, exp))

    if baumer_cam is not None and baumer_connected:
        try:
            baumer_cam.set_exposure_time(int(baumer_exposure_ms * 1000))
        except Exception as e:
            logger.warning(f"Error setting exposure: {e}")

    return jsonify({"exposure_ms": baumer_exposure_ms})


@app.route('/api/set_confidence', methods=['POST'])
def set_confidence():
    """Sets YOLO detection confidence cutoff."""
    global confidence_cutoff
    data = request.json or {}
    conf = float(data.get("confidence", 0.20))
    confidence_cutoff = max(0.05, min(0.95, conf))
    return jsonify({"confidence_cutoff": confidence_cutoff})


@app.route('/api/set_lens', methods=['POST'])
def set_lens():
    """Adjusts real-time lens ISP settings: brightness, contrast, saturation, gamma, auto_wb."""
    data = request.json or {}
    if "brightness" in data:
        lens_settings["brightness"] = float(data["brightness"])
    if "contrast" in data:
        lens_settings["contrast"] = float(data["contrast"])
    if "saturation" in data:
        lens_settings["saturation"] = float(data["saturation"])
    if "gamma" in data:
        lens_settings["gamma"] = float(data["gamma"])
    if "auto_wb" in data:
        lens_settings["auto_wb"] = bool(data["auto_wb"])

    return jsonify({"lens_settings": lens_settings})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5050))
    print(f"\n🚀 Starting Vision AI Object & Color Detection Dashboard on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
