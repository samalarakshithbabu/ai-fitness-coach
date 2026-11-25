# AI-Powered Personal Fitness Coach

**Final Year Major Project** — Deep Learning · FastAPI · MediaPipe · YOLOv8 · React

An end-to-end AI fitness coaching system that detects exercises from images and videos, analyses posture in real-time using body keypoints, and delivers personalised workout and diet recommendations.

---

## What It Does

Upload a gym photo or video (or paste a YouTube link) and the system will:

1. **Identify the exercise** — using a 3-stage ML pipeline covering 25 exercise classes
2. **Score your posture** — rule-based checks on 33 body keypoints, scored 0–100
3. **Flag form issues** — specific problems and how to fix them
4. **Recommend a plan** — BMI-aware workout + diet plan tailored to your goal

---

## ML Pipeline (3-Stage Hierarchical)

```
Input image/video
      │
      ▼
┌─────────────────────────────┐
│  Stage 1: YOLOv8-pose       │  7 classes (deadlift, squat variants,
│  (trained weights)          │  lateral raise, sumo/romanian deadlift)
└────────────┬────────────────┘
             │ keypoints
             ▼
┌─────────────────────────────┐
│  Stage 2: RandomForest      │  22 classes — claimed 96.9% CV accuracy (unverified)
│  Classifier                 │  trained from 14,876 video keypoint samples
└────────────┬────────────────┘
             │ label
             ▼
┌─────────────────────────────┐
│  Stage 3: MediaPipe         │  Geometric rules — catches chest fly vs
│  Pose-Based Override        │  lateral raise, bench press orientation, etc.
└────────────┬────────────────┘
             │
             ▼
      Posture Analysis
   (25 exercise-specific
      rule sets)
```

## Supported Exercises (25 Classes)

| # | Exercise | # | Exercise |
|---|----------|---|----------|
| 0 | Deadlift | 13 | Lat Pulldown |
| 1 | Lateral Raise | 14 | Pull Up |
| 2 | Squat | 15 | Push Up |
| 3 | Front Squat | 16 | Leg Extension |
| 4 | Zercher Squat | 17 | Leg Raises |
| 5 | Romanian Deadlift | 18 | Hip Thrust |
| 6 | Sumo Deadlift | 19 | Plank |
| 7 | Bench Press | 20 | Tricep Dips |
| 8 | Incline Bench Press | 21 | Tricep Pushdown |
| 9 | Decline Bench Press | 22 | T-Bar Row |
| 10 | Barbell Biceps Curl | 23 | Russian Twist |
| 11 | Hammer Curl | 24 | Chest Fly Machine |
| 12 | Shoulder Press | | |

## Project Structure

```
ai-fitness-coach/
├── backend/
│   └── main.py                   ← FastAPI server — all 9 API endpoints
│
├── frontend/                     ← Vanilla JS dark-theme UI
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── fitness-coach-ui/             ← React + Tailwind UI (5 pages)
│   └── src/
│       ├── pages/
│       │   ├── Home.jsx          ← Landing page
│       │   ├── Dashboard.jsx     ← Live stats + recharts
│       │   ├── Workout.jsx       ← Detection UI + YouTube support
│       │   ├── Diet.jsx          ← Diet plan generator
│       │   └── Exercises.jsx     ← Searchable exercise library
│       └── components/
│
├── models/
│   ├── fitness_pose/
│   │   └── weights/best.pt       ← Trained YOLOv8n-pose (7-class, 19 MB)
│   ├── pose_landmarker_lite.task ← MediaPipe pose model (5.5 MB)
│   └── fitness.yaml              ← YOLO dataset config
│
├── utils/
│   ├── classifier.py             ← RF classifier — feature extraction + inference
│   ├── posture_analyzer.py       ← 25 exercise posture rule sets + MediaPipe
│   ├── retrain_classifier_fast.py← Trains classifier from video keypoints
│   ├── recommendation_engine.py  ← BMI-aware workout planner
│   ├── voice_feedback.py         ← Offline TTS via pyttsx3
│   ├── train_model.py            ← YOLOv8 training script
│   ├── prepare_dataset.py        ← Unifies YOLO dataset folders
│   └── test_project.py           ← Integration test suite
│
├── requirements.txt
└── README.md
```

## Model Performance

| Model | Classes | Accuracy | Notes |
|-------|---------|----------|-------|
| YOLOv8n-pose | 7 | Trained on custom dataset | Deadlift, squat variants, lateral raise |
| RandomForest classifier | 22 | **96.9% CV accuracy (claimed, unverified)** | 14,876 samples, 5-fold stratified CV |
| MediaPipe pose rules | 25 | Geometric heuristics | Overrides ML when pose is unambiguous |

## Setup & Run

### 1 — Install Dependencies
```bash
pip install -r requirements.txt
```

### 2 — Train the Classifier (Required)
*Model file not in repo (427 MB). Dataset not included (714 videos).*
```bash
python utils/retrain_classifier_fast.py
```
- Extracts MediaPipe keypoints from all videos in `dataset/`
- Trains RandomForest classifier (~5–10 min)
- Saves to `models/exercise_classifier.pkl`
- Place exercise videos in `dataset/<exercise name>/` folders

### 3 — Start the Backend
```bash
uvicorn backend.main:app --reload --port 8000
```

### 4 — Open the Frontend

**Vanilla JS UI:**
```
http://localhost:8000/static/index.html
```

**React UI:**
```bash
cd fitness-coach-ui
npm install
npm start        # opens http://localhost:3000
```

### 5 — (Optional) Retrain YOLOv8
```bash
python utils/prepare_dataset.py   # unify dataset into dataset_unified/
python utils/train_model.py       # train YOLOv8n-pose (~30–60 min on CPU)
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload-image` | Full pipeline: YOLO + classifier + posture |
| POST | `/upload-video` | Video frame sampling + majority vote |
| POST | `/predict-image` | Same as upload-image (used by React UI) |
| POST | `/predict-video` | Video or YouTube URL → exercise + posture |
| POST | `/detect-exercise` | YOLO detection only (raw bounding boxes) |
| POST | `/get-recommendation` | BMI-aware workout plan |
| GET | `/history` | Past sessions from SQLite |
| GET | `/report` | Last session summary |
| GET | `/health` | Server status + active model path |
| GET | `/docs` | Auto-generated Swagger UI |

## Features

- **Exercise detection** — 25 classes via 3-stage ML pipeline
- **Posture scoring** — 0–100 score with specific issue detection per exercise
- **Video analysis** — samples 20–30 frames, confidence-weighted majority vote
- **YouTube support** — paste any YouTube URL for analysis via yt-dlp
- **Workout recommendations** — beginner/intermediate/advanced × fat loss/muscle gain/endurance
- **Diet plans** — BMI-aware meal plans with calorie targets
- **Session history** — SQLite database, viewable in dashboard
- **Voice feedback** — offline TTS via pyttsx3
- **Two frontends** — vanilla JS (lightweight) + React + Tailwind (full-featured)
- **Health check script** — `python utils/_health_check.py` verifies all components

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Uvicorn, Python 3.12 |
| ML — Detection | YOLOv8n-pose (Ultralytics) |
| ML — Classification | scikit-learn RandomForest |
| ML — Pose | MediaPipe Tasks API (33 keypoints) |
| Computer Vision | OpenCV |
| Frontend (vanilla) | HTML5, CSS3, Vanilla JS |
| Frontend (React) | React 18, React Router, Tailwind CSS, Recharts |
| Database | SQLite |
| Video download | yt-dlp |
| TTS | pyttsx3 |

## Notes

- `models/exercise_classifier.pkl` excluded from repo (427 MB). Regenerate with `python utils/retrain_classifier_fast.py`
- `dataset/` excluded (714 videos). Classifier training expects videos in `dataset/<folder>/`
- `yolov8n-pose.pt` base weights auto-download from Ultralytics on first run
- 3 classes without video data (`front_squat`, `zercher_squat`, `sumo_deadlift`) handled by YOLO model trained on original annotated dataset

---

## Author

**SAMALA RAKSHITH BABU**  

**Contact:**  
- Email: samalarakshithbabu7@gmail.com  
- LinkedIn: https://www.linkedin.com/in/samala-rakshith-babu/  
- GitHub: https://github.com/samalarakshithbabu  

---

## License

MIT License