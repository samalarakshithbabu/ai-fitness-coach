"""
prepare_full_dataset.py
-----------------------
Merges ALL data into dataset_unified_full/:
  1. Original hand-annotated YOLO pose data (7 classes from Deadlifts/Squats/shoulders)
  2. Auto-annotated data from extract_and_annotate.py (18 new classes)

Then writes models/fitness_full.yaml for training.

Usage:
    python utils/prepare_full_dataset.py
"""

import os
import shutil
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT  = ROOT / "dataset_unified_full"

VAL_SPLIT = 0.20   # 20% of each class goes to val

# ── Class map ─────────────────────────────────────────────────────────────────
CLASS_NAMES = {
    0:  "deadlift",
    1:  "lateral_raise",
    2:  "squat",
    3:  "front_squat",
    4:  "zercher_squat",
    5:  "romanian_deadlift",
    6:  "sumo_deadlift",
    7:  "bench_press",
    8:  "incline_bench_press",
    9:  "decline_bench_press",
    10: "barbell_biceps_curl",
    11: "hammer_curl",
    12: "shoulder_press",
    13: "lat_pulldown",
    14: "pull_up",
    15: "push_up",
    16: "leg_extension",
    17: "leg_raises",
    18: "hip_thrust",
    19: "plank",
    20: "tricep_dips",
    21: "tricep_pushdown",
    22: "t_bar_row",
    23: "russian_twist",
    24: "chest_fly_machine",
}

# ── Original annotated sources (class_id, img_dir, lbl_dir, split) ───────────
ORIGINAL_SOURCES = [
    (0, ROOT/"dataset/Deadlifts/deadlift Data29/image/Train",
        ROOT/"dataset/Deadlifts/deadlift Data29/label/Train", "train"),
    (0, ROOT/"dataset/Deadlifts/deadlift Data29/image/Val",
        ROOT/"dataset/Deadlifts/deadlift Data29/label/Val",   "val"),
    (1, ROOT/"dataset/shoulders/lateral data29/images/train",
        ROOT/"dataset/shoulders/lateral data29/labels/train", "train"),
    (1, ROOT/"dataset/shoulders/lateral data29/images/val",
        ROOT/"dataset/shoulders/lateral data29/labels/val",   "val"),
    (2, ROOT/"dataset/Squats/squats data29/images/train",
        ROOT/"dataset/Squats/squats data29/labels/train",     "train"),
    (2, ROOT/"dataset/Squats/squats data29/images/val",
        ROOT/"dataset/Squats/squats data29/labels/val",       "val"),
    (3, ROOT/"dataset/Squats/front_squat data29/images/train",
        ROOT/"dataset/Squats/front_squat data29/labels/train","train"),
    (3, ROOT/"dataset/Squats/front_squat data29/images/val",
        ROOT/"dataset/Squats/front_squat data29/labels/val",  "val"),
    (4, ROOT/"dataset/Squats/zercher Data29/images/train",
        ROOT/"dataset/Squats/zercher Data29/labels/train",    "train"),
    (4, ROOT/"dataset/Squats/zercher Data29/images/val",
        ROOT/"dataset/Squats/zercher Data29/labels/val",      "val"),
    (5, ROOT/"dataset/Deadlifts/romania Data29/images/train",
        ROOT/"dataset/Deadlifts/romania Data29/labels/train", "train"),
    (5, ROOT/"dataset/Deadlifts/romania Data29/images/val",
        ROOT/"dataset/Deadlifts/romania Data29/labels/val",   "val"),
    (6, ROOT/"dataset/Deadlifts/sumo data 29/images/train",
        ROOT/"dataset/Deadlifts/sumo data 29/labels/train",   "train"),
    (6, ROOT/"dataset/Deadlifts/sumo data 29/images/val",
        ROOT/"dataset/Deadlifts/sumo data 29/labels/val",     "val"),
]


def remap_label(src: Path, dst: Path, class_id: int):
    dst.parent.mkdir(parents=True, exist_ok=True)
    lines = src.read_text().strip().splitlines()
    remapped = []
    for line in lines:
        parts = line.split()
        if parts:
            parts[0] = str(class_id)
            remapped.append(" ".join(parts))
    dst.write_text("\n".join(remapped) + "\n")


def copy_original():
    """Copy original hand-annotated data with class ID remapping."""
    counts = {"train": 0, "val": 0}
    for class_id, img_dir, lbl_dir, split in ORIGINAL_SOURCES:
        if not img_dir.exists():
            print(f"  [SKIP] {img_dir}")
            continue
        img_out = OUT / "images" / split
        lbl_out = OUT / "labels" / split
        img_out.mkdir(parents=True, exist_ok=True)
        lbl_out.mkdir(parents=True, exist_ok=True)

        for img_path in list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.png")):
            stem       = f"orig_cls{class_id}_{img_path.stem}"
            dst_img    = img_out / (stem + img_path.suffix)
            src_lbl    = lbl_dir / (img_path.stem + ".txt")
            dst_lbl    = lbl_out / (stem + ".txt")

            shutil.copy2(img_path, dst_img)
            if src_lbl.exists():
                remap_label(src_lbl, dst_lbl, class_id)
            else:
                dst_lbl.write_text("")
            counts[split] += 1

    print(f"  Original data — train={counts['train']}  val={counts['val']}")


def copy_auto_annotated():
    """Copy auto-annotated data with train/val split."""
    auto_base = ROOT / "dataset" / "auto_annotated"
    if not auto_base.exists():
        print("  [SKIP] auto_annotated folder not found — run extract_and_annotate.py first")
        return

    total_train = total_val = 0

    for class_dir in sorted(auto_base.iterdir()):
        if not class_dir.is_dir():
            continue
        img_dir = class_dir / "images"
        lbl_dir = class_dir / "labels"
        if not img_dir.exists():
            continue

        images = sorted(list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.png")))
        random.shuffle(images)

        n_val   = max(1, int(len(images) * VAL_SPLIT))
        val_set = set(img.stem for img in images[:n_val])

        for img_path in images:
            split   = "val" if img_path.stem in val_set else "train"
            img_out = OUT / "images" / split
            lbl_out = OUT / "labels" / split
            img_out.mkdir(parents=True, exist_ok=True)
            lbl_out.mkdir(parents=True, exist_ok=True)

            dst_img = img_out / img_path.name
            src_lbl = lbl_dir / (img_path.stem + ".txt")
            dst_lbl = lbl_out / (img_path.stem + ".txt")

            shutil.copy2(img_path, dst_img)
            if src_lbl.exists():
                shutil.copy2(src_lbl, dst_lbl)
            else:
                dst_lbl.write_text("")

            if split == "train":
                total_train += 1
            else:
                total_val += 1

    print(f"  Auto-annotated data — train={total_train}  val={total_val}")


def write_yaml():
    yaml_path = ROOT / "models" / "fitness_full.yaml"
    names_str = "\n".join(f"  {k}: {v}" for k, v in CLASS_NAMES.items())
    content = f"""# YOLO Pose dataset config — Full 25-class fitness dataset
path: ../dataset_unified_full
train: images/train
val: images/val

kpt_shape: [17, 3]
flip_idx: [0, 2, 1, 4, 3, 6, 5, 8, 7, 10, 9, 12, 11, 14, 13, 16, 15]

nc: {len(CLASS_NAMES)}
names:
{names_str}
"""
    yaml_path.write_text(content)
    print(f"  YAML written: {yaml_path}")


def main():
    print(f"\n{'='*60}")
    print("  PREPARING FULL UNIFIED DATASET")
    print(f"{'='*60}\n")

    if OUT.exists():
        print(f"[INFO] Clearing: {OUT}")
        shutil.rmtree(OUT)

    print("[1] Copying original annotated data...")
    copy_original()

    print("[2] Copying auto-annotated data...")
    copy_auto_annotated()

    print("[3] Writing YAML config...")
    write_yaml()

    # Summary
    for split in ["train", "val"]:
        n = len(list((OUT / "images" / split).glob("*.jpg")))
        print(f"  {split}: {n} images")

    print(f"\n{'='*60}")
    print("  DONE — run utils/train_full_model.py next")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    random.seed(42)
    main()
