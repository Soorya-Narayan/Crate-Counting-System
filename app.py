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
custom_weights = "milma_best.pt" if os.path.exists("milma_best.pt") else "yolov8n.pt"
print(f"Loading custom Milma YOLO model from: {custom_weights}...")
yolo_model = YOLO(custom_weights)
print(f"✓ Milma YOLO model ready ({len(yolo_model.names)} classes: {list(yolo_model.names.values())}).")

# Detection cutoff (tuned for zero duplicate count on shingled pouches)
confidence_cutoff = 0.38

# Hardware Camera & Lens ISP Settings
baumer_cam: Optional[BaumerCamera] = None
baumer_connected = False
camera_source = "simulated"  # 'simulated' (dataset playback) or 'baumer' (physical camera)
baumer_exposure_ms = 30.0

# Live Lens ISP Adjustments
lens_settings = {
    "brightness": 5,        # -50 to +50
    "contrast": 1.18,       # 0.5 to 2.0
    "saturation": 1.35,     # 0.5 to 2.5
    "gamma": 0.85,          # 0.5 to 1.5
    "auto_wb": True         # Auto white balance (Gray World)
}

# Conveyor ROI & ByteTrack Tripwire State
roi_settings = {
    "enabled": True,
    "ymin": 0.04,
    "xmin": 0.04,
    "ymax": 0.96,
    "xmax": 0.96
}
tripwire_settings = {
    "enabled": True,
    "y_norm": 0.52
}
# Detection and Counting Engine Filters
detection_filters = {
    "detect_pouches": True,
    "detect_crates": True
}

tracker_state = {
    "total_counted_pouches": 0,
    "total_counted_crates": 0,
    "pulse_frames": 0,
    "counted_track_ids": set(),
    "counted_crate_track_ids": set(),
    "track_prev_positions": {},
    "last_audit_status": "NOMINAL (20/20)",
    "last_audit_class": "badge-pass",
    "current_crate_pouches": 0,
    "current_crates_count": 0
}

# Stream Frame & Telemetry State
latest_jpeg_frame: Optional[bytes] = None
latest_telemetry: Dict[str, Any] = {
    "camera_source": "simulated",
    "camera_connected": False,
    "fps": 0.0,
    "exposure_ms": 30.0,
    "lens_settings": lens_settings,
    "detected_objects": [],
    "color_distribution": {},
    "total_detections": 0,
    "roi_enabled": True,
    "detect_pouches": True,
    "detect_crates": True,
    "total_counted_pouches": 0,
    "total_counted_crates": 0,
    "current_crate_pouches": 0,
    "current_crates_count": 0,
    "last_audit_status": "NOMINAL (20/20)",
    "last_audit_class": "badge-pass"
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
    """
    Runs ByteTrack multi-object tracking on the enhanced frame,
    filters candidates through Conveyor ROI Masking and user-toggled Pouch/Crate filters,
    applies IoS containment deduplication,
    and updates virtual tripwire crossing counters for both pouches and crates.
    """
    global tracker_state, roi_settings, tripwire_settings, detection_filters
    h, w = frame.shape[:2]
    annotated = frame.copy()

    # Calculate Conveyor ROI pixel bounds
    rx1 = int(roi_settings.get("xmin", 0.04) * w)
    ry1 = int(roi_settings.get("ymin", 0.04) * h)
    rx2 = int(roi_settings.get("xmax", 0.96) * w)
    ry2 = int(roi_settings.get("ymax", 0.96) * h)
    is_roi_enabled = roi_settings.get("enabled", True)

    detect_pouches = detection_filters.get("detect_pouches", True)
    detect_crates = detection_filters.get("detect_crates", True)

    # Run ByteTrack tracking with calibrated NMS IoU threshold (0.45)
    results = yolo_model.track(
        frame,
        tracker="bytetrack.yaml",
        persist=True,
        imgsz=640,
        conf=confidence_cutoff,
        iou=0.45,
        verbose=False
    )[0]

    track_ids = results.boxes.id if results.boxes is not None else None

    raw_candidates = []
    if results.boxes is not None:
        for idx, b in enumerate(results.boxes):
            x1, y1, x2, y2 = [int(v) for v in b.xyxy[0]]
            cls_id = int(b.cls[0])
            obj_name = yolo_model.names[cls_id]
            conf = float(b.conf[0])
            tid = int(track_ids[idx].item()) if (track_ids is not None and len(track_ids) > idx) else None

            is_pouch = "pouch" in obj_name
            is_crate = obj_name in ["crate", "empty_tray"]

            # Filter candidates based on active detection toggles
            if is_pouch and not detect_pouches:
                continue
            if is_crate and not detect_crates:
                continue

            # Clamp bounding box
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            if x2 <= x1 or y2 <= y1:
                continue

            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2

            # Conveyor ROI Masking: suppress perimeter clutter, hands, ambient floor
            if is_roi_enabled and not (rx1 <= cx <= rx2 and ry1 <= cy <= ry2):
                continue

            area = (x2 - x1) * (y2 - y1)
            raw_candidates.append({
                "bbox": (x1, y1, x2, y2),
                "center": (cx, cy),
                "conf": conf,
                "obj_name": obj_name,
                "track_id": tid,
                "area": area
            })

    # Sort candidates by confidence descending
    raw_candidates.sort(key=lambda it: it["conf"], reverse=True)

    # IoS (Intersection over Smaller) Containment Deduplication
    filtered_items = []
    for cand in raw_candidates:
        cx1, cy1, cx2, cy2 = cand["bbox"]
        c_area = cand["area"]
        is_pouch = "pouch" in cand["obj_name"]

        is_dup = False
        if is_pouch:
            for kept in filtered_items:
                if "pouch" not in kept["obj_name"]:
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
            filtered_items.append(cand)

    # Separate pouch vs crate items
    pouch_items = [it for it in filtered_items if "pouch" in it["obj_name"]]
    crate_items = [it for it in filtered_items if it["obj_name"] in ["crate", "empty_tray"]]

    crate_pouch_count = len(pouch_items) if detect_pouches else 0
    crates_in_view = len(crate_items) if detect_crates else 0
    tracker_state["current_crate_pouches"] = crate_pouch_count
    tracker_state["current_crates_count"] = crates_in_view

    # Tripwire Line Crossing Logic
    line_y = int(tripwire_settings.get("y_norm", 0.52) * h)
    now_time = time.time()

    # 1. Pouch crossing tracking
    if detect_pouches:
        for item in pouch_items:
            tid = item["track_id"]
            cx, cy = item["center"]
            if tid is not None:
                prev_info = tracker_state["track_prev_positions"].get(tid)
                if prev_info is not None:
                    prev_cx, prev_cy, _ = prev_info
                    # Check crossing top to bottom (or reverse)
                    if (prev_cy < line_y <= cy) or (prev_cy > line_y >= cy):
                        if tid not in tracker_state["counted_track_ids"]:
                            tracker_state["counted_track_ids"].add(tid)
                            tracker_state["total_counted_pouches"] += 1
                            tracker_state["pulse_frames"] = 8
                tracker_state["track_prev_positions"][tid] = (cx, cy, now_time)

    # 2. Crate crossing tracking
    if detect_crates:
        for item in crate_items:
            tid = item["track_id"]
            cx, cy = item["center"]
            if tid is not None:
                prev_info = tracker_state["track_prev_positions"].get(tid)
                if prev_info is not None:
                    prev_cx, prev_cy, _ = prev_info
                    if (prev_cy < line_y <= cy) or (prev_cy > line_y >= cy):
                        if tid not in tracker_state["counted_crate_track_ids"]:
                            tracker_state["counted_crate_track_ids"].add(tid)
                            tracker_state["total_counted_crates"] += 1
                            tracker_state["pulse_frames"] = 8
                tracker_state["track_prev_positions"][tid] = (cx, cy, now_time)

    # Clean old tracks (> 30s)
    if len(tracker_state["track_prev_positions"]) > 400:
        tracker_state["track_prev_positions"] = {
            k: v for k, v in tracker_state["track_prev_positions"].items()
            if now_time - v[2] < 30.0
        }

    # Crate Audit Verdict
    if not detect_pouches:
        tracker_state["last_audit_status"] = "POUCH DETECTION PAUSED"
        tracker_state["last_audit_class"] = "badge-warn"
    elif crate_pouch_count == 20:
        tracker_state["last_audit_status"] = "PASSED: NOMINAL (20/20)"
        tracker_state["last_audit_class"] = "badge-pass"
    elif crate_pouch_count in [18, 19]:
        tracker_state["last_audit_status"] = f"DEFECT: UNDERFILLED ({crate_pouch_count}/20)"
        tracker_state["last_audit_class"] = "badge-fail"
    elif crate_pouch_count > 20:
        tracker_state["last_audit_status"] = f"DEFECT: OVERFILLED ({crate_pouch_count}/20)"
        tracker_state["last_audit_class"] = "badge-fail"
    elif crate_pouch_count == 0:
        tracker_state["last_audit_status"] = "EMPTY CONVEYOR / TRAY"
        tracker_state["last_audit_class"] = "badge-warn"

    # VISUAL OVERLAYS:
    # 1. Conveyor ROI Mask Boundary
    if is_roi_enabled:
        cv2.rectangle(annotated, (rx1, ry1), (rx2, ry2), (0, 220, 255), 2)
        cv2.putText(annotated, "[ CONVEYOR INSPECTION ROI - ACTIVE ]", (rx1 + 12, max(24, ry1 + 22)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 2, cv2.LINE_AA)

    # 2. Tripwire Virtual Line
    if tripwire_settings.get("enabled", True):
        is_pulsing = tracker_state["pulse_frames"] > 0
        if is_pulsing:
            tracker_state["pulse_frames"] -= 1
        tw_color = (40, 245, 60) if is_pulsing else (0, 165, 255)
        tw_thick = 3 if is_pulsing else 2
        cv2.line(annotated, (rx1, line_y), (rx2, line_y), tw_color, tw_thick)
        tw_label = f"TRIPWIRE • POUCHES: {tracker_state['total_counted_pouches']} | CRATES: {tracker_state['total_counted_crates']}"
        cv2.putText(annotated, tw_label, (rx1 + 12, max(25, line_y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, tw_color, 2, cv2.LINE_AA)

    detected_items = []
    color_dist: Dict[str, int] = {}

    CUSTOM_CLASSES = {
        "crate": {"bgr": (240, 110, 20), "hex": "#3b82f6", "color": "BLUE"},
        "empty_tray": {"bgr": (0, 215, 245), "hex": "#eab308", "color": "YELLOW"},
        "pouch_green": {"bgr": (40, 205, 50), "hex": "#22c55e", "color": "GREEN"},
        "pouch_orange": {"bgr": (0, 135, 245), "hex": "#f97316", "color": "ORANGE"},
        "pouch_purple": {"bgr": (210, 60, 175), "hex": "#a855f7", "color": "PURPLE"}
    }

    for item in filtered_items:
        x1, y1, x2, y2 = item["bbox"]
        obj_name = item["obj_name"]
        conf = item["conf"]
        tid = item["track_id"]

        if obj_name in CUSTOM_CLASSES:
            c_info = CUSTOM_CLASSES[obj_name]
            color_name = c_info["color"]
            bgr_color = c_info["bgr"]
            hex_color = c_info["hex"]
        else:
            crop = frame[y1:y2, x1:x2]
            color_name, bgr_color, hex_color = classify_roi_color(crop)

        color_dist[color_name] = color_dist.get(color_name, 0) + 1

        detected_items.append({
            "object": obj_name,
            "color": color_name,
            "color_hex": hex_color,
            "bgr": bgr_color,
            "confidence": round(conf * 100.0, 1),
            "track_id": tid,
            "bbox": [x1, y1, x2, y2]
        })

        # Draw visual annotation
        cv2.rectangle(annotated, (x1, y1), (x2, y2), bgr_color, 2)

        tid_tag = f" #{tid}" if tid is not None else ""
        label = f"{obj_name.upper()}{tid_tag} • {color_name} ({int(conf * 100)}%)"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.52 if w < 1200 else 0.65
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
    cv2.putText(annotated, "MILMA VISION AI • BYTETRACK & ROI INSPECTION", (18, int(hud_h * 0.65)),
                hud_font, hud_scale, (0, 215, 255), 2, cv2.LINE_AA)

    # Tally in HUD
    tally_items = [f"{k}: {v}" for k, v in sorted(color_dist.items())]
    pouch_status_str = f"Pouches: {crate_pouch_count}/20" if detect_pouches else "Pouches: OFF"
    crate_status_str = f"Crates: {crates_in_view}" if detect_crates else "Crates: OFF"
    tally_str = f"{pouch_status_str} | {crate_status_str}" + (f" | {' • '.join(tally_items)}" if tally_items else "")
    (tw, th), _ = cv2.getTextSize(tally_str, hud_font, hud_scale * 0.72, 1)
    cv2.putText(annotated, tally_str, (w - tw - 18, int(hud_h * 0.65)),
                hud_font, hud_scale * 0.72, (220, 220, 220), 1, cv2.LINE_AA)

    telemetry = {
        "detected_objects": [
            {
                "object": it["object"],
                "color": it["color"],
                "color_hex": it["color_hex"],
                "confidence": it["confidence"],
                "track_id": it.get("track_id"),
                "bbox": it["bbox"]
            }
            for it in detected_items
        ],
        "color_distribution": color_dist,
        "total_detections": len(detected_items),
        "detect_pouches": detect_pouches,
        "detect_crates": detect_crates,
        "current_crate_pouches": crate_pouch_count,
        "total_counted_pouches": tracker_state["total_counted_pouches"],
        "current_crates_count": crates_in_view,
        "total_counted_crates": tracker_state["total_counted_crates"],
        "last_audit_status": tracker_state["last_audit_status"],
        "last_audit_class": tracker_state["last_audit_class"],
        "roi_enabled": is_roi_enabled,
        "active_tracks_count": len(tracker_state["track_prev_positions"])
    }

    return annotated, telemetry


def make_baumer_standby_frame(error_msg: str = "") -> np.ndarray:
    """Renders a sleek, animated diagnostic screen when Baumer GigE camera is searching/offline."""
    w, h = 1280, 720
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    frame[:] = (18, 22, 28)

    # Technical grid
    for gx in range(0, w, 64):
        cv2.line(frame, (gx, 0), (gx, h), (26, 32, 42), 1)
    for gy in range(0, h, 64):
        cv2.line(frame, (0, gy), (w, gy), (26, 32, 42), 1)

    # Center card
    cv2.rectangle(frame, (120, 80), (w - 120, h - 80), (28, 35, 48), -1)
    cv2.rectangle(frame, (120, 80), (w - 120, h - 80), (0, 180, 255), 2)

    # Header
    cv2.putText(frame, "BAUMER VCXG.2-32C • GIGE MACHINE VISION", (160, 140),
                cv2.FONT_HERSHEY_SIMPLEX, 0.82, (0, 220, 255), 2, cv2.LINE_AA)
    cv2.line(frame, (160, 160), (w - 160, 160), (50, 65, 85), 1)

    # Pulsing search indicator
    dots = "." * (int(time.time() * 2) % 4 + 1)
    cv2.putText(frame, f"SEARCHING FOR CAMERA ON NETWORK{dots}", (160, 215),
                cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 255, 255), 2, cv2.LINE_AA)

    cv2.putText(frame, "Target IP: 169.254.123.85 (GigE Vision UDP Port 3956)", (160, 255),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 175, 195), 1, cv2.LINE_AA)

    # Hardware checklist
    checklist = [
        ("1. CAMERA POWER", "Baumer requires 12V-24V DC on 8-pin plug (or PoE Injector).", (240, 200, 80)),
        ("2. RJ45 LINK LED", "Ethernet jack on camera MUST show solid/blinking Green LED.", (40, 220, 80)),
        ("3. MAC ADAPTER", "MacBook Pro requires USB-C to Ethernet adapter in Thunderbolt port.", (240, 140, 80)),
        ("4. DIAGNOSTIC", error_msg or "Waiting for physical Ethernet carrier / link-local ARP...", (120, 170, 255))
    ]

    y_pos = 320
    for title, desc, col in checklist:
        cv2.putText(frame, f"• {title}:", (160, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 2, cv2.LINE_AA)
        cv2.putText(frame, desc, (360, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (220, 225, 235), 1, cv2.LINE_AA)
        y_pos += 46

    cv2.putText(frame, "Milma Vision AI Engine • Continuous auto-reconnect active", (160, h - 110),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (120, 135, 155), 1, cv2.LINE_AA)
    return frame


# ==============================================================================
# BACKGROUND VIDEO CAPTURE WORKER
# ==============================================================================
def video_capture_worker():
    """Continuously fetches frames, enhances lens colors, runs YOLO detection, and feeds stream."""
    global baumer_cam, baumer_connected, camera_source, latest_jpeg_frame, latest_telemetry, latest_frame_id

    webcam_cap = None
    fps_count = 0
    fps_timer = time.time()
    current_fps = 0.0
    baumer_last_error = ""
    last_baumer_attempt = 0.0

    while True:
        frame = None
        is_baumer_standby = False

        if camera_source == "baumer":
            if webcam_cap is not None:
                try:
                    webcam_cap.release()
                except Exception:
                    pass
                webcam_cap = None

            now_s = time.time()
            if baumer_cam is None and (now_s - last_baumer_attempt > 2.0):
                last_baumer_attempt = now_s
                try:
                    print("Connecting to Baumer VCXG.2-32C at 169.254.123.85...")
                    cam = BaumerCamera(camera_ip="169.254.123.85", host_ip="169.254.128.78")
                    cam.connect()
                    cam.set_exposure_time(int(baumer_exposure_ms * 1000))
                    cam.start_stream()
                    baumer_cam = cam
                    baumer_connected = True
                    baumer_last_error = ""
                    print("✓ Baumer camera online and streaming.")
                except Exception as e:
                    baumer_last_error = str(e)
                    logger.warning(f"Baumer connection: {e}")
                    baumer_connected = False

            if baumer_cam is not None and baumer_connected:
                raw_frame, info = baumer_cam.get_frame(timeout=0.4)
                if raw_frame is not None:
                    frame = enhance_lens_frame(raw_frame)
                else:
                    time.sleep(0.01)

            # If not yet streaming from Baumer, show standby diagnostic screen
            if frame is None:
                frame = make_baumer_standby_frame(baumer_last_error)
                is_baumer_standby = True
                time.sleep(0.08)

        elif camera_source == "webcam":
            if baumer_cam is not None:
                try:
                    baumer_cam.stop_stream()
                    baumer_cam.disconnect()
                except Exception:
                    pass
                baumer_cam = None
                baumer_connected = False

            if webcam_cap is None or not webcam_cap.isOpened():
                try:
                    webcam_cap = cv2.VideoCapture(0)
                    webcam_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                    webcam_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                    time.sleep(0.2)
                except Exception as e:
                    logger.warning(f"Mac Webcam init error: {e}")
                    time.sleep(1.0)
                    continue

            ret, raw_frame = webcam_cap.read()
            if ret and raw_frame is not None:
                frame = enhance_lens_frame(raw_frame)
            else:
                time.sleep(0.02)

        else:
            # Simulated Feed fallback
            if webcam_cap is not None:
                try:
                    webcam_cap.release()
                except Exception:
                    pass
                webcam_cap = None

            if baumer_cam is not None:
                try:
                    baumer_cam.stop_stream()
                    baumer_cam.disconnect()
                except Exception:
                    pass
                baumer_cam = None
                baumer_connected = False

            # Simulated Feed fallback (cycles through real plant test crates)
            if not hasattr(video_capture_worker, "test_images"):
                import glob
                t_imgs = sorted(glob.glob("master_yolo_dataset/images/test/*.jpg"))
                video_capture_worker.test_images = t_imgs
                video_capture_worker.img_idx = 0
                video_capture_worker.last_switch = 0.0

            if getattr(video_capture_worker, "test_images", None):
                now_s = time.time()
                if now_s - video_capture_worker.last_switch > 2.0:
                    video_capture_worker.img_idx = (video_capture_worker.img_idx + 1) % len(video_capture_worker.test_images)
                    video_capture_worker.last_switch = now_s
                
                img_path = video_capture_worker.test_images[video_capture_worker.img_idx]
                loaded_frame = cv2.imread(img_path)
                if loaded_frame is not None:
                    frame = loaded_frame
                else:
                    frame = np.full((720, 1280, 3), (25, 28, 34), dtype=np.uint8)
                time.sleep(0.04)
            else:
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

            # Run Object Detection & Color Classification (skip on standby diagnostic screen)
            if is_baumer_standby:
                annotated_frame = frame
                telemetry = {
                    "detected_objects": [],
                    "color_distribution": {},
                    "total_detections": 0,
                    "detect_pouches": detection_filters.get("detect_pouches", True),
                    "detect_crates": detection_filters.get("detect_crates", True),
                    "current_crate_pouches": 0,
                    "total_counted_pouches": tracker_state["total_counted_pouches"],
                    "current_crates_count": 0,
                    "total_counted_crates": tracker_state["total_counted_crates"],
                    "last_audit_status": "SEARCHING FOR BAUMER CAMERA...",
                    "last_audit_class": "badge-warn",
                    "roi_enabled": roi_settings.get("enabled", True),
                    "active_tracks_count": 0
                }
            else:
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
                        "total_detections": telemetry["total_detections"],
                        "detect_pouches": telemetry["detect_pouches"],
                        "detect_crates": telemetry["detect_crates"],
                        "current_crate_pouches": telemetry["current_crate_pouches"],
                        "total_counted_pouches": telemetry["total_counted_pouches"],
                        "current_crates_count": telemetry["current_crates_count"],
                        "total_counted_crates": telemetry["total_counted_crates"],
                        "last_audit_status": telemetry["last_audit_status"],
                        "last_audit_class": telemetry["last_audit_class"],
                        "roi_enabled": telemetry["roi_enabled"],
                        "active_tracks_count": telemetry["active_tracks_count"]
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
    """Toggle between physical Baumer camera, Mac webcam, and simulated test feed."""
    global camera_source
    data = request.json or {}
    source = data.get("source", "baumer").lower()
    if source in ["baumer", "webcam", "simulated"]:
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


@app.route('/api/toggle_roi', methods=['POST'])
def toggle_roi():
    """Toggle conveyor inspection ROI on/off."""
    global roi_settings
    data = request.json or {}
    if "enabled" in data:
        roi_settings["enabled"] = bool(data["enabled"])
    else:
        roi_settings["enabled"] = not roi_settings["enabled"]
    return jsonify({"roi_enabled": roi_settings["enabled"]})


@app.route('/api/toggle_detection', methods=['POST'])
def toggle_detection():
    """Toggle pouch or crate detection & count engine on/off."""
    global detection_filters
    data = request.json or {}
    target = data.get("target", "").lower()

    if target in ["pouch", "pouches"]:
        if "enabled" in data:
            detection_filters["detect_pouches"] = bool(data["enabled"])
        else:
            detection_filters["detect_pouches"] = not detection_filters["detect_pouches"]
    elif target in ["crate", "crates"]:
        if "enabled" in data:
            detection_filters["detect_crates"] = bool(data["enabled"])
        else:
            detection_filters["detect_crates"] = not detection_filters["detect_crates"]

    return jsonify({
        "detect_pouches": detection_filters["detect_pouches"],
        "detect_crates": detection_filters["detect_crates"]
    })


@app.route('/api/reset_tripwire', methods=['POST'])
def reset_tripwire():
    """Resets persistent tripwire pouch and crate counts."""
    global tracker_state
    tracker_state["total_counted_pouches"] = 0
    tracker_state["total_counted_crates"] = 0
    tracker_state["counted_track_ids"].clear()
    tracker_state["counted_crate_track_ids"].clear()
    tracker_state["track_prev_positions"].clear()
    return jsonify({
        "total_counted_pouches": 0,
        "total_counted_crates": 0
    })


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5050))
    print(f"\n🚀 Starting Vision AI Object & Color Detection Dashboard on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
