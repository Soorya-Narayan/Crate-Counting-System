"""
Milma Kottayam Dairy - YOLO Model Training & Evaluation Pipeline
=================================================================
Automated training script for custom Milk Pouch & Crate detection model.
Uses master_yolo_dataset/data.yaml (1,496 images, 18,192 labeled objects).

Author: Goose Industrial Solutions
Client: Milma (E.R.C.M.P.U. Ltd.), Kottayam Dairy Plant
"""

import os
import sys
import time
import argparse
from datetime import datetime
from ultralytics import YOLO
import torch

def get_best_device():
    """Detects Apple Silicon (MPS), NVIDIA CUDA, or CPU."""
    if torch.cuda.is_available():
        return "0"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"

def create_epoch_callback(total_epochs):
    """Creates a custom callback for live per-epoch console updates."""
    def on_fit_epoch_end(trainer):
        try:
            curr_epoch = getattr(trainer, "epoch", 0) + 1
            metrics = getattr(trainer, "metrics", {}) or {}
            
            p = metrics.get("metrics/precision(B)", 0.0)
            r = metrics.get("metrics/recall(B)", 0.0)
            m50 = metrics.get("metrics/mAP50(B)", 0.0)
            m50_95 = metrics.get("metrics/mAP50-95(B)", 0.0)
            
            # Extract loss values if available
            loss_info = ""
            if hasattr(trainer, "loss_items") and trainer.loss_items is not None:
                try:
                    losses = [f"{float(v):.4f}" for v in trainer.loss_items]
                    loss_info = f"Loss [box/cls/dfl]: {' / '.join(losses)}"
                except Exception:
                    pass

            bar_len = 30
            filled = int(bar_len * curr_epoch / total_epochs)
            progress_bar = "█" * filled + "░" * (bar_len - filled)

            now_str = datetime.now().strftime("%H:%M:%S")
            print(f"\n{'='*75}", flush=True)
            print(f"[{now_str}] 🚀 EPOCH {curr_epoch:02d}/{total_epochs:02d} COMPLETED  |  [{progress_bar}] {int(curr_epoch/total_epochs*100)}%", flush=True)
            print(f"  • mAP50        : {m50 * 100:.2f}%", flush=True)
            print(f"  • mAP50-95     : {m50_95 * 100:.2f}%", flush=True)
            print(f"  • Precision    : {p * 100:.2f}%", flush=True)
            print(f"  • Recall       : {r * 100:.2f}%", flush=True)
            if loss_info:
                print(f"  • {loss_info}", flush=True)
            print(f"{'='*75}\n", flush=True)
        except Exception as e:
            print(f"[Callback Warning] Could not parse epoch stats: {e}", flush=True)

    return on_fit_epoch_end

def train(epochs=50, imgsz=640, batch=16, model_type="yolov8s.pt", device=None):
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    data_yaml = os.path.join(workspace_dir, "master_yolo_dataset", "data.yaml")
    
    if not os.path.exists(data_yaml):
        print(f"Error: Dataset configuration not found at {data_yaml}")
        sys.exit(1)
        
    chosen_device = device if device else get_best_device()
    print("=" * 75)
    print(" MILMA KOTTAYAM - PRODUCTION 50-EPOCH TRAINING PIPELINE")
    print("=" * 75)
    print(f" Dataset YAML   : {data_yaml}")
    print(f" Base Weights   : {model_type} (Small Architecture - 11.2M params)")
    print(f" Hardware Device: {chosen_device} (Apple Silicon Metal GPU Acceleration)")
    print(f" Target Epochs  : {epochs}")
    print(f" Image Size     : {imgsz}x{imgsz}")
    print(f" Batch Size     : {batch}")
    print(f" Cosine LR      : True (cos_lr)")
    print(f" Mosaic Augment : Enabled (close_mosaic in final 10 epochs)")
    print("=" * 75)
    
    # Initialize YOLO model
    model = YOLO(model_type)
    
    # Register per-epoch real-time feedback callback
    model.add_callback("on_fit_epoch_end", create_epoch_callback(epochs))
    
    # Train
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=chosen_device,
        project=os.path.join(workspace_dir, "runs", "milma_train"),
        name="milma_pouch_detector",
        save=True,
        patience=20,
        workers=4,
        exist_ok=True,
        pretrained=True,
        plots=True,
        cos_lr=True,
        close_mosaic=10,
        # Industrial augmentations tailored for Milma conveyor crates
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=10.0,
        translate=0.1,
        scale=0.5,
        fliplr=0.5,
        flipud=0.5,
        mosaic=1.0
    )
    
    print("\n" + "=" * 75)
    print(" 50-EPOCH TRAINING COMPLETED SUCCESSFULLY!")
    print("=" * 75)
    
    # Run evaluation on held-out test split (236 images)
    print("\nRunning benchmark evaluation on held-out test split (236 images)...")
    val_metrics = model.val(data=data_yaml, split="test", imgsz=imgsz, device=chosen_device)
    print(f"• Final Test mAP50    : {val_metrics.box.map50 * 100:.2f}%")
    print(f"• Final Test mAP50-95 : {val_metrics.box.map * 100:.2f}%")
    
    best_weights = os.path.join(workspace_dir, "runs", "milma_train", "milma_pouch_detector", "weights", "best.pt")
    if os.path.exists(best_weights):
        target_pt = os.path.join(workspace_dir, "milma_best.pt")
        import shutil
        shutil.copy2(best_weights, target_pt)
        print(f"\n✓ Upgraded model weights written to: {target_pt}")
        print("✓ System ready for live counting and dashboard deployment.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train custom Milma Pouch & Crate YOLO Model")
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs (default: 50)")
    parser.add_argument("--imgsz", type=int, default=640, help="Image resolution size (default: 640)")
    parser.add_argument("--batch", type=int, default=16, help="Batch size (default: 16)")
    parser.add_argument("--model", type=str, default="yolov8s.pt", help="Base model architecture (default: yolov8s.pt)")
    parser.add_argument("--device", type=str, default="", help="Device: mps, cuda, 0, cpu (default: auto)")
    
    args = parser.parse_args()
    train(epochs=args.epochs, imgsz=args.imgsz, batch=args.batch, model_type=args.model, device=args.device if args.device else None)
