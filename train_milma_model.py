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
import argparse
from ultralytics import YOLO
import torch

def get_best_device():
    """Detects Apple Silicon (MPS), NVIDIA CUDA, or CPU."""
    if torch.cuda.is_available():
        return "0"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"

def train(epochs=50, imgsz=640, batch=16, model_type="yolov8n.pt", device=None):
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    data_yaml = os.path.join(workspace_dir, "master_yolo_dataset", "data.yaml")
    
    if not os.path.exists(data_yaml):
        print(f"Error: Dataset configuration not found at {data_yaml}")
        sys.exit(1)
        
    chosen_device = device if device else get_best_device()
    print("=" * 65)
    print(" MILMA KOTTAYAM - YOLO TRAINING PIPELINE")
    print("=" * 65)
    print(f" Dataset YAML: {data_yaml}")
    print(f" Base Weights: {model_type}")
    print(f" Hardware Device: {chosen_device}")
    print(f" Target Epochs:  {epochs}")
    print(f" Image Size:     {imgsz}x{imgsz}")
    print(f" Batch Size:     {batch}")
    print("-" * 65)
    
    # Initialize YOLO model
    model = YOLO(model_type)
    
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
        patience=15,
        workers=4,
        exist_ok=True,
        pretrained=True,
        plots=True,
        # Industrial augmentations tailored for factory lines
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
    
    print("\n" + "=" * 65)
    print(" TRAINING COMPLETED SUCCESSFULLY!")
    print("=" * 65)
    
    # Run evaluation on held-out test split
    print("\nEvaluating on held-out test benchmark split (236 images)...")
    val_metrics = model.val(data=data_yaml, split="test", imgsz=imgsz, device=chosen_device)
    print(f"Test mAP50:    {val_metrics.box.map50:.4f}")
    print(f"Test mAP50-95: {val_metrics.box.map:.4f}")
    
    best_weights = os.path.join(workspace_dir, "runs", "milma_train", "milma_pouch_detector", "weights", "best.pt")
    if os.path.exists(best_weights):
        # Create a convenient symlink / copy in workspace root
        target_pt = os.path.join(workspace_dir, "milma_best.pt")
        import shutil
        shutil.copy2(best_weights, target_pt)
        print(f"\nBest trained weights saved to: {target_pt}")
        print("You can now run milma_counter.py or launch app.py with your new custom weights!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train custom Milma Pouch & Crate YOLO Model")
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs (default: 50)")
    parser.add_argument("--imgsz", type=int, default=640, help="Image resolution size (default: 640)")
    parser.add_argument("--batch", type=int, default=16, help="Batch size (default: 16)")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="Base model architecture (default: yolov8n.pt)")
    parser.add_argument("--device", type=str, default="", help="Device: mps, cuda, 0, cpu (default: auto)")
    
    args = parser.parse_args()
    train(epochs=args.epochs, imgsz=args.imgsz, batch=args.batch, model_type=args.model, device=args.device if args.device else None)
