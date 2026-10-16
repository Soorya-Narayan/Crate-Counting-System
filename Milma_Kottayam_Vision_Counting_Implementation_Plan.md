# Automated Vision-Based Milk Pouch & Crate Counting System
## Technical Implementation Plan & Data Requirement Specification

**Client:** Milma (E.R.C.M.P.U. Ltd.), Kottayam Dairy Plant  
**Prepared by:** Goose Industrial Solutions (Vision AI & Automation Solutions)  
**Date:** October 2026  
**Reference:** Review of Milma Kottayam Site Survey Report & Follow-up Response  

---

## 1. Executive Summary & Project Overview

Following the site survey conducted at **Milma (E.R.C.M.P.U. Ltd.) Kottayam Dairy**, Goose Industrial Solutions has formulated this detailed **Technical Implementation Plan and Data Requirement Specification**.

The objective of this engagement is to deploy a high-speed, non-intrusive, **Vision-Based Milk Pouch & Crate Counting System** on the active crate conveyor line. The system replaces error-prone manual tallies with real-time deep learning instance segmentation, providing **100% auditable production figures** segregated across milk packet variants.

### Key Project Parameters

| Metric / Parameter | Value / Specification |
| :--- | :--- |
| **Target Facility** | Milma (E.R.C.M.P.U. Ltd.), Kottayam Dairy Plant |
| **Primary Goal** | Real-time automated packet counting per crate & shift total segregated by variant |
| **Line Speed & Throughput** | 24 crates/min (~280–480 pouches/min) \| Stated daily throughput ~1.5 Lakh pouches/day |
| **Product Variants** | 500 ml LDPE pillow pouches (**Orange, Violet, Green**) in blue plastic crates (nominal 20 pouches/crate) |
| **Technology Stack** | Global Shutter Vision Camera + Polarized LED Lighting + YOLO Edge AI Inference |
| **Primary Deliverable** | Turnkey vision rig, live shopfloor HMI dashboard, tamper-proof tally records & ERP export |

---

## 2. Synthesis of Site Survey Findings & Engineering Mitigations

Our engineering design directly addresses the physical and optical characteristics noted in Milma's survey report:

| Survey Parameter | Observed Site Condition | Goose Engineering Solution |
| :--- | :--- | :--- |
| **Dim Lighting & Specular Glare** | Overhead dim fluorescent tubes; polished stainless steel guards and wet glossy film create strong specular glare. | High-intensity **polarized industrial LED bar lights** with **cross-polarizing optical lens filter** to eliminate surface glare entirely. |
| **Crate Spacing & Motion** | Crates travel abutting with zero inter-crate gap at ~24 crates/min; manual lift-off causes variable dwell time. | Continuous **optical edge tracking** combined with a photoelectric trigger sensor to delineate crate entry, boundaries, and exit. |
| **Pouch Packing Arrangement** | Packets lie flat and shingled (overlapping in 2 runs, ~20 per crate) with protruding fin seals. | **Deep learning instance segmentation (YOLOv8/v11)** trained specifically to isolate overlapping boundaries and fin-seal geometries. |
| **Washdown Dairy Environment** | Wet washdown dairy processing area with humidity and daily cleaning cycles. | **IP65/IP67 food-grade stainless steel/anodized sealed enclosure** for camera, lens, and lighting; moisture-proof industrial connectors. |
| **Physical Clearance** | Conveyor height: 900 mm; belt width: 450 mm; max overhead clearance to structure: ~950 mm. | Compact custom **overhead C-frame bracket** with 8mm/12mm lens tailored for short working distance (WD ~700 mm). |

---

## 3. Requirements from Milma Kottayam for Model Development

To achieve **maximum counting accuracy (target ≥ 99.5%)** under dynamic plant conditions, Goose Industrial Solutions requires specific dataset assets and site provisions from Milma Kottayam.

### 3.1 Machine Learning Dataset & Photography Requirements

Because milk pouches are pliable, glossy, and packed in overlapping layers, the machine learning model must be trained on authentic visual conditions from the Kottayam plant floor.

#### Image & Video Volume Breakdown

| Pouch Variant / Condition | Recommended Quantity | Visual Variations to Include |
| :--- | :--- | :--- |
| **Orange Variant (Standard)** | **600 – 800 Photos** | Normal shingled runs (nominal 20 pouches/crate), varying overlap depths, fin-seal orientation, dry vs. wet pouches. |
| **Violet Variant (Standard)** | **600 – 800 Photos** | Standard packing layouts, different print alignment on film, partial overlaps, full crates on moving conveyor. |
| **Green Variant (Standard)** | **600 – 800 Photos** | Standard packing runs, pouch settling variations, slight crate skewing on outer frame. |
| **Anomalies & Edge Cases** | **350 – 500 Photos** | Underfilled crates (16, 17, 18, 19 packets), overfilled/tilted pouches, folded/creased pouches, empty crates, worn crates. |
| **High-Speed Video Footages** | **20 – 30 Minutes Total** | Continuous top-down videos (1080p @ 30/60 fps) across morning shift (07:30 start) and mid-shift capturing natural crate flow. |

> **Dataset Summary:** Approximately **2,100 to 2,900 still photographs** + **25 minutes of continuous video**.  
> *Note: Photos can be captured using standard high-resolution smartphones or DSLRs following the protocol below, or by Goose engineers during a 1-day dedicated staging visit.*

---

### 3.2 Photography Capture Protocol & Guidelines

1. **Camera Perspective & Angle:**
   - Capture directly from above (**perpendicular 90° nadir angle**), looking straight down into the crate. This simulates the fixed industrial camera view.
   - Include slight angular variations (±5° to ±10°) to train robustness against crate rocking on the chain conveyor.
2. **Camera Distance & Framing:**
   - Position the camera approximately **700 mm to 900 mm** above the conveyor belt so the entire crate (565 mm × 300 mm) plus a small border is fully visible.
3. **Image Sharpness & Motion:**
   - Maintain crisp focus on the pouch body and fin seals.
   - If the conveyor is moving, use a fast shutter speed (minimum 1/250s) to eliminate motion blur.
4. **Lighting & Moisture Diversity:**
   - Capture samples under existing tube lighting, during morning shift start (07:30), mid-shift, and with wet pouch surfaces.
5. **Folder Segregation:**
   - Organize files into clearly labelled folders: `/Orange/`, `/Violet/`, `/Green/`, and `/Edge_Cases/` (with approximate counts noted for validation).

---

### 3.3 Site Infrastructure Provisions Needed from Milma

* **Regulated Electrical Power:** One single-phase 230V AC (50 Hz) UPS-backed power socket (~500W load) within 3 meters of the inspection station.
* **Network Connectivity:** One Gigabit Ethernet (RJ45) drop or stable plant Wi-Fi access near the line for edge system dashboard access and automated data backup.
* **Overhead Mechanical Mount:** Permission and support to mount an overhead rigid C-arm bracket (850–950 mm above conveyor) before the wall hatch / manual offload point.
* **Plant Coordination:** Nomination of an on-site technical point of contact (Production/Maintenance) to facilitate line access during calibration and UAT.

---

## 4. Proposed Vision AI System Architecture

The proposed system is an **edge-native industrial vision station**. All neural network inference executes locally on dedicated edge hardware without reliance on external cloud connections, ensuring high throughput (<100 ms per crate) and zero downtime.

### Hardware & Software Stack

| Subsystem Component | Proposed Specification | Functional Role in Kottayam Plant |
| :--- | :--- | :--- |
| **Industrial Vision Camera** | 3.2 MP – 5.0 MP Global Shutter CMOS (Sony Pregius), GigE Vision, IP67 enclosure | Freezes crate motion at 24 crates/min without blur or rolling distortion. |
| **Optical Lens & Filter** | 8mm / 12mm Low-Distortion C-Mount Lens + Polarizing Optical Filter | Frames full crate at ~750 mm WD and cuts specular reflections from wet LDPE film. |
| **Industrial Lighting** | High-Intensity Polarized LED Diffuse Illuminator (IP67 food-grade housing) | Overpowers dim ambient factory lighting, creating consistent shadow-free illumination. |
| **Edge AI Computing Unit** | Industrial Embedded AI Box (NVIDIA Jetson Orin / RTX Industrial PC, Fanless IP50/65) | Executes deep learning instance segmentation and tracking in < 80 ms per frame. |
| **Operator Dashboard & HMI** | 10.1" / 15.6" Touch Screen HMI + Audio-Visual Stack Light | Displays live packet counts, variant status, shift totals, and triggers instant alerts for underfilled crates. |

### Computer Vision & ML Pipeline

```
[Moving Crate on Conveyor]
         │
         ▼
[Optical / Software Crate Edge Trigger] ──> Initializes unique Crate ID
         │
         ▼
[High-Speed Global Shutter Image Capture with Polarized LED]
         │
         ▼
[Crate Boundary Alignment & ROI Extraction] (Handles abutting crates)
         │
         ▼
[YOLO Instance Segmentation Neural Network] (Isolates overlapping pouches & fin seals)
         │
         ▼
[Variant Classification (Orange / Violet / Green)] (99.8%+ confidence)
         │
         ▼
[Counting & Validation Logic] (Target: 20 pouches/crate)
    ├── If 20: PASSED ──> Increment Shift Tally
    └── If ≠ 20: ALERT ──> Trigger Stack Light & Archive Audit Image
         │
         ▼
[Local Edge Database & Milma ERP / SCADA Integration]
```

---

## 5. Project Implementation Plan & Milestone Roadmap

Goose Industrial Solutions proposes an **8-week structured deployment schedule** designed for zero disruption to daily plant operations:

| Phase | Milestone Focus | Key Deliverables & Action Items | Duration |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **Data Acquisition & Ground Truth Labelling** | Collect 2,000+ photos/videos across Orange, Violet, and Green runs. Image annotation and polygon segmentation tagging. | **Weeks 1 – 2** |
| **Phase 2** | **AI Model Training & Edge Optimization** | Train deep learning segmentation models. Handle overlapping/shingled pouch edges. TensorRT quantization for edge speed. | **Weeks 3 – 4** |
| **Phase 3** | **Hardware Rig Staging & Pre-Commissioning** | Fabricate IP65/IP67 enclosure and mounting bracket. Bench test camera, polarized LED light, and Edge AI unit. | **Weeks 4 – 5** |
| **Phase 4** | **On-Site Installation & Calibration** | Physical installation at Kottayam line. Optical calibration, fine-tuning under live production conveyor (24 crates/min), latency benchmarking. | **Weeks 6 – 7** |
| **Phase 5** | **UAT, Shift Validation & Full Handover** | Continuous testing during Shift 1 (07:30–15:30) over 10,000+ crates. Reconcile against physical count. Operator training & sign-off. | **Weeks 8 – 9** |

---

## 6. Key Performance Indicators (KPIs) & Acceptance Criteria

| Performance Metric | Target SLA / KPI | Measurement Methodology |
| :--- | :--- | :--- |
| **Packet Counting Accuracy** | **≥ 99.5%** | Evaluated over 10,000 continuous crates compared against physical audit counts. |
| **Variant Classification Accuracy** | **≥ 99.8%** | Automatic verification of Orange vs. Violet vs. Green milk crates. |
| **Inference Latency** | **< 100 milliseconds** | Complete processing time per crate; comfortably exceeds 2.5s crate cycle. |
| **Underfill / Anomaly Detection** | **≥ 99.0% Detection** | Immediate trigger of visual/audio stack light and photo archive whenever count != 20. |

---

## 7. Deliverables from Goose Industrial Solutions

1. **Turnkey Vision Rig:** IP65/IP67 sealed industrial camera, polarized LED illumination, custom overhead C-frame bracket, and photoelectric trigger.
2. **Edge AI Unit & Software Engine:** Pre-loaded industrial edge computer with trained YOLO segmentation, tracking algorithms, and database storage.
3. **Operator HMI & Web Dashboard:** Live touch screen display showing instantaneous counts, variant status, shift totals, and discrepancy alarms.
4. **Shift Reconciliation Reports:** Automated daily/shift summaries in PDF/Excel format with optional Milma ERP/SAP integration API.
5. **Documentation & Training:** System Operation Manual, Maintenance SOP, and on-site training sessions for plant operators.

---

## 8. Next Steps & Immediate Action Items

1. **Plan Alignment & Sign-off:** Review and confirm the technical approach and infrastructure checklist with Milma plant engineering.
2. **Dataset Collection Scheduling:** Agree upon dates for the photo/video dataset collection (either compiled by Milma or during a 1-day visit by Goose engineers).
3. **Hardware Staging & Fabrication:** Finalize bracket mounting dimensions on the conveyor frame and initiate Phase 1.

---

**SUBMITTED BY:**  
**Goose Industrial Solutions**  
Vision AI & Automation Solutions  
Email: contact@goosetech.ai | Web: www.goosetech.ai  

**PREPARED FOR:**  
**Milma (E.R.C.M.P.U. Ltd.)**  
Kottayam Dairy Plant  
Kerala Co-operative Milk Marketing Federation  
