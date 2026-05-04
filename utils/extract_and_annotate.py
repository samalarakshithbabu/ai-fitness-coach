"""
extract_and_annotate.py
-----------------------
Step 1 of full dataset expansion:
  - Extracts frames from all raw video folders in dataset/
  - Auto-annotates each frame using the existing YOLOv8 pose model
  - Saves frames + YOLO pose labels into dataset/auto_annotated/<exercise>/

Class ID mapping (extends existing 7 classes):
  0  deadlift
  1  lateral_raise
  2  squat
  3  front_squat
  4  zercher_squat
  5  romanian_deadlift
  6  sumo_deadlift
  7  bench_press
  8  incline_bench_press
  9  decline_bench_press
  10 barbell_biceps_curl
  11 hammer_curl
  12 shoulder_press
  13 lat_pulldown
  14 pull_up
  15 push_up
  16 leg_extension
  17 leg_raises
  18 hip_thrust
  19 plank
  20 tricep_dips
  21 tricep_pushdown
  22 t_bar_row
  23 russian_twist
  24 chest_fly_machine

Usage:
    python utils/extract_and_annotate.py
"""

import os
import sys
import cv2
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ultralytics import YOLO

# ── Load model ────────────────────────────────────────────────────────────────
# Use BASE yolov8n-pose (pretrained on COCO) — it detects human keypoints on
# ANY exercise. The class-specific model only knows 7 exercises and will skip
# all other exercises during annotation.
print("[INFO] Loading base YOLOv8n-pose for annotation (detects any human pose)")
model = YOLO("yolov8n-pose.pt")

# ── Raw video folder → (class_id, normalized_name) ───────────────────────────
VIDEO_SOURCES = {
    # Already-annotated folders (skip — already in dataset_unified)
    # "Deadlifts"  → handled by prepare_dataset.py
    # "Squats"     → handled by prepare_dataset.py
    # "shoulders"  → handled by prepare_dataset.py

    # New raw video folders
    "bench press":          (7,  "bench_press"),
    "incline bench press":  (8,  "incline_bench_press"),
    "decline bench press":  (9,  "decline_bench_press"),
    "barbell biceps curl":  (10, "barbell_biceps_curl"),
    "hammer curl":          (11, "hammer_curl"),
    "shoulder press":       (12, "shoulder_press"),
    "lat pulldown":         (13, "lat_pulldown"),
    "pull Up":              (14, "pull_up"),
    "push-up":              (15, "push_up"),
    "leg extension":        (16, "leg_extension"),
    "leg raises":           (17, "leg_raises"),
    "hip thrust":           (18, "hip_thrust"),
    "plank":                (19, "plank"),
    "tricep dips":          (20, "tricep_dips"),
    "tricep Pushdown":      (21, "tricep_pushdown"),
    "t bar row":            (22, "t_bar_row"),
    "russian twist":        (23, "russian_twist"),
    "chest fly machine":    (24, "chest_fly_machine"),
    # Raw video duplicates of already-annotated classes
    "deadlift":             (0,  "deadlift"),
    "squat":                (2,  "squat"),
    "lateral raise":        (1,  "lateral_raise"),
    "romanian deadlift":    (5,  "romanian_deadlift"),
}

FRAMES_PER_VIDEO = 30   # extract this many evenly-spaced frames per video
CONF_THRESHOLD   = 0.25  # lower threshold — base model is more conservative
OUT_BASE         = ROOT / "dataset" / "auto_annotated"


def extract_frames(video_path: Path, n_frames: int) -> list:
    """Extract n_frames evenly spaced from a video. Returns list of BGR frames."""
    cap = cv2.VideoCapture(str(video_path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total <= 0:
        cap.release()
        return []
    step = max(1, total // n_frames)
    frames = []
    idx = 0
    while cap.isOpened() and len(frames) < n_frames:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % step == 0:
            frames.append(frame)
        idx += 1
    cap.release()
    return frames


def frame_to_yolo_label(result, class_id: int) -> str | None:
    """
    Convert a single YOLO pose result to a YOLO pose label line.
    Format: class cx cy w h [kp_x kp_y kp_v] * 17
    Returns None if no person detected with sufficient confidence.
    """
    if result.boxes is None or len(result.boxes) == 0:
        return None

    # Pick highest-confidence box
    best_idx  = int(result.boxes.conf.argmax())
    conf      = float(result.boxes.conf[best_idx])
    if conf < CONF_THRESHOLD:
        return None

    # Bounding box (normalized xywh)
    box_xywhn = result.boxes.xywhn[best_idx].tolist()
    cx, cy, w, h = box_xywhn

    # Keypoints (normalized x, y, visibility)
    if result.keypoints is None or len(result.keypoints) == 0:
        return None

    kps_xy  = result.keypoints.xyn[best_idx].tolist()   # [[x,y], ...]
    kps_vis = (
        result.keypoints.conf[best_idx].tolist()
        if result.keypoints.conf is not None
        else [1.0] * len(kps_xy)
    )

    if len(kps_xy) < 17:
        return None

    kp_str = " ".join(
        f"{x:.6f} {y:.6f} {v:.6f}"
        for (x, y), v in zip(kps_xy[:17], kps_vis[:17])
    )

    return f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f} {kp_str}"


def process_folder(folder_name: str, class_id: int, class_label: str):
    src_dir = ROOT / "dataset" / folder_name
    if not src_dir.exists():
        print(f"  [SKIP] {folder_name} — folder not found")
        return 0, 0

    video_files = (
        list(src_dir.glob("*.mp4")) +
        list(src_dir.glob("*.MP4")) +
        list(src_dir.glob("*.mov")) +
        list(src_dir.glob("*.MOV")) +
        list(src_dir.glob("*.avi")) +
        list(src_dir.glob("*.AVI"))
    )

    if not video_files:
        print(f"  [SKIP] {folder_name} — no video files found")
        return 0, 0

    out_img = OUT_BASE / class_label / "images"
    out_lbl = OUT_BASE / class_label / "labels"
    out_img.mkdir(parents=True, exist_ok=True)
    out_lbl.mkdir(parents=True, exist_ok=True)

    saved = 0
    skipped = 0

    for vid_path in video_files:
        frames = extract_frames(vid_path, FRAMES_PER_VIDEO)
        if not frames:
            print(f"    [WARN] Could not read: {vid_path.name}")
            continue

        results = model(frames, verbose=False)

        for i, (frame, result) in enumerate(zip(frames, results)):
            label_line = frame_to_yolo_label(result, class_id)
            if label_line is None:
                skipped += 1
                continue

            stem = f"cls{class_id}_{vid_path.stem}_f{i:03d}"
            img_path = out_img / f"{stem}.jpg"
            lbl_path = out_lbl / f"{stem}.txt"

            cv2.imwrite(str(img_path), frame)
            lbl_path.write_text(label_line + "\n")
            saved += 1

    return saved, skipped


def main():
    print(f"\n{'='*60}")
    print("  FRAME EXTRACTION + AUTO-ANNOTATION")
    print(f"{'='*60}\n")

    if OUT_BASE.exists():
        print(f"[INFO] Clearing previous output: {OUT_BASE}")
        shutil.rmtree(OUT_BASE)

    total_saved   = 0
    total_skipped = 0

    for folder_name, (class_id, class_label) in VIDEO_SOURCES.items():
        print(f"[{class_id:02d}] {folder_name} → {class_label}")
        saved, skipped = process_folder(folder_name, class_id, class_label)
        print(f"      saved={saved}  skipped={skipped}")
        total_saved   += saved
        total_skipped += skipped

    print(f"\n{'='*60}")
    print(f"  DONE — saved={total_saved}  skipped={total_skipped}")
    print(f"  Output: {OUT_BASE}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
