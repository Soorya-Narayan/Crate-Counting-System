# Milma Kottayam Dairy — 50-Epoch YOLOv8s Training Performance Graphs

This directory contains the verified training performance curves, confusion matrices, and validation visual predictions for the **YOLOv8s** milk pouch and crate detection model trained on the master consolidated dataset.

---

## 1. Multi-Epoch Training Loss & Metric Curves
![Training Results & Loss Curves](results.png)

- **Total Epochs:** 50 Epochs (AdamW with Cosine Learning Rate Schedule)
- **Final Test mAP50:** **98.25%**
- **Final Test mAP50-95:** **80.51%** (BBox precision jump)
- **Precision / Recall:** **95.9% / 95.8%**

---

## 2. Classification Confusion Matrix (Normalized)
![Normalized Confusion Matrix](confusion_matrix_normalized.png)

### Class Accuracies:
| Class | Precision | Recall | mAP50 | mAP50-95 | Status |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`empty_tray`** | **97.4%** | **100.0%** | **99.5%** | **92.2%** | Zero false negatives |
| **`pouch_purple`** | **99.3%** | **98.5%** | **99.4%** | **86.4%** | High resolution separation |
| **`pouch_orange`** | **95.3%** | **95.2%** | **98.2%** | **77.8%** | Robust under reflections |
| **`pouch_green`** | **90.8%** | **96.9%** | **97.5%** | **73.4%** | Accurate under dense packs |
| **`crate`** | **96.8%** | **88.5%** | **96.7%** | **72.8%** | Outer rim localization |

---

## 3. F1-Confidence & Precision-Recall Curves
| F1 vs. Confidence Curve | Precision vs. Recall Curve |
| :---: | :---: |
| ![F1 Curve](BoxF1_curve.png) | ![PR Curve](BoxPR_curve.png) |

- **Optimal Confidence Threshold:** **`conf = 0.42`** (Peak F1 score = 0.96).

---

## 4. Visual Validation Detections
![Sample Validation Detections](val_batch0_pred.jpg)
Model detections on test validation batch containing dense 18/19 packet trays with class tags and confidence percentages.
