# Milma Kottayam - Crate & Pouch Counting System
An automated vision-based AI system for detecting, segmenting, and counting milk pouches inside moving crates on a conveyor line with variant classification and shift-level reconciliation, developed for implementation at **Milma (E.R.C.M.P.U. Ltd.), Kottayam Dairy Plant**.

Developed by **Goose Industrial Solutions**.

---

## Key Features

- **Deep Learning Instance Segmentation (YOLOv8 / YOLOv11):** Isolates individual 500 ml pillow pouches packed in overlapping / shingled configurations (2 lanes of ~10 packets each).
- **Multi-Spectral Variant Segregation:** Distinguishes between **Orange** (Rich Milk), **Violet** (Toned Milk), and **Green** (Smart Milk) pouches using masked ink chromaticity and crate-level consensus voting.
- **Pouch Count Verification:** Audits total detected pouches against the nominal target (**20 pouches/crate**). Flags underfilled, overfilled, or misaligned crates immediately.
- **High-Speed Real-Time Inference:** Sub-35ms processing latency per crate (>28 FPS) on standard hardware, comfortably exceeding the 24 crates/min conveyor line speed.
- **Auditable HUD Visualization:** Renders color-coded translucent segmentation overlays, centroid index markers (`#1` to `#20`), status badges, and cumulative shift statistics.
- **Flexible Ingestion:** Supports live Baumer GigE cameras (`neoapi`), standard USB/RTSP streams, static images, recorded video files, and built-in synthetic benchmark generation.

---

## System Requirements

- Python 3.9+
- Dependencies:
  ```bash
  pip install -r requirements.txt
  ```

---

## Quickstart & Usage

### 1. Run Automated Demo & Self-Test Suite
Executes the counting and variant classification engine across multiple synthetic crate scenarios (normal 20-packet crates and underfill anomalies) and saves annotated outputs:
```bash
python milma_counter.py --demo
```

### 2. Process a Static Crate Image
```bash
python milma_counter.py --image path/to/crate.jpg --output annotated_crate.jpg
```

### 3. Process a Video Stream
```bash
python milma_counter.py --video path/to/conveyor_run.mp4
```

### 4. Run with Custom Trained YOLO Weights
```bash
python milma_counter.py --image path/to/crate.jpg --model weights/milma_pouch_seg.pt
```

---

## Command Line Arguments

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--image` | string | `None` | Path to single input image |
| `--video` | string | `None` | Path to video file or RTSP stream |
| `--model` | string | `None` | Path to custom trained YOLO segmentation weights (`.pt`) |
| `--expected` | integer | `20` | Nominal pouch count per crate |
| `--output` | string | `milma_counted_output.jpg` | Destination filename for annotated image |
| `--demo` | flag | `False` | Run self-test suite across Orange, Violet, and Green variants |

---

## Project Documentation
- **Technical Implementation Plan:** [Milma_Kottayam_Vision_Counting_Implementation_Plan.md](Milma_Kottayam_Vision_Counting_Implementation_Plan.md)
- **Executive Word Proposal:** `Milma_Kottayam_Vision_Counting_Implementation_Plan.docx`
- **Printable PDF Document:** `Milma_Kottayam_Vision_Counting_Implementation_Plan.pdf`
