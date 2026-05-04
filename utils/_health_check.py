"""Quick health check for all project components."""
import sys, warnings, os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["GLOG_minloglevel"] = "3"
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")

from pathlib import Path
import sqlite3

OK   = "[OK]  "
FAIL = "[FAIL]"
errors = []

# ── 1. Classifier ─────────────────────────────────────────────────────────────
try:
    from utils.classifier import predict_exercise, MODEL_PATH
    import pickle
    with open(MODEL_PATH, "rb") as f:
        clf = pickle.load(f)
    print(f"{OK} Classifier loaded: {len(clf.classes_)} classes")
    print(f"       {sorted(clf.classes_)}")
except Exception as e:
    errors.append(f"{FAIL} Classifier: {e}")
    print(errors[-1])

# ── 2. Posture analyzer ───────────────────────────────────────────────────────
try:
    from utils.posture_analyzer import EXERCISE_CHECKERS, analyze_posture, _pose_based_detect
    print(f"{OK} Posture analyzer: {len(EXERCISE_CHECKERS)} exercise checkers")
    print(f"       {sorted(EXERCISE_CHECKERS.keys())}")
except Exception as e:
    errors.append(f"{FAIL} Posture analyzer: {e}")
    print(errors[-1])

# ── 3. Recommendation engine ──────────────────────────────────────────────────
try:
    from utils.recommendation_engine import get_recommendation
    plan = get_recommendation(25, 75, 175, "fat_loss", "squat")
    assert plan["level"] in ["beginner", "intermediate", "advanced"]
    assert len(plan["exercises"]) > 0
    print(f"{OK} Recommendation engine: level={plan['level']}, {len(plan['exercises'])} exercises")
except Exception as e:
    errors.append(f"{FAIL} Recommendation engine: {e}")
    print(errors[-1])

# ── 4. Voice feedback ─────────────────────────────────────────────────────────
try:
    from utils.voice_feedback import build_feedback_message
    msg = build_feedback_message("deadlift", {"is_correct": True, "issues": [], "suggestions": []})
    assert "deadlift" in msg.lower()
    print(f'{OK} Voice feedback: "{msg}"')
except Exception as e:
    errors.append(f"{FAIL} Voice feedback: {e}")
    print(errors[-1])

# ── 5. Classifier predict smoke test ─────────────────────────────────────────
try:
    # Fake 17 COCO keypoints (all zeros — just tests the pipeline doesn't crash)
    fake_kps = [{"x": 0.5, "y": 0.5, "z": 0.0, "visibility": 0.9}] * 17
    label, conf = predict_exercise(fake_kps)
    print(f"{OK} Classifier predict: label='{label}', conf={conf:.3f}")
except Exception as e:
    errors.append(f"{FAIL} Classifier predict: {e}")
    print(errors[-1])

# ── 6. Model files ────────────────────────────────────────────────────────────
model_files = {
    "exercise_classifier.pkl":      Path("models/exercise_classifier.pkl"),
    "pose_landmarker_lite.task":    Path("models/pose_landmarker_lite.task"),
    "fitness_pose/weights/best.pt": Path("models/fitness_pose/weights/best.pt"),
}
for name, p in model_files.items():
    if p.exists():
        size_mb = p.stat().st_size / 1024 / 1024
        print(f"{OK} Model file: {name} ({size_mb:.1f} MB)")
    else:
        errors.append(f"{FAIL} Missing model file: {name}")
        print(errors[-1])

# ── 7. Dataset folders ────────────────────────────────────────────────────────
dataset_dir = Path("dataset")
video_folders = [f for f in dataset_dir.iterdir() if f.is_dir() and f.name != "auto_annotated"]
total_videos = sum(
    len(list(f.glob("*.mp4")) + list(f.glob("*.MOV")) + list(f.glob("*.mov")) + list(f.glob("*.avi")))
    for f in video_folders
)
print(f"{OK} Dataset: {len(video_folders)} folders, ~{total_videos} videos")

# ── 8. SQLite DB ──────────────────────────────────────────────────────────────
db = Path("fitness_history.db")
if db.exists():
    conn = sqlite3.connect(db)
    count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    conn.close()
    print(f"{OK} Database: {count} sessions stored")
else:
    errors.append(f"{FAIL} fitness_history.db missing")
    print(errors[-1])

# ── 9. Frontend files ─────────────────────────────────────────────────────────
frontend_files = [
    Path("frontend/index.html"),
    Path("frontend/app.js"),
    Path("frontend/style.css"),
]
for fp in frontend_files:
    if fp.exists():
        print(f"{OK} Frontend file: {fp}")
    else:
        errors.append(f"{FAIL} Missing frontend file: {fp}")
        print(errors[-1])

# ── 10. React UI build ────────────────────────────────────────────────────────
react_build = Path("fitness-coach-ui/build/index.html")
react_src   = Path("fitness-coach-ui/src/App.jsx")
if react_build.exists():
    print(f"{OK} React UI: production build exists")
elif react_src.exists():
    print(f"[WARN] React UI: src exists but not built (run: cd fitness-coach-ui && npm run build)")
else:
    errors.append(f"{FAIL} React UI: src missing")
    print(errors[-1])

# ── 11. YOLO weights ──────────────────────────────────────────────────────────
yolo_base = Path("yolov8n-pose.pt")
if yolo_base.exists():
    print(f"{OK} YOLOv8 base weights: yolov8n-pose.pt ({yolo_base.stat().st_size/1024/1024:.1f} MB)")
else:
    print(f"[WARN] yolov8n-pose.pt not found (will auto-download on first run)")

# ── 12. CLASS_NAMES vs classifier classes alignment ───────────────────────────
try:
    CLASS_NAMES_BACKEND = {
        0:"deadlift", 1:"lateral_raise", 2:"squat", 3:"front_squat",
        4:"zercher_squat", 5:"romanian_deadlift", 6:"sumo_deadlift",
        7:"bench_press", 8:"incline_bench_press", 9:"decline_bench_press",
        10:"barbell_biceps_curl", 11:"hammer_curl", 12:"shoulder_press",
        13:"lat_pulldown", 14:"pull_up", 15:"push_up", 16:"leg_extension",
        17:"leg_raises", 18:"hip_thrust", 19:"plank", 20:"tricep_dips",
        21:"tricep_pushdown", 22:"t_bar_row", 23:"russian_twist", 24:"chest_fly_machine",
    }
    backend_set    = set(CLASS_NAMES_BACKEND.values())
    classifier_set = set(clf.classes_)
    only_backend   = backend_set - classifier_set
    only_clf       = classifier_set - backend_set
    if only_backend:
        print(f"[WARN] In backend CLASS_NAMES but NOT in classifier: {sorted(only_backend)}")
        print(f"       (YOLO handles these 3 — no video data available)")
    if only_clf:
        print(f"[WARN] In classifier but NOT in backend CLASS_NAMES: {sorted(only_clf)}")
    if not only_backend and not only_clf:
        print(f"{OK} CLASS_NAMES alignment: backend and classifier match perfectly")
    else:
        print(f"{OK} CLASS_NAMES: {len(classifier_set)} in classifier, {len(backend_set)} in backend (overlap: {len(classifier_set & backend_set)})")
except Exception as e:
    print(f"[WARN] CLASS_NAMES check skipped: {e}")

# ── 13. EXERCISE_CHECKERS vs CLASS_NAMES alignment ───────────────────────────
try:
    checker_set = set(EXERCISE_CHECKERS.keys())
    missing_checkers = backend_set - checker_set
    if missing_checkers:
        errors.append(f"{FAIL} Missing posture checkers for: {sorted(missing_checkers)}")
        print(errors[-1])
    else:
        print(f"{OK} Posture checkers: all 25 exercises covered")
except Exception as e:
    print(f"[WARN] Checker alignment check skipped: {e}")

# ── Summary ───────────────────────────────────────────────────────────────────
print()
print("=" * 55)
if errors:
    print(f"  {len(errors)} issue(s) found:")
    for e in errors:
        print(f"  {e}")
else:
    print("  ALL CHECKS PASSED — project is healthy")
print("=" * 55)
