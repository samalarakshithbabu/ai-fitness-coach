"""
prepare_dataset.py
------------------
Scans the dataset/ folder, unifies all exercise sub-datasets into a single
YOLO-compatible structure under dataset_unified/, and writes class-id remapped
label files so YOLOv8 can train on all exercises at once.

Exercise → class_id mapping:
  0  deadlift
  1  lateral_raise
  2  squat
  3  front_squat
  4  zercher_squat
  5  person   (fallback for any unlabelled class)
"""

import os
import shutil
import random
from pathlib import Path

# ── dataset source definitions ──────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent / "dataset"

SOURCES = [
    # (class_id, image_dir, label_dir, split)

    # Deadlifts  – uses image/Train + label/Train layout
    (0, BASE / "Deadlifts/deadlift Data29/image/Train",
        BASE / "Deadlifts/deadlift Data29/label/Train", "train"),
    (0, BASE / "Deadlifts/deadlift Data29/image/Val",
        BASE / "Deadlifts/deadlift Data29/label/Val",   "val"),

    # Lateral raise (shoulders)
    (1, BASE / "shoulders/lateral data29/images/train",
        BASE / "shoulders/lateral data29/labels/train", "train"),
    (1, BASE / "shoulders/lateral data29/images/val",
        BASE / "shoulders/lateral data29/labels/val",   "val"),

    # Squats
    (2, BASE / "Squats/squats data29/images/train",
        BASE / "Squats/squats data29/labels/train", "train"),
    (2, BASE / "Squats/squats data29/images/val",
        BASE / "Squats/squats data29/labels/val",   "val"),

    # Front squat
    (3, BASE / "Squats/front_squat data29/images/train",
        BASE / "Squats/front_squat data29/labels/train", "train"),
    (3, BASE / "Squats/front_squat data29/images/val",
        BASE / "Squats/front_squat data29/labels/val",   "val"),

    # Zercher squat
    (4, BASE / "Squats/zercher Data29/images/train",
        BASE / "Squats/zercher Data29/labels/train", "train"),
    (4, BASE / "Squats/zercher Data29/images/val",
        BASE / "Squats/zercher Data29/labels/val",   "val"),

    # Romanian deadlift
    (5, BASE / "Deadlifts/romania Data29/images/train",
        BASE / "Deadlifts/romania Data29/labels/train", "train"),
    (5, BASE / "Deadlifts/romania Data29/images/val",
        BASE / "Deadlifts/romania Data29/labels/val",   "val"),

    # Sumo deadlift
    (6, BASE / "Deadlifts/sumo data 29/images/train",
        BASE / "Deadlifts/sumo data 29/labels/train", "train"),
    (6, BASE / "Deadlifts/sumo data 29/images/val",
        BASE / "Deadlifts/sumo data 29/labels/val",   "val"),
]

OUT = Path(__file__).resolve().parent.parent / "dataset_unified"


def remap_label(src_label: Path, dst_label: Path, class_id: int):
    """Copy label file, replacing the first token (class id) on every line."""
    dst_label.parent.mkdir(parents=True, exist_ok=True)
    lines = src_label.read_text().strip().splitlines()
    remapped = []
    for line in lines:
        parts = line.split()
        if parts:
            parts[0] = str(class_id)
            remapped.append(" ".join(parts))
    dst_label.write_text("\n".join(remapped) + "\n")


def prepare():
    print("Preparing unified dataset …")
    counts = {"train": 0, "val": 0}

    for class_id, img_dir, lbl_dir, split in SOURCES:
        if not img_dir.exists():
            print(f"  [SKIP] {img_dir} not found")
            continue

        img_out = OUT / "images" / split
        lbl_out = OUT / "labels" / split
        img_out.mkdir(parents=True, exist_ok=True)
        lbl_out.mkdir(parents=True, exist_ok=True)

        images = list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.png"))
        for img_path in images:
            stem = img_path.stem
            # build a unique name to avoid collisions across classes
            unique_stem = f"cls{class_id}_{stem}"

            # copy image
            dst_img = img_out / (unique_stem + img_path.suffix)
            shutil.copy2(img_path, dst_img)

            # remap + copy label
            src_lbl = lbl_dir / (stem + ".txt")
            if src_lbl.exists():
                remap_label(src_lbl, lbl_out / (unique_stem + ".txt"), class_id)
            else:
                # create empty label if missing
                (lbl_out / (unique_stem + ".txt")).write_text("")

            counts[split] += 1

    print(f"  train images: {counts['train']}")
    print(f"  val   images: {counts['val']}")
    print(f"  Output: {OUT}")
    print("Done.")


if __name__ == "__main__":
    prepare()
