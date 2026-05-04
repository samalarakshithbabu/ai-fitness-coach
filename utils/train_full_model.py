"""
train_full_model.py
-------------------
Trains YOLOv8n-pose on the full 25-class fitness dataset.
Run AFTER prepare_full_dataset.py.

Usage:
    python utils/train_full_model.py
"""

from pathlib import Path
from ultralytics import YOLO

YAML   = Path(__file__).resolve().parent.parent / "models" / "fitness_full.yaml"
EPOCHS = 50
IMGSZ  = 640
BATCH  = 8
DEVICE = "cpu"   # change to 0 for GPU


def train():
    if not YAML.exists():
        print(f"[ERROR] {YAML} not found.")
        print("        Run: python utils/prepare_full_dataset.py first")
        return

    print("Loading YOLOv8n-pose base weights...")
    model = YOLO("yolov8n-pose.pt")

    print(f"Training on {YAML} — {EPOCHS} epochs, imgsz={IMGSZ}, batch={BATCH}...")
    model.train(
        data=str(YAML),
        epochs=EPOCHS,
        imgsz=IMGSZ,
        batch=BATCH,
        device=DEVICE,
        project="models",
        name="fitness_pose_full",
        exist_ok=True,
        verbose=True,
    )

    best = Path("models/fitness_pose_full/weights/best.pt")
    print(f"\nTraining complete. Best weights: {best}")
    return str(best)


if __name__ == "__main__":
    train()
