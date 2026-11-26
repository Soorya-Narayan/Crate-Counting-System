# Hailo-8L Compilation Guide for Milma Crate & Pouch Detection

This document provides step-by-step instructions for converting `milma_best.onnx` into the hardware-accelerated `milma_best.hef` (Hailo Executable Format) binary for the **Raspberry Pi 5 + Raspberry Pi AI Kit (Hailo-8L, 13 TOPS)**.

---

## 1. Model Specifications

- **Input Node Name:** `images`
- **Input Shape:** `[1, 3, 640, 640]` (Fixed BCHW tensor, Float32)
- **Output Node Name:** `output0`
- **Output Shape:** `[1, 9, 8400]` (8400 anchor candidates: 4 box coords + 5 class scores)
- **Classes (5):**
  - `0`: `crate`
  - `1`: `empty_tray`
  - `2`: `pouch_green`
  - `3`: `pouch_orange`
  - `4`: `pouch_purple`

---

## 2. Compilation Environment

The **Hailo Dataflow Compiler (DFC)** runs inside an x86_64 or Linux environment (Ubuntu 22.04 / 20.04) or via the official Hailo Docker container.

### Option A: Using the Hailo Software Suite Docker (Recommended)
Download and run the official container:
```bash
docker run -it --rm -v $(pwd):/workspace -w /workspace hailo-software-suite:latest
```

### Option B: Local Virtualenv (x86_64 Ubuntu)
```bash
python3.10 -m venv hailo_env
source hailo_env/bin/activate
pip install hailo_dataflow_compiler-3.28.0-py3-none-linux_x86_64.whl
```

---

## 3. Step-by-Step Conversion Flow

### Step 1: Parse the ONNX Model
Create the Hailo internal HAR (Hailo Archive):
```bash
hailo parser onnx milma_best.onnx \
    --hw-arch hailo8l \
    --start-node-names images \
    --end-node-names output0 \
    --har-path milma_best.har
```

### Step 2: Model Optimization & Quantization (HAR -> Quantized HAR)
Create an alls script `milma_yolov8.alls`:
```text
normalization1 = normalization([0.0, 0.0, 0.0], [255.0, 255.0, 255.0])
change_output_activation(conv42, sigmoid)
change_output_activation(conv53, sigmoid)
change_output_activation(conv63, sigmoid)
```

Run Hailo Optimization with a calibration dataset (use 64-128 images from `dataset/train`):
```bash
hailo optimize \
    --har milma_best.har \
    --hw-arch hailo8l \
    --calib-set-path ./master_yolo_dataset/images/train \
    --model-script milma_yolov8.alls \
    --results-har-path milma_best_quantized.har
```

### Step 3: Compile to HEF Binary
```bash
hailo compiler \
    --har milma_best_quantized.har \
    --hw-arch hailo8l \
    --results-hef-path milma_best.hef
```

---

## 4. Deploying on Raspberry Pi 5

Copy `milma_best.hef` to the Raspberry Pi:
```bash
scp milma_best.hef pi@<pi-ip>:~/Crate-Counting-System/
```

On the Raspberry Pi 5:
```bash
sudo apt update
sudo apt install hailo-all
```

Test hardware detection:
```bash
hailortcli fw-control identify
```
You should see:
```text
Device: Hailo-8L
Architecture: HAILO8L
```

Run inference test via Python:
```python
from hailo_platform import VDevice, InferModel

vdevice = VDevice()
infer_model = vdevice.create_infer_model("milma_best.hef")
# Offloads 100% of YOLO computation to the 13 TOPS Hailo NPU!
```
