"""
classifier.py
-------------
Lightweight exercise classifier using keypoints from MediaPipe/YOLO.
Uses scikit-learn RandomForest trained on keypoint feature vectors.

Training:
    python utils/classifier.py --train

Inference:
    from utils.classifier import predict_exercise
    label, confidence = predict_exercise(keypoints_list)
"""

import pickle
import argparse
import numpy as np
from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "exercise_classifier.pkl"

# Full 25-class label map — must match CLASS_NAMES in main.py exactly
LABELS = [
    "deadlift",           # 0
    "lateral_raise",      # 1
    "squat",              # 2
    "front_squat",        # 3
    "zercher_squat",      # 4
    "romanian_deadlift",  # 5
    "sumo_deadlift",      # 6
    "bench_press",        # 7
    "incline_bench_press",# 8
    "decline_bench_press",# 9
    "barbell_biceps_curl",# 10
    "hammer_curl",        # 11
    "shoulder_press",     # 12
    "lat_pulldown",       # 13
    "pull_up",            # 14
    "push_up",            # 15
    "leg_extension",      # 16
    "leg_raises",         # 17
    "hip_thrust",         # 18
    "plank",              # 19
    "tricep_dips",        # 20
    "tricep_pushdown",    # 21
    "t_bar_row",          # 22
    "russian_twist",      # 23
    "chest_fly_machine",  # 24
]

# ── COCO-17 hip indices (used when YOLO gives 17 keypoints)
# COCO-17: 11=left_hip, 12=right_hip
_COCO17_HIP_L = 11
_COCO17_HIP_R = 12

# MediaPipe-33 hip indices
_MP33_HIP_L = 23
_MP33_HIP_R = 24


# ── feature extraction ────────────────────────────────────────────────────────

def keypoints_to_features(keypoints: list) -> np.ndarray:
    """
    Convert a list of keypoint dicts to a normalised flat feature vector.

    Supports both:
      - 17-keypoint COCO format (from YOLO)   → hip at indices 11, 12
      - 33-keypoint MediaPipe format           → hip at indices 23, 24

    Normalisation: subtract hip midpoint from all (x, y) coordinates so the
    feature vector is translation-invariant regardless of where in the frame
    the person stands.

    Output is always padded/truncated to 33 keypoints × 4 values = 132 dims.
    """
    if not keypoints:
        return np.zeros(33 * 4, dtype=np.float32)

    coords = np.array(
        [[kp["x"], kp["y"], kp.get("z", 0.0), kp.get("visibility", 1.0)]
         for kp in keypoints],
        dtype=np.float32,
    )

    n = len(coords)

    # ── pick the correct hip indices based on keypoint count ─────────────────
    if n >= 33:
        # MediaPipe 33-keypoint format
        hip_l_idx, hip_r_idx = _MP33_HIP_L, _MP33_HIP_R
    elif n >= 13:
        # COCO 17-keypoint format (YOLO)
        hip_l_idx, hip_r_idx = _COCO17_HIP_L, _COCO17_HIP_R
    else:
        # Too few keypoints — still normalise against centroid
        hip_l_idx = hip_r_idx = None

    # ── normalise x,y relative to hip midpoint ────────────────────────────────
    if hip_l_idx is not None:
        hip_mid = (coords[hip_l_idx, :2] + coords[hip_r_idx, :2]) / 2.0
    else:
        hip_mid = coords[:, :2].mean(axis=0)

    coords[:, :2] -= hip_mid

    # ── scale by torso height for scale invariance ────────────────────────────
    # torso height ≈ distance from hip midpoint to shoulder midpoint
    if n >= 13:
        sh_l_idx = 5 if n < 33 else 11   # COCO: 5=left_shoulder, MP: 11=left_shoulder
        sh_r_idx = 6 if n < 33 else 12
        torso_h = np.linalg.norm(
            (coords[sh_l_idx, :2] + coords[sh_r_idx, :2]) / 2.0
        )
        if torso_h > 1e-4:
            coords[:, :2] /= torso_h

    # ── pad or truncate to 33 keypoints ──────────────────────────────────────
    target = 33
    if n < target:
        pad = np.zeros((target - n, 4), dtype=np.float32)
        coords = np.vstack([coords, pad])
    else:
        coords = coords[:target]

    return coords.flatten()


# ── inference ─────────────────────────────────────────────────────────────────

def _load_model():
    if MODEL_PATH.exists():
        with open(MODEL_PATH, "rb") as f:
            return pickle.load(f)
    return None


_clf = None  # lazy-loaded singleton


def predict_exercise(keypoints: list) -> tuple[str, float]:
    """
    Predict exercise from keypoints.
    Returns (label, confidence). Falls back to 'unknown' if model not trained.
    """
    global _clf
    # Reload if the pkl was updated since last load
    if _clf is None or (MODEL_PATH.exists() and
            MODEL_PATH.stat().st_mtime > getattr(_clf, '_load_time', 0)):
        _clf = _load_model()
        if _clf is not None:
            _clf._load_time = MODEL_PATH.stat().st_mtime

    if _clf is None:
        return "unknown", 0.0

    features = keypoints_to_features(keypoints).reshape(1, -1)
    label = _clf.predict(features)[0]
    proba = _clf.predict_proba(features)[0]
    confidence = float(np.max(proba))
    return label, confidence


# ── training ──────────────────────────────────────────────────────────────────

def train_from_dataset(dataset_dir: str = None):
    """
    Train classifier from dataset_unified labels.
    Parses YOLO pose label files: class cx cy w h [kp_x kp_y kp_v] * 17
    Saves model to models/exercise_classifier.pkl.

    Handles class imbalance via class_weight='balanced' in RandomForest.
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import StratifiedKFold, cross_val_score
    from sklearn.metrics import classification_report
    from collections import Counter

    ROOT = Path(__file__).resolve().parent.parent
    dataset_dir = dataset_dir or str(ROOT / "dataset_unified")
    label_dir = Path(dataset_dir) / "labels" / "train"

    if not label_dir.exists():
        print(f"[ERROR] Label directory not found: {label_dir}")
        print("        Run utils/prepare_dataset.py first.")
        return

    X, y = [], []

    for txt_file in label_dir.glob("*.txt"):
        try:
            lines = txt_file.read_text().strip().splitlines()
            for line in lines:
                parts = list(map(float, line.split()))
                # Need at least: cls cx cy w h + 17*(x y v) = 5 + 51 = 56 values
                if len(parts) < 56:
                    continue
                cls_id = int(parts[0])
                if cls_id >= len(LABELS):
                    continue
                # Extract 17 COCO keypoints (x, y, visibility)
                kp_data = parts[5:]
                keypoints = []
                for i in range(0, min(len(kp_data), 17 * 3), 3):
                    keypoints.append({
                        "x":          kp_data[i],
                        "y":          kp_data[i + 1],
                        "z":          0.0,
                        "visibility": kp_data[i + 2],
                    })
                features = keypoints_to_features(keypoints)
                X.append(features)
                y.append(LABELS[cls_id])
        except Exception as e:
            print(f"[WARN] Skipping {txt_file.name}: {e}")

    if len(X) < 10:
        print(f"[ERROR] Not enough samples ({len(X)}) to train. Check dataset.")
        return

    X = np.array(X)
    y = np.array(y)

    # ── report class distribution ─────────────────────────────────────────────
    dist = Counter(y)
    print(f"\n[INFO] Training on {len(X)} samples across {len(dist)} classes")
    print("[INFO] Class distribution:")
    max_count = max(dist.values())
    for cls, cnt in sorted(dist.items(), key=lambda x: -x[1]):
        bar = "█" * int(20 * cnt / max_count)
        print(f"  {cls:<25} {cnt:>4}  {bar}")

    # ── train with class_weight='balanced' to handle imbalance ───────────────
    clf = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=2,
        class_weight="balanced",   # compensates for unequal class sizes
        random_state=42,
        n_jobs=-1,
    )

    # 5-fold stratified cross-validation for honest accuracy estimate
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(clf, X, y, cv=cv, scoring="accuracy")
    print(f"\n[INFO] 5-fold CV accuracy: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    # Final fit on all data
    clf.fit(X, y)

    print("\n[INFO] Training set classification report:")
    print(classification_report(y, clf.predict(X)))

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(clf, f)
    print(f"\n[INFO] Model saved to {MODEL_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true", help="Train the classifier")
    args = parser.parse_args()
    if args.train:
        train_from_dataset()
    else:
        print("Usage: python utils/classifier.py --train")
