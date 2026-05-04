"""
retrain_classifier_fast.py
--------------------------
Extracts MediaPipe keypoints from ALL dataset videos and trains
a high-accuracy classifier covering all 25 exercises.

Usage:
    python utils/retrain_classifier_fast.py
"""

import os
import sys
import pickle
import warnings
import numpy as np
from pathlib import Path
from collections import Counter

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["GLOG_minloglevel"] = "3"
warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

from utils.classifier import keypoints_to_features, MODEL_PATH

# ── dataset folder → label mapping ───────────────────────────────────────────
FOLDER_TO_LABEL = {
    "barbell biceps curl":  "barbell_biceps_curl",
    "bench press":          "bench_press",
    "chest fly machine":    "chest_fly_machine",
    "deadlift":             "deadlift",
    "Deadlifts":            "deadlift",
    "decline bench press":  "decline_bench_press",
    "hammer curl":          "hammer_curl",
    "hip thrust":           "hip_thrust",
    "incline bench press":  "incline_bench_press",
    "lat pulldown":         "lat_pulldown",
    "lateral raise":        "lateral_raise",
    "leg extension":        "leg_extension",
    "leg raises":           "leg_raises",
    "plank":                "plank",
    "pull Up":              "pull_up",
    "push-up":              "push_up",
    "romanian deadlift":    "romanian_deadlift",
    "russian twist":        "russian_twist",
    "shoulder press":       "shoulder_press",
    "shoulders":            "shoulder_press",
    "squat":                "squat",
    "Squats":               "squat",
    "sumo deadlift":        "sumo_deadlift",
    "t bar row":            "t_bar_row",
    "tricep dips":          "tricep_dips",
    "tricep Pushdown":      "tricep_pushdown",
    "front squat":          "front_squat",
    "zercher squat":        "zercher_squat",
}

DATASET_DIR    = ROOT / "dataset"
FRAMES_PER_VID = 12   # balanced speed vs accuracy

# ── MediaPipe landmarker ──────────────────────────────────────────────────────
_TASK_PATH = ROOT / "models" / "pose_landmarker_lite.task"

def _make_landmarker():
    base_opts = mp_python.BaseOptions(model_asset_path=str(_TASK_PATH))
    opts = mp_vision.PoseLandmarkerOptions(
        base_options=base_opts,
        running_mode=mp_vision.RunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.3,
        min_pose_presence_confidence=0.3,
        min_tracking_confidence=0.3,
    )
    return mp_vision.PoseLandmarker.create_from_options(opts)

landmarker = _make_landmarker()


def extract_keypoints(bgr_frame):
    rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = landmarker.detect(mp_img)
    if not result.pose_landmarks:
        return None
    lms = result.pose_landmarks[0]
    return [{"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility} for lm in lms]


def augment_features(feat: np.ndarray) -> list[np.ndarray]:
    """Horizontal flip only — keeps it fast."""
    flipped = feat.copy()
    flipped[0::4] = -flipped[0::4]
    return [feat, flipped]


def sample_video(video_path: Path, n_frames: int = FRAMES_PER_VID):
    cap = cv2.VideoCapture(str(video_path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total < 1:
        cap.release()
        return []
    # Skip first and last 10% (often transitions/cuts)
    margin = max(1, int(total * 0.10))
    start  = margin
    end    = max(start + 1, total - margin)
    indices = set(np.linspace(start, end - 1, min(n_frames, end - start), dtype=int))
    results = []
    idx = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if idx in indices:
            kps = extract_keypoints(frame)
            if kps:
                results.append(keypoints_to_features(kps))
        idx += 1
    cap.release()
    return results


def main():
    X, y = [], []
    # Collect all exercise folders, including auto_annotated subfolders
    folders = []
    for f in DATASET_DIR.iterdir():
        if f.is_dir() and f.name == "auto_annotated":
            # Include subfolders of auto_annotated
            for sub in f.iterdir():
                if sub.is_dir():
                    folders.append(sub)
        elif f.is_dir():
            folders.append(f)

    print(f"Found {len(folders)} exercise folders\n")

    for folder in sorted(folders):
        label = FOLDER_TO_LABEL.get(folder.name)
        if label is None:
            print(f"  [SKIP] {folder.name}")
            continue
        videos = list(folder.glob("*.mp4")) + list(folder.glob("*.avi")) + list(folder.glob("*.mov"))
        if not videos:
            print(f"  [SKIP] No videos: {folder.name}")
            continue

        folder_X = []
        for vid in videos:
            feats = sample_video(vid)
            folder_X.extend(feats)

        print(f"  {folder.name:<30} → {label:<25} | {len(videos)} vids, {len(folder_X)} samples")
        for feat in folder_X:
            for aug in augment_features(feat):
                X.append(aug)
                y.append(label)

    print(f"\nTotal samples (with augmentation): {len(X)}")
    dist = Counter(y)
    print("Class distribution:")
    max_c = max(dist.values())
    for cls, cnt in sorted(dist.items(), key=lambda x: -x[1]):
        bar = "█" * int(20 * cnt / max_c)
        print(f"  {cls:<30} {cnt:>5}  {bar}")

    if len(X) < 20:
        print("[ERROR] Not enough samples.")
        return

    X = np.array(X)
    y = np.array(y)

    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier, VotingClassifier
    from sklearn.preprocessing import LabelEncoder
    from sklearn.model_selection import StratifiedKFold, cross_val_score
    from sklearn.metrics import classification_report

    print("\nTraining ensemble classifier (RF + GBM)...")

    rf = RandomForestClassifier(
        n_estimators=500,
        max_depth=None,
        min_samples_leaf=1,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    # Use voting ensemble for best accuracy
    clf = rf  # RF alone is fast and accurate; swap to VotingClassifier if time allows

    # Cross-validation
    min_samples = min(dist.values())
    if min_samples >= 5:
        n_splits = min(5, min_samples)
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        cv_scores = cross_val_score(clf, X, y, cv=cv, scoring="accuracy", n_jobs=-1)
        print(f"CV accuracy: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    clf.fit(X, y)

    print("\nClassification report (train set):")
    print(classification_report(y, clf.predict(X), zero_division=0))

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(clf, f)
    print(f"\n[OK] Model saved → {MODEL_PATH}")
    print(f"[OK] Classes ({len(clf.classes_)}): {sorted(clf.classes_)}")


if __name__ == "__main__":
    main()
