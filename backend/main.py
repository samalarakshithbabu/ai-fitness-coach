"""
main.py  –  AI Fitness Coach  –  FastAPI Backend
-------------------------------------------------
Endpoints:
  POST /upload-image        → detect exercise + analyse posture
  POST /upload-video        → frame-by-frame detection on video
  POST /detect-exercise     → YOLO detection only (raw JSON)
  POST /get-recommendation  → personalised workout plan
  GET  /history             → list stored sessions
  GET  /health              → server health check

  POST /predict-image       → image → YOLO → keypoints → classifier → posture
  POST /predict-video       → video/YouTube → frames → majority vote
  GET  /report              → last session report summary
"""

import os
import sys
import uuid
import json
import time
import sqlite3
import tempfile
import threading
import warnings
import logging

# Suppress noisy TF-Lite / protobuf / absl warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["GLOG_minloglevel"] = "3"
warnings.filterwarnings("ignore")
logging.getLogger("absl").setLevel(logging.ERROR)

from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from PIL import Image
import io

# ── path setup so utils/ is importable ───────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.posture_analyzer      import analyze_posture, _pose_based_detect
from utils.recommendation_engine import get_recommendation
from utils.voice_feedback        import speak, build_feedback_message
from utils.classifier            import predict_exercise as clf_predict

# ── YOLO model ────────────────────────────────────────────────────────────────
from ultralytics import YOLO

# Priority: full 25-class model → original 7-class model → base pretrained
FULL_WEIGHTS    = ROOT / "models" / "fitness_pose_full" / "weights" / "best.pt"
TRAINED_WEIGHTS = ROOT / "models" / "fitness_pose" / "weights" / "best.pt"
BASE_WEIGHTS    = "yolov8n-pose.pt"

if FULL_WEIGHTS.exists():
    print(f"[INFO] Loading full 25-class weights: {FULL_WEIGHTS}")
    yolo_model = YOLO(str(FULL_WEIGHTS))
    _active_weights = str(FULL_WEIGHTS)
elif TRAINED_WEIGHTS.exists():
    print(f"[INFO] Loading trained weights: {TRAINED_WEIGHTS}")
    yolo_model = YOLO(str(TRAINED_WEIGHTS))
    _active_weights = str(TRAINED_WEIGHTS)
else:
    print(f"[WARN] No trained weights found. Using base YOLOv8n-pose.")
    yolo_model = YOLO(BASE_WEIGHTS)
    _active_weights = BASE_WEIGHTS

# Class names — full 25-class map (7 original + 18 new)
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

# ── SQLite database ───────────────────────────────────────────────────────────
DB_PATH = ROOT / "fitness_history.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id          TEXT PRIMARY KEY,
            timestamp   REAL,
            exercise    TEXT,
            posture_ok  INTEGER,
            score       INTEGER,
            issues      TEXT,
            suggestions TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_session(session_id, exercise, posture):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO sessions VALUES (?,?,?,?,?,?,?)",
        (
            session_id,
            time.time(),
            exercise,
            int(posture["is_correct"]),
            posture["score"],
            json.dumps(posture["issues"]),
            json.dumps(posture["suggestions"]),
        ),
    )
    conn.commit()
    conn.close()

init_db()

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Fitness Coach",
    description="Exercise detection, posture analysis & personalised recommendations",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
FRONTEND = ROOT / "frontend"
if FRONTEND.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")


# ── helpers ───────────────────────────────────────────────────────────────────

def _bytes_to_bgr(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


CONFIDENCE_THRESHOLD = 0.35   # below this → report as unknown

# Minimum fraction of frames that must agree for a stable video prediction
_VIDEO_AGREEMENT_THRESHOLD = 0.30


def _preprocess_frame(bgr: np.ndarray, target_size: int = 640) -> np.ndarray:
    """
    Resize frame to target_size while preserving aspect ratio with letterboxing.
    This matches the preprocessing YOLO was trained with (letterbox, not stretch).
    """
    h, w = bgr.shape[:2]
    scale = target_size / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(bgr, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    # Pad to square
    canvas = np.full((target_size, target_size, 3), 114, dtype=np.uint8)
    pad_top  = (target_size - new_h) // 2
    pad_left = (target_size - new_w) // 2
    canvas[pad_top:pad_top + new_h, pad_left:pad_left + new_w] = resized
    return canvas


def _detect_exercise(bgr_frame: np.ndarray) -> tuple[str, float]:
    """
    Run YOLO on a BGR frame with proper letterbox preprocessing.
    Returns (exercise_name, confidence).
    """
    preprocessed = _preprocess_frame(bgr_frame)
    results = yolo_model(preprocessed, verbose=False)
    best_cls, best_conf = "unknown", 0.0
    for r in results:
        if r.boxes is not None and len(r.boxes):
            for box in r.boxes:
                cls_id = int(box.cls[0])
                conf   = float(box.conf[0])
                if conf > best_conf:
                    best_conf = conf
                    best_cls  = CLASS_NAMES.get(cls_id, "person")
    if best_conf < CONFIDENCE_THRESHOLD:
        return "unknown", best_conf
    return best_cls, best_conf


def _confidence_weighted_vote(
    votes: list[str], confidences: list[float]
) -> tuple[str, float]:
    """
    Weighted majority vote: each frame's vote is weighted by its confidence.
    Returns (winning_label, average_confidence_of_winning_label).

    This prevents a burst of low-confidence "deadlift" frames from overriding
    a smaller number of high-confidence "chest_fly_machine" frames.
    """
    from collections import defaultdict
    weight_map: dict[str, float] = defaultdict(float)
    count_map:  dict[str, int]   = defaultdict(int)

    for label, conf in zip(votes, confidences):
        weight_map[label] += conf
        count_map[label]  += 1

    # Winner = highest total confidence weight
    winner = max(weight_map, key=weight_map.__getitem__)
    avg_conf = weight_map[winner] / count_map[winner]
    return winner, round(avg_conf, 3)


def _draw_skeleton(bgr: np.ndarray, keypoints: list) -> np.ndarray:
    """Draw MediaPipe keypoints on image for visual feedback."""
    h, w = bgr.shape[:2]
    for kp in keypoints:
        if kp["visibility"] > 0.5:
            cx = int(kp["x"] * w)
            cy = int(kp["y"] * h)
            cv2.circle(bgr, (cx, cy), 5, (0, 255, 0), -1)
    return bgr


# ── routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "model": _active_weights}


@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image → detect exercise (YOLO + classifier + pose) → analyse posture → return full feedback.
    """
    data = await file.read()
    bgr  = _bytes_to_bgr(data)
    if bgr is None:
        raise HTTPException(400, "Invalid image file")

    # 1. Letterbox preprocess for YOLO
    preprocessed = _preprocess_frame(bgr)
    results = yolo_model(preprocessed, verbose=False)
    yolo_keypoints = []
    yolo_exercise, yolo_conf = "unknown", 0.0

    for r in results:
        if r.boxes is not None and len(r.boxes):
            for box in r.boxes:
                cls_id = int(box.cls[0])
                conf   = float(box.conf[0])
                if conf > yolo_conf:
                    yolo_conf     = conf
                    yolo_exercise = CLASS_NAMES.get(cls_id, "person")
        if r.keypoints is not None and len(r.keypoints):
            kps      = r.keypoints.xyn[0].tolist()
            kps_conf = (r.keypoints.conf[0].tolist()
                        if r.keypoints.conf is not None
                        else [1.0] * len(kps))
            for (x, y), v in zip(kps, kps_conf):
                yolo_keypoints.append({"x": x, "y": y, "z": 0.0, "visibility": float(v)})

    # 2. Classifier override (25 classes)
    clf_exercise, clf_conf = clf_predict(yolo_keypoints)
    if clf_exercise != "unknown" and clf_conf >= 0.30:
        exercise   = clf_exercise
        confidence = clf_conf
    elif yolo_conf >= CONFIDENCE_THRESHOLD:
        exercise   = yolo_exercise
        confidence = yolo_conf
    else:
        exercise   = clf_exercise if clf_exercise != "unknown" else yolo_exercise
        confidence = max(yolo_conf, clf_conf)

    # 3. Pose-based geometric override (MediaPipe)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    try:
        import mediapipe as _mp
        from utils.posture_analyzer import _landmarker
        _mp_img    = _mp.Image(image_format=_mp.ImageFormat.SRGB, data=rgb)
        _mp_result = _landmarker.detect(_mp_img)
        if _mp_result.pose_landmarks:
            pose_label = _pose_based_detect(_mp_result.pose_landmarks[0])
            if pose_label is not None:
                exercise   = pose_label
                confidence = max(confidence, 0.70)
    except Exception:
        pass

    # 4. Posture analysis
    posture = analyze_posture(rgb, exercise)

    # 5. Save to DB
    session_id = str(uuid.uuid4())
    save_session(session_id, exercise, posture)

    # 6. Voice feedback (non-blocking)
    msg = build_feedback_message(exercise, posture)
    speak(msg)

    return {
        "session_id":  session_id,
        "exercise":    exercise.replace("_", " ").title(),
        "confidence":  round(confidence, 3),
        "posture":     posture,
        "feedback":    msg,
    }


@app.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a video → sample frames → detect exercise (YOLO + classifier + pose) → aggregate posture results.
    """
    data = await file.read()

    suffix = Path(file.filename).suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        cap = cv2.VideoCapture(tmp_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        # Sample ~20 frames evenly, skip first/last 5%
        margin      = max(1, int(total_frames * 0.05))
        usable_start = margin
        usable_end   = max(usable_start + 1, total_frames - margin)
        sample_step  = max(1, (usable_end - usable_start) // 20)

        frame_results  = []
        exercise_votes = []
        conf_list      = []
        frame_idx = 0
        posture_frame_bgr = None  # save a middle frame for posture

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if (frame_idx >= usable_start
                    and frame_idx < usable_end
                    and (frame_idx - usable_start) % sample_step == 0):

                # YOLO + keypoints
                preprocessed = _preprocess_frame(frame)
                results = yolo_model(preprocessed, verbose=False)
                kps: list[dict] = []
                ex, conf = "unknown", 0.0

                for r in results:
                    if r.boxes is not None and len(r.boxes):
                        for box in r.boxes:
                            cls_id = int(box.cls[0])
                            c      = float(box.conf[0])
                            if c > conf:
                                conf = c
                                ex   = CLASS_NAMES.get(cls_id, "person")
                    if r.keypoints is not None and len(r.keypoints):
                        raw_kps  = r.keypoints.xyn[0].tolist()
                        raw_conf = (r.keypoints.conf[0].tolist()
                                    if r.keypoints.conf is not None
                                    else [1.0] * len(raw_kps))
                        for (x, y), v in zip(raw_kps, raw_conf):
                            kps.append({"x": x, "y": y, "z": 0.0, "visibility": float(v)})

                # Classifier override
                clf_ex, clf_conf = clf_predict(kps)
                if clf_ex != "unknown" and clf_conf >= 0.30:
                    ex, conf = clf_ex, clf_conf
                elif ex == "unknown" or conf < CONFIDENCE_THRESHOLD:
                    if clf_ex != "unknown":
                        ex, conf = clf_ex, clf_conf

                # Pose-based override
                try:
                    import mediapipe as _mp
                    from utils.posture_analyzer import _landmarker
                    rgb_frame  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    _mp_img    = _mp.Image(image_format=_mp.ImageFormat.SRGB, data=rgb_frame)
                    _mp_result = _landmarker.detect(_mp_img)
                    if _mp_result.pose_landmarks:
                        pose_label = _pose_based_detect(_mp_result.pose_landmarks[0])
                        if pose_label is not None:
                            ex   = pose_label
                            conf = max(conf, 0.70)
                except Exception:
                    pass

                if conf >= CONFIDENCE_THRESHOLD:
                    exercise_votes.append(ex)
                    conf_list.append(conf)
                    if posture_frame_bgr is None:
                        posture_frame_bgr = frame.copy()

                frame_results.append({
                    "frame":      frame_idx,
                    "exercise":   ex,
                    "confidence": round(conf, 3),
                })
            frame_idx += 1

        cap.release()
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    if not frame_results:
        raise HTTPException(400, "Could not read video frames")

    if not exercise_votes:
        return {
            "session_id":    None,
            "exercise":      "Not Supported",
            "average_score": 0,
            "total_frames":  total_frames,
            "sampled_frames": len(frame_results),
            "issues":        ["No exercise detected with sufficient confidence"],
            "frame_details": frame_results,
        }

    # Confidence-weighted majority vote
    top_exercise, avg_conf = _confidence_weighted_vote(exercise_votes, conf_list)
    agreement = exercise_votes.count(top_exercise) / len(exercise_votes)

    if top_exercise == "unknown" or agreement < _VIDEO_AGREEMENT_THRESHOLD:
        top_exercise = max(set(exercise_votes), key=exercise_votes.count)

    # Posture on representative frame
    posture = {"is_correct": False, "score": int(avg_conf * 100),
               "issues": [], "suggestions": [], "keypoints": []}
    if posture_frame_bgr is not None:
        try:
            rgb2 = cv2.cvtColor(posture_frame_bgr, cv2.COLOR_BGR2RGB)
            posture = analyze_posture(rgb2, top_exercise)
        except Exception:
            pass

    avg_score  = posture["score"]
    all_issues = posture["issues"]

    session_id = str(uuid.uuid4())
    save_session(session_id, top_exercise, posture)

    return {
        "session_id":    session_id,
        "exercise":      top_exercise.replace("_", " ").title(),
        "confidence":    round(avg_conf, 3),
        "average_score": avg_score,
        "total_frames":  total_frames,
        "sampled_frames": len(frame_results),
        "issues":        all_issues,
        "posture":       posture,
        "frame_details": frame_results,
    }


@app.post("/detect-exercise")
async def detect_exercise(file: UploadFile = File(...)):
    """YOLO detection only — returns exercise name and bounding box info."""
    data = await file.read()
    bgr  = _bytes_to_bgr(data)
    if bgr is None:
        raise HTTPException(400, "Invalid image")

    results = yolo_model(bgr, verbose=False)
    detections = []
    for r in results:
        if r.boxes is not None:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                detections.append({
                    "exercise":   CLASS_NAMES.get(cls_id, "unknown"),
                    "confidence": round(float(box.conf[0]), 3),
                    "bbox":       [round(v, 2) for v in box.xyxyn[0].tolist()],
                })

    return {"detections": detections}


@app.post("/get-recommendation")
async def get_recommendation_endpoint(
    age:            int   = Form(...),
    weight_kg:      float = Form(...),
    height_cm:      float = Form(...),
    fitness_goal:   str   = Form(...),
    detected_exercise: str = Form(""),
):
    """Return a personalised workout plan based on user profile."""
    plan = get_recommendation(age, weight_kg, height_cm, fitness_goal, detected_exercise)
    return plan


@app.get("/history")
def get_history(limit: int = 20):
    """Return the last N workout sessions from the database."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, timestamp, exercise, posture_ok, score, issues, suggestions "
        "FROM sessions ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()

    history = []
    for row in rows:
        history.append({
            "id":          row[0],
            "timestamp":   row[1],
            "exercise":    row[2],
            "posture_ok":  bool(row[3]),
            "score":       row[4],
            "issues":      json.loads(row[5]),
            "suggestions": json.loads(row[6]),
        })
    return {"history": history}


# ── /predict-image ────────────────────────────────────────────────────────────

@app.post("/predict-image")
async def predict_image(file: UploadFile = File(...)):
    """
    Image → letterbox preprocess → YOLO pose → keypoints → classifier → posture.
    Output: { "exercise": str, "confidence": float, "keypoints": [...], "posture": {...} }
    """
    start = time.time()
    data = await file.read()
    bgr  = _bytes_to_bgr(data)
    if bgr is None:
        raise HTTPException(400, "Invalid image file")

    # Step 1: Letterbox preprocess (matches YOLO training pipeline)
    preprocessed = _preprocess_frame(bgr)

    # Step 2: YOLO pose — extract keypoints from preprocessed frame
    results = yolo_model(preprocessed, verbose=False)
    yolo_keypoints = []
    yolo_exercise, yolo_conf = "unknown", 0.0

    for r in results:
        if r.boxes is not None and len(r.boxes):
            for box in r.boxes:
                cls_id = int(box.cls[0])
                conf   = float(box.conf[0])
                if conf > yolo_conf:
                    yolo_conf     = conf
                    yolo_exercise = CLASS_NAMES.get(cls_id, "person")

        if r.keypoints is not None and len(r.keypoints):
            kps      = r.keypoints.xyn[0].tolist()
            kps_conf = (r.keypoints.conf[0].tolist()
                        if r.keypoints.conf is not None
                        else [1.0] * len(kps))
            for (x, y), v in zip(kps, kps_conf):
                yolo_keypoints.append({"x": x, "y": y, "z": 0.0, "visibility": float(v)})

    # Step 3: Classifier prediction from keypoints
    clf_exercise, clf_conf = clf_predict(yolo_keypoints)

    # Decision logic: classifier uses pose geometry → trust it over YOLO's 7-class model
    if clf_exercise != "unknown" and clf_conf >= 0.30:
        exercise   = clf_exercise
        confidence = clf_conf
    elif yolo_conf >= CONFIDENCE_THRESHOLD:
        exercise   = yolo_exercise
        confidence = yolo_conf
    else:
        exercise   = clf_exercise if clf_exercise != "unknown" else "unknown"
        confidence = max(yolo_conf, clf_conf)

    # Step 4: Posture analysis (MediaPipe needs original RGB, not preprocessed)
    rgb     = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    # Pose-based override before posture analysis — catches chest_fly vs lateral_raise
    try:
        import mediapipe as mp
        from utils.posture_analyzer import _landmarker
        _mp_img    = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        _mp_result = _landmarker.detect(_mp_img)
        if _mp_result.pose_landmarks:
            pose_label = _pose_based_detect(_mp_result.pose_landmarks[0])
            if pose_label is not None:
                exercise   = pose_label
                confidence = max(confidence, 0.70)
    except Exception:
        pass

    posture = analyze_posture(rgb, exercise)

    keypoints = posture.get("keypoints") or yolo_keypoints

    session_id = str(uuid.uuid4())
    save_session(session_id, exercise, posture)

    processing_time = round(time.time() - start, 3)

    return {
        "session_id":       session_id,
        "exercise":         exercise.replace("_", " ").title(),
        "confidence":       round(confidence, 3),
        "posture":          posture,
        "keypoints":        keypoints,
        "processing_time":  processing_time,
        "status":           "success",
    }


# ── /predict-video ────────────────────────────────────────────────────────────

@app.post("/predict-video")
async def predict_video(
    file:         UploadFile = File(None),
    youtube_url:  str        = Form(None),
):
    """
    Flask-compat endpoint.
    Accepts either an uploaded video file OR a YouTube URL.
    Steps: download → extract frames → YOLO pose → classifier → majority vote.
    Output: { "exercise": str, "confidence": float, "frames_analyzed": int, ... }
    """
    start = time.time()

    # ── acquire video file ────────────────────────────────────────────────────
    tmp_path = None

    if youtube_url:
        # Download via yt-dlp
        try:
            import yt_dlp
        except ImportError:
            raise HTTPException(500, "yt-dlp not installed. Run: pip install yt-dlp")

        # Normalize YouTube Shorts URL → standard watch URL so yt-dlp handles it reliably
        # e.g. https://youtube.com/shorts/Kl3LEzQ5Zqs?si=... → https://www.youtube.com/watch?v=Kl3LEzQ5Zqs
        import re
        shorts_match = re.search(r"youtube\.com/shorts/([A-Za-z0-9_-]+)", youtube_url)
        if shorts_match:
            video_id = shorts_match.group(1)
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"

        # Use a temp directory so yt-dlp doesn't append extra extensions
        tmp_dir  = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, "video.mp4")

        ydl_opts = {
            # format 18 = 360p mp4 with video+audio in ONE file — no ffmpeg needed
            # fallback: worstvideo+worstaudio in single container
            "format":             "18/worst[ext=mp4]/worst",
            "outtmpl":            tmp_path,
            "quiet":              True,
            "noplaylist":         True,
            "no_warnings":        True,
            "nocheckcertificate": True,
            "no_color":           True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
            # yt-dlp may write video.mp4 or video.mp4.mp4 — find the actual file
            candidates = [f for f in os.listdir(tmp_dir) if f.startswith("video")]
            if not candidates:
                raise HTTPException(400, "yt-dlp downloaded nothing")
            tmp_path = os.path.join(tmp_dir, candidates[0])
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(400, f"Failed to download video: {e}")

    elif file:
        data = await file.read()
        suffix = Path(file.filename).suffix or ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
    else:
        raise HTTPException(400, "Provide either a video file or youtube_url")

    # ── process frames ────────────────────────────────────────────────────────
    cap = cv2.VideoCapture(tmp_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30

    # Sample ~30 frames evenly, but skip the first and last 5% (often transitions)
    margin      = max(1, int(total_frames * 0.05))
    usable_start = margin
    usable_end   = max(usable_start + 1, total_frames - margin)
    usable_count = usable_end - usable_start
    sample_step  = max(1, usable_count // 30)

    frame_results:  list[dict] = []
    exercise_votes: list[str]  = []
    conf_list:      list[float] = []
    frame_idx = 0
    _posture_frame_bgr = None   # capture a representative frame for posture analysis

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if (frame_idx >= usable_start
                and frame_idx < usable_end
                and (frame_idx - usable_start) % sample_step == 0):

            # YOLO pose on letterbox-preprocessed frame
            preprocessed = _preprocess_frame(frame)
            results = yolo_model(preprocessed, verbose=False)
            kps: list[dict] = []
            ex, conf = "unknown", 0.0

            for r in results:
                if r.boxes is not None and len(r.boxes):
                    for box in r.boxes:
                        cls_id = int(box.cls[0])
                        c      = float(box.conf[0])
                        if c > conf:
                            conf = c
                            ex   = CLASS_NAMES.get(cls_id, "person")

                if r.keypoints is not None and len(r.keypoints):
                    raw_kps  = r.keypoints.xyn[0].tolist()
                    raw_conf = (r.keypoints.conf[0].tolist()
                                if r.keypoints.conf is not None
                                else [1.0] * len(raw_kps))
                    for (x, y), v in zip(raw_kps, raw_conf):
                        kps.append({"x": x, "y": y, "z": 0.0, "visibility": float(v)})

            # Classifier override — trust classifier over YOLO for all exercises
            # (classifier uses pose geometry, YOLO only knows 7 classes)
            clf_ex, clf_conf = clf_predict(kps)
            if clf_ex != "unknown" and clf_conf >= 0.30:
                ex, conf = clf_ex, clf_conf
            elif ex == "unknown" or conf < CONFIDENCE_THRESHOLD:
                # YOLO didn't fire confidently, keep classifier result if any
                if clf_ex != "unknown":
                    ex, conf = clf_ex, clf_conf

            # Pose-based override — runs MediaPipe on this frame and applies
            # geometric rules. This catches chest_fly vs lateral_raise etc.
            # regardless of what YOLO or the classifier predicted.
            try:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                import mediapipe as mp
                from mediapipe.tasks import python as mp_python
                from mediapipe.tasks.python import vision as mp_vision
                _mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                from utils.posture_analyzer import _landmarker
                _mp_result = _landmarker.detect(_mp_img)
                if _mp_result.pose_landmarks:
                    pose_label = _pose_based_detect(_mp_result.pose_landmarks[0])
                    if pose_label is not None:
                        ex   = pose_label
                        conf = max(conf, 0.70)  # assign minimum confidence
            except Exception:
                pass

            # Only count frames where we actually detected something
            if conf >= CONFIDENCE_THRESHOLD:
                exercise_votes.append(ex)
                conf_list.append(conf)
                if _posture_frame_bgr is None:
                    _posture_frame_bgr = frame.copy()

            frame_results.append({
                "frame":      frame_idx,
                "exercise":   ex,
                "confidence": round(conf, 3),
            })

        frame_idx += 1

    cap.release()
    try:
        os.unlink(tmp_path)
        _tmp_dir = os.path.dirname(tmp_path)
        if _tmp_dir != tempfile.gettempdir() and os.path.isdir(_tmp_dir):
            import shutil
            shutil.rmtree(_tmp_dir, ignore_errors=True)
    except Exception:
        pass

    if not frame_results:
        raise HTTPException(400, "Could not read video frames or no person detected")

    # ── confidence-weighted majority vote ─────────────────────────────────────
    # If no frame passed the confidence threshold → unsupported
    if not exercise_votes:
        return {
            "session_id":      None,
            "exercise":        "Not Supported",
            "confidence":      0.0,
            "frames_analyzed": len(frame_results),
            "total_frames":    total_frames,
            "frame_details":   frame_results,
            "processing_time": round(time.time() - start, 3),
            "status":          "unsupported",
            "message":         "No exercise detected above confidence threshold.",
            "posture": {
                "is_correct": False,
                "score": 0,
                "issues": ["Exercise not detected with sufficient confidence"],
                "suggestions": ["Ensure the full body is visible and well-lit"],
                "keypoints": [],
            },
        }

    top_exercise, avg_conf = _confidence_weighted_vote(exercise_votes, conf_list)

    # Check if the winning class has enough agreement (>40% of confident frames)
    agreement = exercise_votes.count(top_exercise) / len(exercise_votes)

    # ── YOLO-only bias fix: if YOLO's 7 classes dominate but classifier
    # disagrees on most frames, trust the classifier majority instead ──────────
    YOLO_7_CLASSES = {
        "deadlift", "lateral_raise", "squat", "front_squat",
        "zercher_squat", "romanian_deadlift", "sumo_deadlift"
    }
    if top_exercise in YOLO_7_CLASSES:
        # collect classifier-only votes (from frames where clf fired)
        clf_votes = [ex for ex in exercise_votes if ex not in YOLO_7_CLASSES]
        if len(clf_votes) >= len(exercise_votes) * 0.3:
            from collections import Counter
            clf_top = Counter(clf_votes).most_common(1)[0][0]
            top_exercise = clf_top

    if top_exercise == "unknown" or agreement < _VIDEO_AGREEMENT_THRESHOLD:
        return {
            "session_id":      None,
            "exercise":        "Not Supported",
            "confidence":      avg_conf,
            "frames_analyzed": len(frame_results),
            "total_frames":    total_frames,
            "frame_details":   frame_results,
            "processing_time": round(time.time() - start, 3),
            "status":          "unsupported",
            "message":         (
                f"Prediction unstable — best guess '{top_exercise}' only agreed "
                f"in {agreement:.0%} of frames. "
                "Supported: Deadlift, Squat, Front Squat, Zercher Squat, "
                "Romanian Deadlift, Sumo Deadlift, Lateral Raise."
            ),
            "posture": {
                "is_correct": False,
                "score": 0,
                "issues": ["Exercise not supported or prediction too unstable"],
                "suggestions": ["Try one of the supported exercises with full body visible"],
                "keypoints": [],
            },
        }

    # ── run posture analysis on the middle sampled frame ─────────────────────
    # Use the frame we already captured during processing
    posture_result = {"is_correct": False, "score": int(avg_conf * 100),
                      "issues": [], "suggestions": [], "keypoints": []}
    if _posture_frame_bgr is not None:
        try:
            rgb2 = cv2.cvtColor(_posture_frame_bgr, cv2.COLOR_BGR2RGB)
            posture_result = analyze_posture(rgb2, top_exercise)
        except Exception:
            pass

    session_id = str(uuid.uuid4())
    save_session(session_id, top_exercise, posture_result)

    processing_time = round(time.time() - start, 3)

    return {
        "session_id":       session_id,
        "exercise":         top_exercise.replace("_", " ").title(),
        "confidence":       avg_conf,
        "frames_analyzed":  len(frame_results),
        "confident_frames": len(exercise_votes),
        "agreement":        round(agreement, 3),
        "total_frames":     total_frames,
        "frame_details":    frame_results,
        "processing_time":  processing_time,
        "status":           "success",
        "posture":          posture_result,
    }


# ── /report ───────────────────────────────────────────────────────────────────

@app.get("/report")
def get_report():
    """
    Return the most recent session as a structured report.
    Output: { input_type, exercise, confidence, processing_time, status }
    """
    conn = sqlite3.connect(DB_PATH)
    row  = conn.execute(
        "SELECT id, timestamp, exercise, posture_ok, score, issues, suggestions "
        "FROM sessions ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    conn.close()

    if not row:
        return {
            "status":          "no_data",
            "exercise":        None,
            "confidence":      None,
            "processing_time": None,
            "input_type":      None,
        }

    return {
        "session_id":      row[0],
        "timestamp":       row[1],
        "exercise":        row[2].replace("_", " ").title() if row[2] else None,
        "posture_ok":      bool(row[3]),
        "score":           row[4],
        "issues":          json.loads(row[5]),
        "suggestions":     json.loads(row[6]),
        "status":          "success",
        "input_type":      "image_or_video",
        "confidence":      round(row[4] / 100, 2),
        "processing_time": None,
    }
