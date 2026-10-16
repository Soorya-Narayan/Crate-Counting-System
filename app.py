"""
Milma Kottayam Dairy - Real-Time Operator Web Dashboard & HMI
============================================================
Application: app.py
Company: Goose Industrial Solutions
Client: Milma (E.R.C.M.P.U. Ltd.), Kottayam Dairy Plant

Features:
- Live MJPEG video stream with YOLO instance segmentation overlays.
- Real-time shopfloor telemetry: pass/fail verdicts, shift counters, variant breakdown.
- Interactive controls: simulate live conveyor (24 crates/min), inject underfill defects.
- Incident audit log with timestamped snapshot inspection.
- Automated shift report CSV export.
"""

import os
import io
import time
import csv
import threading
from datetime import datetime
from typing import Dict, Any, List

from flask import Flask, render_template, Response, jsonify, request, send_file
import cv2
import numpy as np

from milma_counter import MilmaPouchCounter, PouchVariant, CrateStatus, generate_synthetic_milma_crate

app = Flask(__name__)

# Global Application State
counter_engine = MilmaPouchCounter()
active_variant = PouchVariant.ORANGE
auto_cycle_variant = True
conveyor_running = True
crates_per_minute = 24.0   # Default Milma line speed: 24 crates/min
latest_crate_result = None
latest_jpeg_frame = None
incident_history: List[Dict[str, Any]] = []
audit_snapshots: Dict[str, bytes] = {}  # crate_id -> jpeg bytes
state_lock = threading.Lock()

# Sequence of variants for auto-cycling
CYCLE_VARIANTS = [PouchVariant.ORANGE, PouchVariant.VIOLET, PouchVariant.GREEN]
variant_cycle_idx = 0


def process_new_crate(variant: PouchVariant, num_pouches: int = 20) -> Any:
    """Simulates a crate passing the camera and processes it through the engine."""
    global latest_crate_result, latest_jpeg_frame, incident_history, audit_snapshots

    # Generate synthetic camera frame
    raw_frame = generate_synthetic_milma_crate(variant=variant, num_pouches=num_pouches)

    # Process frame through counting engine
    result = counter_engine.process_crate(raw_frame)

    # Encode annotated frame to JPEG for live stream
    ret, jpeg = cv2.imencode('.jpg', result.annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    jpeg_bytes = jpeg.tobytes() if ret else b''

    with state_lock:
        latest_crate_result = result
        latest_jpeg_frame = jpeg_bytes

        # If not passed (underfilled or overfilled), record into incident log
        if result.status != CrateStatus.PASSED:
            incident_entry = {
                "crate_id": result.crate_id,
                "timestamp": datetime.fromtimestamp(result.timestamp).strftime('%H:%M:%S'),
                "variant": result.dominant_variant.value,
                "detected_count": result.total_pouches,
                "expected_count": result.expected_count,
                "discrepancy": result.total_pouches - result.expected_count,
                "status": result.status.value,
                "latency_ms": round(result.latency_ms, 1)
            }
            incident_history.insert(0, incident_entry)
            if len(incident_history) > 50:
                incident_history.pop()

            # Store audit snapshot
            audit_snapshots[result.crate_id] = jpeg_bytes

    return result


def conveyor_worker_loop():
    """Background worker simulating active conveyor line at specified line speed."""
    global variant_cycle_idx, active_variant

    # Initial frame
    process_new_crate(PouchVariant.ORANGE, 20)

    crate_seq = 0
    while True:
        if conveyor_running:
            crate_seq += 1

            # Decide variant
            if auto_cycle_variant:
                # Switch variant every 15 crates to simulate real batch runs
                if crate_seq % 15 == 0:
                    variant_cycle_idx = (variant_cycle_idx + 1) % len(CYCLE_VARIANTS)
                cur_var = CYCLE_VARIANTS[variant_cycle_idx]
            else:
                cur_var = active_variant

            # Inject realistic occasional underfill defect (~5% chance: e.g. 19 pouches)
            # This demonstrates real-time alert triggering on the operator dashboard
            if crate_seq % 18 == 0:
                pouches = 19   # Underfilled crate
            elif crate_seq % 43 == 0:
                pouches = 18   # Severely underfilled crate
            else:
                pouches = 20   # Normal full crate

            process_new_crate(cur_var, pouches)

            # Sleep according to crates_per_minute (24 crates/min = 2.5s per crate)
            delay = 60.0 / max(1.0, crates_per_minute)
            time.sleep(delay)
        else:
            time.sleep(0.2)


# Start background conveyor worker thread
conveyor_thread = threading.Thread(target=conveyor_worker_loop, daemon=True)
conveyor_thread.start()


# ==============================================================================
# FLASK HTTP & STREAMING ROUTES
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
        time.sleep(0.04)  # ~25 FPS stream refresh


@app.route('/video_feed')
def video_feed():
    return Response(
        generate_mjpeg_stream(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/api/stats')
def get_stats():
    """Returns current real-time metrics and system state."""
    with state_lock:
        res = latest_crate_result
        history = list(incident_history)

        shift = {
            "total_crates": counter_engine.shift_total_crates,
            "passed_crates": counter_engine.shift_passed_crates,
            "failed_crates": counter_engine.shift_failed_crates,
            "accuracy_pct": round(
                (counter_engine.shift_passed_crates / counter_engine.shift_total_crates * 100.0)
                if counter_engine.shift_total_crates > 0 else 100.0, 1
            ),
            "total_pouches": sum(counter_engine.shift_variant_counts.values()),
            "variant_totals": {
                "orange": counter_engine.shift_variant_counts[PouchVariant.ORANGE],
                "violet": counter_engine.shift_variant_counts[PouchVariant.VIOLET],
                "green": counter_engine.shift_variant_counts[PouchVariant.GREEN],
            }
        }

        latest_data = None
        if res is not None:
            latest_data = {
                "crate_id": res.crate_id,
                "timestamp": datetime.fromtimestamp(res.timestamp).strftime('%H:%M:%S'),
                "total_pouches": res.total_pouches,
                "expected_count": res.expected_count,
                "status": res.status.value,
                "is_passed": (res.status == CrateStatus.PASSED),
                "variant": res.dominant_variant.value,
                "variant_confidence": round(res.variant_confidence * 100.0, 1),
                "latency_ms": round(res.latency_ms, 1)
            }

        return jsonify({
            "conveyor_running": conveyor_running,
            "crates_per_minute": crates_per_minute,
            "auto_cycle_variant": auto_cycle_variant,
            "active_variant": active_variant.value,
            "latest_crate": latest_data,
            "shift_stats": shift,
            "recent_incidents": history[:10]
        })


@app.route('/api/trigger_crate', methods=['POST'])
def trigger_crate():
    """Manually triggers a crate with custom variant or count."""
    data = request.json or {}
    var_str = data.get("variant", "orange").lower()
    count = int(data.get("count", 20))

    if "violet" in var_str:
        var = PouchVariant.VIOLET
    elif "green" in var_str:
        var = PouchVariant.GREEN
    else:
        var = PouchVariant.ORANGE

    res = process_new_crate(var, count)
    return jsonify({
        "status": "success",
        "crate_id": res.crate_id,
        "count": res.total_pouches,
        "verdict": res.status.value
    })


@app.route('/api/toggle_conveyor', methods=['POST'])
def toggle_conveyor():
    global conveyor_running
    conveyor_running = not conveyor_running
    return jsonify({"conveyor_running": conveyor_running})


@app.route('/api/set_speed', methods=['POST'])
def set_speed():
    global crates_per_minute
    data = request.json or {}
    crates_per_minute = float(data.get("speed", 24.0))
    crates_per_minute = max(5.0, min(60.0, crates_per_minute))
    return jsonify({"crates_per_minute": crates_per_minute})


@app.route('/api/set_variant', methods=['POST'])
def set_variant():
    global active_variant, auto_cycle_variant
    data = request.json or {}
    var_str = data.get("variant", "auto").lower()

    if var_str == "auto":
        auto_cycle_variant = True
    elif "violet" in var_str:
        auto_cycle_variant = False
        active_variant = PouchVariant.VIOLET
    elif "green" in var_str:
        auto_cycle_variant = False
        active_variant = PouchVariant.GREEN
    else:
        auto_cycle_variant = False
        active_variant = PouchVariant.ORANGE

    return jsonify({
        "auto_cycle": auto_cycle_variant,
        "active_variant": active_variant.value
    })


@app.route('/api/reset_shift', methods=['POST'])
def reset_shift():
    with state_lock:
        counter_engine.shift_total_crates = 0
        counter_engine.shift_passed_crates = 0
        counter_engine.shift_failed_crates = 0
        counter_engine.shift_variant_counts = {
            PouchVariant.ORANGE: 0,
            PouchVariant.VIOLET: 0,
            PouchVariant.GREEN: 0
        }
        incident_history.clear()
        audit_snapshots.clear()
    return jsonify({"status": "shift_reset"})


@app.route('/api/snapshot/<crate_id>')
def get_snapshot(crate_id):
    """Returns stored JPEG audit snapshot of a specific crate."""
    with state_lock:
        img_bytes = audit_snapshots.get(crate_id)

    if img_bytes:
        return Response(img_bytes, mimetype='image/jpeg')
    return "Snapshot not found", 404


@app.route('/api/export_csv')
def export_csv():
    """Generates and downloads audit CSV report for Milma shift."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Milma Kottayam Dairy - Conveyor Inspection Shift Report",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "Solution: Goose Industrial Solutions"
    ])
    writer.writerow([])
    writer.writerow(["Crate ID", "Time", "Variant", "Detected Count", "Expected Count", "Discrepancy", "Verdict", "Latency (ms)"])

    with state_lock:
        for inc in incident_history:
            writer.writerow([
                inc["crate_id"],
                inc["timestamp"],
                inc["variant"],
                inc["detected_count"],
                inc["expected_count"],
                inc["discrepancy"],
                inc["status"],
                inc["latency_ms"]
            ])

    output.seek(0)
    filename = f"Milma_Shift_Audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5050))
    print(f"\n🚀 Starting Milma Kottayam Operator Dashboard on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
