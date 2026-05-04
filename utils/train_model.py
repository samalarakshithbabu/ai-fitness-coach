"""
train_model.py
--------------
Trains YOLOv8-pose on the unified fitness dataset.
Run AFTER prepare_dataset.py.

Usage:
    python utils/train_model.py
"""

from pathlib import Path
import torch
from ultralytics import YOLO
from ultralytics.nn.tasks import PoseModel

# Fix for PyTorch 2.6+ weights_only default change
torch.serialization.add_safe_globals([PoseModel])


YAML   = Path(__file__).resolve().parent.parent / "models" / "fitness.yaml"
EPOCHS = 50
IMGSZ  = 640
BATCH  = 8
DEVICE = "cpu"   # change to 0 for GPU


def train():
    print("Loading YOLOv8n-pose base weights …")
    model = YOLO("yolov8n-pose.pt")   # downloads ~6 MB pretrained weights

    print(f"Training on {YAML} …")
    results = model.train(
        data=str(YAML),
        epochs=EPOCHS,
        imgsz=IMGSZ,
        batch=BATCH,
        device=DEVICE,
        project="models",
        name="fitness_pose",
        exist_ok=True,
        verbose=True,
    )

    best = Path("models/fitness_pose/weights/best.pt")
    print(f"\nTraining complete. Best weights saved to: {best}")
    return str(best)


if __name__ == "__main__":
    train()
