# AI-Powered Personal Fitness Coach

Final Year Major Project — Deep Learning + FastAPI + MediaPipe

## Project Structure

```
├── backend/
│   └── main.py              ← FastAPI server (all API endpoints)
├── frontend/
│   ├── index.html           ← Single-page UI
│   ├── style.css            ← Dark-theme styling
│   └── app.js               ← Frontend logic
├── models/
│   └── fitness.yaml         ← YOLO dataset config
├── utils/
│   ├── prepare_dataset.py   ← Unifies dataset/ into dataset_unified/
│   ├── train_model.py       ← Trains YOLOv8-pose on your dataset
│   ├── posture_analyzer.py  ← MediaPipe posture rules
│   ├── recommendation_engine.py ← Rule-based workout planner
│   └── voice_feedback.py    ← Text-to-speech (pyttsx3)
├── dataset/                 ← Your existing YOLO dataset (DO NOT MODIFY)
├── requirements.txt
└── README.md
```

## Exercise Classes (from your dataset)

| ID | Class          | Dataset folder                        |
|----|----------------|---------------------------------------|
| 0  | deadlift       | dataset/Deadlifts/deadlift Data29     |
| 1  | lateral_raise  | dataset/shoulders/lateral data29      |
| 2  | squat          | dataset/Squats/squats data29          |
| 3  | front_squat    | dataset/Squats/front_squat data29     |
| 4  | zercher_squat  | dataset/Squats/zercher Data29         |

## Setup & Run

### Step 1 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 2 — Prepare dataset (unify all exercise folders)
```bash
python utils/prepare_dataset.py
```
This creates `dataset_unified/` with remapped class IDs.

### Step 3 — Train the model (optional but recommended)
```bash
python utils/train_model.py
```
Training takes ~30–60 min on CPU (faster on GPU).  
Trained weights saved to `models/fitness_pose/weights/best.pt`.

> If you skip training, the app uses the base `yolov8n-pose.pt` weights
> (detects "person" only — exercise classification requires training).

### Step 4 — Start the backend
```bash
uvicorn backend.main:app --reload --port 8000
```

### Step 5 — Open the frontend
Open `frontend/index.html` in your browser, or navigate to:
```
http://localhost:8000/static/index.html
```

## API Endpoints

| Method | Endpoint              | Description                          |
|--------|-----------------------|--------------------------------------|
| POST   | /upload-image         | Detect exercise + analyse posture    |
| POST   | /upload-video         | Frame-by-frame video analysis        |
| POST   | /detect-exercise      | YOLO detection only                  |
| POST   | /get-recommendation   | Personalised workout plan            |
| GET    | /history              | Past workout sessions                |
| GET    | /health               | Server health check                  |
| GET    | /docs                 | Auto-generated Swagger UI            |

## Features

- YOLOv8-pose exercise detection (trained on your dataset)
- MediaPipe 33-keypoint posture analysis
- Rule-based posture checks per exercise (deadlift, squat, lateral raise)
- Personalised workout plans (beginner / intermediate / advanced)
- BMI-aware recommendations
- SQLite session history
- Voice feedback via pyttsx3 (offline TTS)
- Clean dark-theme React-style frontend
