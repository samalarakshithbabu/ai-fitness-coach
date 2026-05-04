"""
posture_analyzer.py
-------------------
Uses MediaPipe Pose Landmarker (Tasks API — compatible with mediapipe >= 0.10.x)
to extract 33 body landmarks and applies rule-based posture checks per exercise.

Returns:
    {
        "is_correct": bool,
        "score": int (0-100),
        "issues": [str],
        "suggestions": [str],
        "keypoints": [{"x":..,"y":..,"z":..,"visibility":..}]
    }
"""

import math
import urllib.request
from pathlib import Path

import numpy as np

# ── MediaPipe Tasks API ───────────────────────────────────────────────────────
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.components.containers import landmark as mp_landmark

# Download the pose landmarker model if not present
MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "pose_landmarker_lite.task"

def _ensure_model():
    if not MODEL_PATH.exists():
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
        print(f"[INFO] Downloading MediaPipe pose model to {MODEL_PATH} …")
        urllib.request.urlretrieve(url, MODEL_PATH)
        print("[INFO] Model downloaded.")

_ensure_model()

# Build the landmarker once as a module-level singleton (avoids ~300ms overhead per call)
_base_options  = mp_python.BaseOptions(model_asset_path=str(MODEL_PATH))
_landmarker_options = mp_vision.PoseLandmarkerOptions(
    base_options=_base_options,
    output_segmentation_masks=False,
    num_poses=1,
    min_pose_detection_confidence=0.5,
    min_pose_presence_confidence=0.5,
    min_tracking_confidence=0.5,
)
_landmarker = mp_vision.PoseLandmarker.create_from_options(_landmarker_options)


# ── helpers ───────────────────────────────────────────────────────────────────

def _angle(a, b, c) -> float:
    """Return angle at point b formed by a-b-c (degrees)."""
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba = a - b
    bc = c - b
    cos = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    return math.degrees(math.acos(np.clip(cos, -1.0, 1.0)))


# MediaPipe Pose landmark indices (same as legacy PoseLandmark enum)
class LM:
    NOSE            = 0
    LEFT_SHOULDER   = 11
    RIGHT_SHOULDER  = 12
    LEFT_ELBOW      = 13
    RIGHT_ELBOW     = 14
    LEFT_WRIST      = 15
    RIGHT_WRIST     = 16
    LEFT_HIP        = 23
    RIGHT_HIP       = 24
    LEFT_KNEE       = 25
    RIGHT_KNEE      = 26
    LEFT_ANKLE      = 27
    RIGHT_ANKLE     = 28


def _xy(landmarks, idx):
    lm = landmarks[idx]
    return (lm.x, lm.y)


def _xyz(landmarks, idx):
    lm = landmarks[idx]
    return (lm.x, lm.y, lm.z)


def _vis(landmarks, idx) -> float:
    return landmarks[idx].visibility


def _avg(a, b):
    """Average two (x, y) or (x, y, z) points."""
    return tuple((a[i] + b[i]) / 2 for i in range(len(a)))


def _bilateral_xy(lm, l_idx, r_idx, vis_threshold=0.4):
    """
    Return the best available landmark between left/right sides.
    Prefers the side with higher visibility; falls back to averaging
    when both are visible, or to whichever side is visible.
    """
    l_vis = _vis(lm, l_idx)
    r_vis = _vis(lm, r_idx)
    l_pt  = _xy(lm, l_idx)
    r_pt  = _xy(lm, r_idx)

    both_visible = l_vis >= vis_threshold and r_vis >= vis_threshold
    if both_visible:
        return _avg(l_pt, r_pt)
    if l_vis >= vis_threshold:
        return l_pt
    if r_vis >= vis_threshold:
        return r_pt
    # Neither clearly visible — average anyway
    return _avg(l_pt, r_pt)


# ── per-exercise rule sets ────────────────────────────────────────────────────

def _check_deadlift(lm):
    """
    Conventional deadlift checks (bilateral, with spine angle).
    Issues are weighted: critical = 30pts, major = 20pts, minor = 10pts.
    """
    issues, suggestions, penalty = [], [], 0

    shoulder = _bilateral_xy(lm, LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER)
    hip      = _bilateral_xy(lm, LM.LEFT_HIP,      LM.RIGHT_HIP)
    l_knee   = _xy(lm, LM.LEFT_KNEE)
    r_knee   = _xy(lm, LM.RIGHT_KNEE)
    l_ankle  = _xy(lm, LM.LEFT_ANKLE)
    r_ankle  = _xy(lm, LM.RIGHT_ANKLE)
    knee     = _avg(l_knee, r_knee)
    ankle    = _avg(l_ankle, r_ankle)

    # 1. Hip hinge angle (shoulder–hip–knee) — critical
    hip_angle = _angle(shoulder, hip, knee)
    if hip_angle < 60:
        issues.append("Back severely rounded — hips too high")
        suggestions.append("Hinge at the hips, push them back, and keep your chest tall")
        penalty += 30
    elif hip_angle < 80:
        issues.append("Back slightly rounded / hips too high")
        suggestions.append("Push hips back further and keep chest up during the lift")
        penalty += 20

    # 2. Spine angle — shoulder-to-hip vertical alignment (major)
    #    In a good deadlift the torso is inclined; we check the hip isn't
    #    excessively forward of the shoulder (bar drifting away).
    spine_lean = shoulder[0] - hip[0]   # positive = shoulder ahead of hip
    if spine_lean > 0.18:
        issues.append("Hips shooting back too fast — losing bar path")
        suggestions.append("Keep hips and shoulders rising at the same rate off the floor")
        penalty += 20
    elif spine_lean < -0.18:
        issues.append("Shoulders too far behind hips — squat-style pull")
        suggestions.append("Lean torso forward slightly and keep the bar over mid-foot")
        penalty += 20

    # 3. Knee drift — bilateral average (major)
    knee_drift = abs(knee[0] - ankle[0])
    if knee_drift > 0.12:
        issues.append("Knees drifting forward past toes")
        suggestions.append("Keep shins vertical and drive through your heels")
        penalty += 20

    # 4. Shoulder symmetry — uneven shoulders indicate rotation (minor)
    l_sh = _xy(lm, LM.LEFT_SHOULDER)
    r_sh = _xy(lm, LM.RIGHT_SHOULDER)
    if abs(l_sh[1] - r_sh[1]) > 0.06:
        issues.append("Shoulders uneven — torso rotating")
        suggestions.append("Keep both shoulders square and level throughout the lift")
        penalty += 10

    return issues, suggestions, penalty


def _check_sumo_deadlift(lm):
    """
    Sumo deadlift — wider stance, more upright torso, knees track over toes.
    """
    issues, suggestions, penalty = [], [], 0

    shoulder = _bilateral_xy(lm, LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER)
    hip      = _bilateral_xy(lm, LM.LEFT_HIP,      LM.RIGHT_HIP)
    l_knee   = _xy(lm, LM.LEFT_KNEE)
    r_knee   = _xy(lm, LM.RIGHT_KNEE)
    l_ankle  = _xy(lm, LM.LEFT_ANKLE)
    r_ankle  = _xy(lm, LM.RIGHT_ANKLE)
    knee     = _avg(l_knee, r_knee)

    # 1. Torso upright — sumo should be more vertical than conventional
    hip_angle = _angle(shoulder, hip, knee)
    if hip_angle < 55:
        issues.append("Torso too horizontal for sumo — back rounding")
        suggestions.append("Stay more upright; sumo requires a more vertical torso")
        penalty += 30
    elif hip_angle < 70:
        issues.append("Torso slightly too horizontal")
        suggestions.append("Keep chest up and torso more vertical for sumo stance")
        penalty += 15

    # 2. Knee tracking — each knee should be over its own ankle (not caving in)
    l_cave = l_knee[0] - l_ankle[0]   # left knee should be ≥ left ankle x
    r_cave = r_ankle[0] - r_knee[0]   # right knee should be ≤ right ankle x
    if l_cave < -0.08:
        issues.append("Left knee caving inward")
        suggestions.append("Push left knee out in line with your left toes")
        penalty += 20
    if r_cave < -0.08:
        issues.append("Right knee caving inward")
        suggestions.append("Push right knee out in line with your right toes")
        penalty += 20

    # 3. Hip width — sumo stance should show wide hip spread
    hip_width  = abs(_xy(lm, LM.LEFT_HIP)[0]   - _xy(lm, LM.RIGHT_HIP)[0])
    ankle_width = abs(l_ankle[0] - r_ankle[0])
    if ankle_width < hip_width * 0.8:
        issues.append("Stance too narrow for sumo deadlift")
        suggestions.append("Widen your stance so feet are outside shoulder width")
        penalty += 15

    # 4. Shoulder symmetry
    l_sh = _xy(lm, LM.LEFT_SHOULDER)
    r_sh = _xy(lm, LM.RIGHT_SHOULDER)
    if abs(l_sh[1] - r_sh[1]) > 0.06:
        issues.append("Shoulders uneven — torso rotating")
        suggestions.append("Keep both shoulders square and level")
        penalty += 10

    return issues, suggestions, penalty


def _check_romanian_deadlift(lm):
    """
    Romanian deadlift — hip hinge with soft knees, back flat, bar close to legs.
    """
    issues, suggestions, penalty = [], [], 0

    shoulder = _bilateral_xy(lm, LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER)
    hip      = _bilateral_xy(lm, LM.LEFT_HIP,      LM.RIGHT_HIP)
    l_knee   = _xy(lm, LM.LEFT_KNEE)
    r_knee   = _xy(lm, LM.RIGHT_KNEE)
    l_ankle  = _xy(lm, LM.LEFT_ANKLE)
    r_ankle  = _xy(lm, LM.RIGHT_ANKLE)
    knee     = _avg(l_knee, r_knee)
    ankle    = _avg(l_ankle, r_ankle)

    # 1. Hip hinge — RDL should show a strong hip hinge (torso forward)
    hip_angle = _angle(shoulder, hip, knee)
    if hip_angle < 50:
        issues.append("Back severely rounded during RDL")
        suggestions.append("Keep back flat; hinge at hips not the lower back")
        penalty += 30
    elif hip_angle < 70:
        issues.append("Back slightly rounded — losing neutral spine")
        suggestions.append("Engage lats, keep chest up, and push hips back")
        penalty += 20

    # 2. Knee bend — RDL uses soft knees, not locked out and not squatting
    knee_angle = _angle(hip, knee, ankle)
    if knee_angle > 170:
        issues.append("Knees fully locked out — risk of hamstring strain")
        suggestions.append("Maintain a soft bend in the knees throughout the RDL")
        penalty += 15
    elif knee_angle < 130:
        issues.append("Knees bending too much — turning into a deadlift")
        suggestions.append("Keep knees only slightly bent; this is a hip hinge movement")
        penalty += 15

    # 3. Bar path — shoulders should stay over or slightly ahead of ankles
    bar_drift = abs(shoulder[0] - ankle[0])
    if bar_drift > 0.20:
        issues.append("Bar drifting away from body")
        suggestions.append("Keep the bar close to your legs throughout the movement")
        penalty += 20

    # 4. Shoulder symmetry
    l_sh = _xy(lm, LM.LEFT_SHOULDER)
    r_sh = _xy(lm, LM.RIGHT_SHOULDER)
    if abs(l_sh[1] - r_sh[1]) > 0.06:
        issues.append("Shoulders uneven — torso rotating")
        suggestions.append("Keep both shoulders square and level")
        penalty += 10

    return issues, suggestions, penalty


def _check_squat(lm, variant="squat"):
    issues, suggestions, penalty = [], [], 0

    hip    = _bilateral_xy(lm, LM.LEFT_HIP,   LM.RIGHT_HIP)
    l_knee  = _xy(lm, LM.LEFT_KNEE)
    r_knee  = _xy(lm, LM.RIGHT_KNEE)
    l_ankle = _xy(lm, LM.LEFT_ANKLE)
    r_ankle = _xy(lm, LM.RIGHT_ANKLE)
    knee    = _avg(l_knee, r_knee)
    ankle   = _avg(l_ankle, r_ankle)

    knee_angle = _angle(hip, knee, ankle)
    if knee_angle > 120:
        issues.append("Squat depth too shallow")
        suggestions.append("Lower until thighs are parallel to the floor")
        penalty += 20
    elif knee_angle > 110:
        issues.append("Squat slightly shallow")
        suggestions.append("Try to go a little deeper — aim for parallel")
        penalty += 10

    knee_width  = abs(l_knee[0] - r_knee[0])
    ankle_width = abs(l_ankle[0] - r_ankle[0])
    if knee_width < ankle_width * 0.75:
        issues.append("Knees caving inward (valgus collapse)")
        suggestions.append("Push knees out in line with toes throughout the movement")
        penalty += 25

    # Torso lean — front/zercher squats require a more upright torso
    shoulder = _bilateral_xy(lm, LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER)
    torso_lean = abs(shoulder[0] - hip[0])
    lean_threshold = 0.10 if variant in ("front_squat", "zercher_squat") else 0.15
    if torso_lean > lean_threshold:
        issues.append("Excessive forward lean")
        if variant in ("front_squat", "zercher_squat"):
            suggestions.append("Keep torso very upright — this squat variant demands a vertical back")
        else:
            suggestions.append("Keep chest up and torso more upright")
        penalty += 15

    return issues, suggestions, penalty


def _check_lateral_raise(lm):
    issues, suggestions, penalty = [], [], 0

    shoulder = _bilateral_xy(lm, LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER)
    l_elbow  = _xy(lm, LM.LEFT_ELBOW)
    r_elbow  = _xy(lm, LM.RIGHT_ELBOW)
    l_wrist  = _xy(lm, LM.LEFT_WRIST)
    r_wrist  = _xy(lm, LM.RIGHT_WRIST)
    hip      = _bilateral_xy(lm, LM.LEFT_HIP, LM.RIGHT_HIP)

    # Use the more visible arm
    l_vis = _vis(lm, LM.LEFT_ELBOW)
    r_vis = _vis(lm, LM.RIGHT_ELBOW)
    elbow = _xy(lm, LM.LEFT_ELBOW) if l_vis >= r_vis else _xy(lm, LM.RIGHT_ELBOW)
    wrist = _xy(lm, LM.LEFT_WRIST) if l_vis >= r_vis else _xy(lm, LM.RIGHT_WRIST)

    arm_angle   = _angle(hip, shoulder, elbow)
    elbow_angle = _angle(shoulder, elbow, wrist)

    if arm_angle < 55:
        issues.append("Arms not raised high enough")
        suggestions.append("Raise arms until parallel to the floor (90°)")
        penalty += 20
    elif arm_angle < 70:
        issues.append("Arms slightly low")
        suggestions.append("Raise arms a little higher — aim for shoulder height")
        penalty += 10

    if elbow_angle > 170:
        issues.append("Elbows fully locked out")
        suggestions.append("Keep a slight bend in the elbows to protect joints")
        penalty += 15

    # Shrugging — shoulders rising toward ears
    l_sh = _xy(lm, LM.LEFT_SHOULDER)
    r_sh = _xy(lm, LM.RIGHT_SHOULDER)
    nose = _xy(lm, LM.NOSE)
    avg_sh_y = (l_sh[1] + r_sh[1]) / 2
    if abs(avg_sh_y - nose[1]) < 0.12:
        issues.append("Shrugging shoulders during raise")
        suggestions.append("Depress your shoulders away from your ears")
        penalty += 10

    return issues, suggestions, penalty


def _check_generic(lm):
    issues, suggestions, penalty = [], [], 0
    l_shoulder = _xy(lm, LM.LEFT_SHOULDER)
    r_shoulder = _xy(lm, LM.RIGHT_SHOULDER)
    l_hip      = _xy(lm, LM.LEFT_HIP)
    r_hip      = _xy(lm, LM.RIGHT_HIP)

    if abs(l_shoulder[1] - r_shoulder[1]) > 0.05:
        issues.append("Shoulders are uneven")
        suggestions.append("Keep shoulders level and square")
        penalty += 15
    if abs(l_hip[1] - r_hip[1]) > 0.05:
        issues.append("Hips are tilted")
        suggestions.append("Engage core and keep hips level")
        penalty += 15

    return issues, suggestions, penalty


def _check_bench_press(lm):
    """Bench press — person lying horizontal, arms pushing up."""
    issues, suggestions, penalty = [], [], 0

    l_shoulder = _xy(lm, LM.LEFT_SHOULDER)
    r_shoulder = _xy(lm, LM.RIGHT_SHOULDER)
    l_elbow    = _xy(lm, LM.LEFT_ELBOW)
    r_elbow    = _xy(lm, LM.RIGHT_ELBOW)
    l_wrist    = _xy(lm, LM.LEFT_WRIST)
    r_wrist    = _xy(lm, LM.RIGHT_WRIST)

    # Elbow flare — elbows should not be wider than wrists
    elbow_span  = abs(l_elbow[0] - r_elbow[0])
    wrist_span  = abs(l_wrist[0] - r_wrist[0])
    if elbow_span > wrist_span * 1.4:
        issues.append("Elbows flaring too wide")
        suggestions.append("Tuck elbows slightly (45–75°) to protect shoulders")
        penalty += 20

    # Shoulder symmetry
    if abs(l_shoulder[1] - r_shoulder[1]) > 0.06:
        issues.append("Shoulders uneven — possible arch imbalance")
        suggestions.append("Keep both shoulders pressed evenly into the bench")
        penalty += 15

    return issues, suggestions, penalty


def _check_incline_bench_press(lm):
    return _check_bench_press(lm)


def _check_decline_bench_press(lm):
    return _check_bench_press(lm)


def _check_barbell_biceps_curl(lm):
    """Biceps curl — elbows stay at sides, full range of motion."""
    issues, suggestions, penalty = [], [], 0

    l_shoulder = _xy(lm, LM.LEFT_SHOULDER)
    r_shoulder = _xy(lm, LM.RIGHT_SHOULDER)
    l_elbow    = _xy(lm, LM.LEFT_ELBOW)
    r_elbow    = _xy(lm, LM.RIGHT_ELBOW)
    l_wrist    = _xy(lm, LM.LEFT_WRIST)
    r_wrist    = _xy(lm, LM.RIGHT_WRIST)
    l_hip      = _xy(lm, LM.LEFT_HIP)
    r_hip      = _xy(lm, LM.RIGHT_HIP)

    avg_shoulder_x = (l_shoulder[0] + r_shoulder[0]) / 2
    avg_elbow_x    = (l_elbow[0]    + r_elbow[0])    / 2

    # Elbow drift forward (swinging)
    elbow_forward = avg_shoulder_x - avg_elbow_x  # positive = elbow behind shoulder
    if abs(elbow_forward) > 0.12:
        issues.append("Elbows drifting forward — using momentum")
        suggestions.append("Keep elbows pinned at your sides throughout the curl")
        penalty += 20

    # Shoulder symmetry
    if abs(l_shoulder[1] - r_shoulder[1]) > 0.05:
        issues.append("Shoulders uneven — one side working harder")
        suggestions.append("Keep both shoulders level and relaxed")
        penalty += 10

    # Hip sway check
    if abs(l_hip[1] - r_hip[1]) > 0.06:
        issues.append("Hips tilting — using body swing")
        suggestions.append("Brace your core and keep hips still")
        penalty += 15

    return issues, suggestions, penalty


def _check_hammer_curl(lm):
    return _check_barbell_biceps_curl(lm)


def _check_shoulder_press(lm):
    """Overhead press — wrists above elbows, core braced."""
    issues, suggestions, penalty = [], [], 0

    l_shoulder = _xy(lm, LM.LEFT_SHOULDER)
    r_shoulder = _xy(lm, LM.RIGHT_SHOULDER)
    l_elbow    = _xy(lm, LM.LEFT_ELBOW)
    r_elbow    = _xy(lm, LM.RIGHT_ELBOW)
    l_wrist    = _xy(lm, LM.LEFT_WRIST)
    r_wrist    = _xy(lm, LM.RIGHT_WRIST)
    l_hip      = _xy(lm, LM.LEFT_HIP)
    r_hip      = _xy(lm, LM.RIGHT_HIP)

    avg_wrist_y    = (l_wrist[1]    + r_wrist[1])    / 2
    avg_elbow_y    = (l_elbow[1]    + r_elbow[1])    / 2
    avg_shoulder_y = (l_shoulder[1] + r_shoulder[1]) / 2

    # Wrists should be above elbows at top of press
    if avg_wrist_y > avg_elbow_y + 0.05:
        issues.append("Wrists dropping below elbows — incomplete press")
        suggestions.append("Press fully overhead until arms are straight")
        penalty += 20

    # Elbow flare at start position
    elbow_span    = abs(l_elbow[0] - r_elbow[0])
    shoulder_span = abs(l_shoulder[0] - r_shoulder[0]) + 1e-6
    if elbow_span > shoulder_span * 1.5:
        issues.append("Elbows flaring too wide")
        suggestions.append("Keep elbows slightly in front of the bar at the start")
        penalty += 15

    # Shoulder symmetry
    if abs(l_shoulder[1] - r_shoulder[1]) > 0.05:
        issues.append("Shoulders uneven")
        suggestions.append("Press evenly with both arms")
        penalty += 10

    return issues, suggestions, penalty


def _check_lat_pulldown(lm):
    """Lat pulldown — pull bar to upper chest, lean back slightly."""
    issues, suggestions, penalty = [], [], 0

    l_shoulder = _xy(lm, LM.LEFT_SHOULDER)
    r_shoulder = _xy(lm, LM.RIGHT_SHOULDER)
    l_elbow    = _xy(lm, LM.LEFT_ELBOW)
    r_elbow    = _xy(lm, LM.RIGHT_ELBOW)
    l_wrist    = _xy(lm, LM.LEFT_WRIST)
    r_wrist    = _xy(lm, LM.RIGHT_WRIST)

    avg_elbow_y    = (l_elbow[1]    + r_elbow[1])    / 2
    avg_shoulder_y = (l_shoulder[1] + r_shoulder[1]) / 2
    avg_wrist_y    = (l_wrist[1]    + r_wrist[1])    / 2

    # Elbows should come down below shoulder level at bottom
    if avg_elbow_y < avg_shoulder_y - 0.05:
        issues.append("Not pulling bar down far enough")
        suggestions.append("Pull the bar to your upper chest, driving elbows down")
        penalty += 20

    # Shoulder symmetry
    if abs(l_shoulder[1] - r_shoulder[1]) > 0.05:
        issues.append("Pulling unevenly — one side dominant")
        suggestions.append("Focus on pulling equally with both arms")
        penalty += 15

    return issues, suggestions, penalty


def _check_pull_up(lm):
    """Pull-up — chin above bar, full hang at bottom."""
    issues, suggestions, penalty = [], [], 0

    l_shoulder = _xy(lm, LM.LEFT_SHOULDER)
    r_shoulder = _xy(lm, LM.RIGHT_SHOULDER)
    l_elbow    = _xy(lm, LM.LEFT_ELBOW)
    r_elbow    = _xy(lm, LM.RIGHT_ELBOW)
    nose       = _xy(lm, LM.NOSE)

    avg_wrist_y    = (_xy(lm, LM.LEFT_WRIST)[1] + _xy(lm, LM.RIGHT_WRIST)[1]) / 2
    avg_shoulder_y = (l_shoulder[1] + r_shoulder[1]) / 2

    # Shoulder symmetry
    if abs(l_shoulder[1] - r_shoulder[1]) > 0.06:
        issues.append("Shoulders uneven — body swinging")
        suggestions.append("Keep core tight and pull straight up without swinging")
        penalty += 20

    # Elbow symmetry
    if abs(l_elbow[1] - r_elbow[1]) > 0.08:
        issues.append("Uneven elbow bend — one arm doing more work")
        suggestions.append("Focus on pulling evenly with both arms")
        penalty += 15

    return issues, suggestions, penalty


def _check_push_up(lm):
    """Push-up — body straight, elbows at ~45°."""
    issues, suggestions, penalty = [], [], 0

    l_shoulder = _xy(lm, LM.LEFT_SHOULDER)
    r_shoulder = _xy(lm, LM.RIGHT_SHOULDER)
    l_hip      = _xy(lm, LM.LEFT_HIP)
    r_hip      = _xy(lm, LM.RIGHT_HIP)
    l_elbow    = _xy(lm, LM.LEFT_ELBOW)
    r_elbow    = _xy(lm, LM.RIGHT_ELBOW)
    l_ankle    = _xy(lm, LM.LEFT_ANKLE)
    r_ankle    = _xy(lm, LM.RIGHT_ANKLE)

    avg_shoulder_y = (l_shoulder[1] + r_shoulder[1]) / 2
    avg_hip_y      = (l_hip[1]      + r_hip[1])      / 2
    avg_ankle_y    = (l_ankle[1]    + r_ankle[1])    / 2

    # Hips sagging or piking
    body_line = avg_ankle_y - avg_shoulder_y
    hip_deviation = avg_hip_y - (avg_shoulder_y + body_line * 0.5)
    if hip_deviation > 0.08:
        issues.append("Hips sagging — lower back arching")
        suggestions.append("Squeeze glutes and brace core to keep body in a straight line")
        penalty += 25
    elif hip_deviation < -0.08:
        issues.append("Hips piking up")
        suggestions.append("Lower hips to form a straight line from head to heels")
        penalty += 20

    # Elbow flare
    elbow_span    = abs(l_elbow[0] - r_elbow[0])
    shoulder_span = abs(l_shoulder[0] - r_shoulder[0]) + 1e-6
    if elbow_span > shoulder_span * 1.6:
        issues.append("Elbows flaring too wide")
        suggestions.append("Keep elbows at 45° from your torso")
        penalty += 15

    return issues, suggestions, penalty


def _check_leg_extension(lm):
    """Leg extension — seated, full knee extension."""
    issues, suggestions, penalty = [], [], 0

    l_shoulder = _xy(lm, LM.LEFT_SHOULDER)
    r_shoulder = _xy(lm, LM.RIGHT_SHOULDER)
    l_hip      = _xy(lm, LM.LEFT_HIP)
    r_hip      = _xy(lm, LM.RIGHT_HIP)

    # Shoulder symmetry
    if abs(l_shoulder[1] - r_shoulder[1]) > 0.05:
        issues.append("Leaning to one side")
        suggestions.append("Sit upright and keep both shoulders level")
        penalty += 15

    # Hip symmetry
    if abs(l_hip[1] - r_hip[1]) > 0.05:
        issues.append("Hips shifting — using momentum")
        suggestions.append("Keep hips firmly on the seat throughout the movement")
        penalty += 15

    return issues, suggestions, penalty


def _check_leg_raises(lm):
    """Leg raises — core engaged, controlled movement."""
    issues, suggestions, penalty = [], [], 0

    l_shoulder = _xy(lm, LM.LEFT_SHOULDER)
    r_shoulder = _xy(lm, LM.RIGHT_SHOULDER)
    l_hip      = _xy(lm, LM.LEFT_HIP)
    r_hip      = _xy(lm, LM.RIGHT_HIP)

    # Hip symmetry
    if abs(l_hip[1] - r_hip[1]) > 0.06:
        issues.append("Hips rotating — uneven leg raise")
        suggestions.append("Keep hips flat and raise both legs together")
        penalty += 20

    # Shoulder symmetry
    if abs(l_shoulder[1] - r_shoulder[1]) > 0.05:
        issues.append("Upper body twisting")
        suggestions.append("Keep shoulders flat and arms steady")
        penalty += 15

    return issues, suggestions, penalty


def _check_hip_thrust(lm):
    """Hip thrust — full hip extension at top."""
    issues, suggestions, penalty = [], [], 0

    l_shoulder = _xy(lm, LM.LEFT_SHOULDER)
    r_shoulder = _xy(lm, LM.RIGHT_SHOULDER)
    l_hip      = _xy(lm, LM.LEFT_HIP)
    r_hip      = _xy(lm, LM.RIGHT_HIP)
    l_knee     = _xy(lm, LM.LEFT_KNEE)
    r_knee     = _xy(lm, LM.RIGHT_KNEE)

    avg_hip_y      = (l_hip[1]      + r_hip[1])      / 2
    avg_shoulder_y = (l_shoulder[1] + r_shoulder[1]) / 2
    avg_knee_y     = (l_knee[1]     + r_knee[1])     / 2

    # At top: hip should be roughly level with shoulder and knee
    hip_extension = abs(avg_hip_y - avg_shoulder_y)
    if hip_extension > 0.15:
        issues.append("Not reaching full hip extension at the top")
        suggestions.append("Drive hips up until your body forms a straight line from shoulders to knees")
        penalty += 25

    # Hip symmetry
    if abs(l_hip[1] - r_hip[1]) > 0.06:
        issues.append("Hips tilting to one side")
        suggestions.append("Keep hips level throughout the movement")
        penalty += 20

    return issues, suggestions, penalty


def _check_plank(lm):
    """Plank — straight body line, no sagging or piking."""
    issues, suggestions, penalty = [], [], 0

    l_shoulder = _xy(lm, LM.LEFT_SHOULDER)
    r_shoulder = _xy(lm, LM.RIGHT_SHOULDER)
    l_hip      = _xy(lm, LM.LEFT_HIP)
    r_hip      = _xy(lm, LM.RIGHT_HIP)
    l_ankle    = _xy(lm, LM.LEFT_ANKLE)
    r_ankle    = _xy(lm, LM.RIGHT_ANKLE)

    avg_shoulder_y = (l_shoulder[1] + r_shoulder[1]) / 2
    avg_hip_y      = (l_hip[1]      + r_hip[1])      / 2
    avg_ankle_y    = (l_ankle[1]    + r_ankle[1])    / 2

    # Body should be roughly horizontal — check hip deviation from shoulder-ankle line
    expected_hip_y = avg_shoulder_y + (avg_ankle_y - avg_shoulder_y) * 0.5
    hip_deviation  = avg_hip_y - expected_hip_y

    if hip_deviation > 0.07:
        issues.append("Hips sagging — lower back arching")
        suggestions.append("Squeeze glutes and brace core to keep body flat")
        penalty += 30
    elif hip_deviation < -0.07:
        issues.append("Hips piking up")
        suggestions.append("Lower hips to form a straight line from head to heels")
        penalty += 20

    # Shoulder symmetry
    if abs(l_shoulder[1] - r_shoulder[1]) > 0.05:
        issues.append("Shoulders uneven — body rotating")
        suggestions.append("Keep both shoulders level and square to the floor")
        penalty += 15

    return issues, suggestions, penalty


def _check_tricep_dips(lm):
    """Tricep dips — elbows tracking back, upright torso."""
    issues, suggestions, penalty = [], [], 0

    l_shoulder = _xy(lm, LM.LEFT_SHOULDER)
    r_shoulder = _xy(lm, LM.RIGHT_SHOULDER)
    l_elbow    = _xy(lm, LM.LEFT_ELBOW)
    r_elbow    = _xy(lm, LM.RIGHT_ELBOW)
    l_hip      = _xy(lm, LM.LEFT_HIP)
    r_hip      = _xy(lm, LM.RIGHT_HIP)

    avg_shoulder_y = (l_shoulder[1] + r_shoulder[1]) / 2
    avg_elbow_y    = (l_elbow[1]    + r_elbow[1])    / 2

    # Elbows should be behind shoulders (not flaring out)
    elbow_span    = abs(l_elbow[0] - r_elbow[0])
    shoulder_span = abs(l_shoulder[0] - r_shoulder[0]) + 1e-6
    if elbow_span > shoulder_span * 1.3:
        issues.append("Elbows flaring outward")
        suggestions.append("Keep elbows pointing straight back, not out to the sides")
        penalty += 20

    # Shoulder symmetry
    if abs(l_shoulder[1] - r_shoulder[1]) > 0.05:
        issues.append("Shoulders uneven")
        suggestions.append("Keep both shoulders level throughout the dip")
        penalty += 15

    return issues, suggestions, penalty


def _check_tricep_pushdown(lm):
    """Tricep pushdown — elbows locked at sides, full extension."""
    issues, suggestions, penalty = [], [], 0

    l_shoulder = _xy(lm, LM.LEFT_SHOULDER)
    r_shoulder = _xy(lm, LM.RIGHT_SHOULDER)
    l_elbow    = _xy(lm, LM.LEFT_ELBOW)
    r_elbow    = _xy(lm, LM.RIGHT_ELBOW)

    avg_shoulder_x = (l_shoulder[0] + r_shoulder[0]) / 2
    avg_elbow_x    = (l_elbow[0]    + r_elbow[0])    / 2

    # Elbows should stay at sides (not drifting forward)
    if abs(avg_elbow_x - avg_shoulder_x) > 0.12:
        issues.append("Elbows drifting away from body")
        suggestions.append("Pin elbows to your sides throughout the movement")
        penalty += 20

    # Shoulder symmetry
    if abs(l_shoulder[1] - r_shoulder[1]) > 0.05:
        issues.append("Shoulders uneven")
        suggestions.append("Keep both shoulders level and relaxed")
        penalty += 10

    return issues, suggestions, penalty


def _check_t_bar_row(lm):
    """T-bar row — neutral spine, elbows driving back."""
    issues, suggestions, penalty = [], [], 0

    l_shoulder = _xy(lm, LM.LEFT_SHOULDER)
    r_shoulder = _xy(lm, LM.RIGHT_SHOULDER)
    l_hip      = _xy(lm, LM.LEFT_HIP)
    r_hip      = _xy(lm, LM.RIGHT_HIP)
    l_knee     = _xy(lm, LM.LEFT_KNEE)
    r_knee     = _xy(lm, LM.RIGHT_KNEE)

    shoulder = _bilateral_xy(lm, LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER)
    hip      = _bilateral_xy(lm, LM.LEFT_HIP,      LM.RIGHT_HIP)
    knee     = _avg(_xy(lm, LM.LEFT_KNEE), _xy(lm, LM.RIGHT_KNEE))

    hip_angle = _angle(shoulder, hip, knee)
    if hip_angle < 40:
        issues.append("Back too rounded — excessive forward lean")
        suggestions.append("Maintain a neutral spine with chest up")
        penalty += 25
    elif hip_angle > 80:
        issues.append("Too upright — not enough hip hinge")
        suggestions.append("Hinge at the hips to about 45° for proper row mechanics")
        penalty += 15

    if abs(l_shoulder[1] - r_shoulder[1]) > 0.05:
        issues.append("Shoulders uneven — rotating during pull")
        suggestions.append("Keep both shoulders square and pull symmetrically")
        penalty += 15

    return issues, suggestions, penalty


def _check_russian_twist(lm):
    """Russian twist — controlled rotation, feet off ground."""
    issues, suggestions, penalty = [], [], 0

    l_shoulder = _xy(lm, LM.LEFT_SHOULDER)
    r_shoulder = _xy(lm, LM.RIGHT_SHOULDER)
    l_hip      = _xy(lm, LM.LEFT_HIP)
    r_hip      = _xy(lm, LM.RIGHT_HIP)

    # Shoulder height difference indicates rotation (expected in this exercise)
    # Only flag if hips are also tilting (losing control)
    if abs(l_hip[1] - r_hip[1]) > 0.08:
        issues.append("Hips rocking — losing core stability")
        suggestions.append("Keep hips stable and rotate only through the torso")
        penalty += 20

    return issues, suggestions, penalty


def _check_chest_fly_machine(lm):
    """Chest fly — arms spread wide, controlled arc."""
    issues, suggestions, penalty = [], [], 0

    l_shoulder = _xy(lm, LM.LEFT_SHOULDER)
    r_shoulder = _xy(lm, LM.RIGHT_SHOULDER)
    l_elbow    = _xy(lm, LM.LEFT_ELBOW)
    r_elbow    = _xy(lm, LM.RIGHT_ELBOW)

    # Shoulder symmetry
    if abs(l_shoulder[1] - r_shoulder[1]) > 0.05:
        issues.append("Shoulders uneven — one side working harder")
        suggestions.append("Keep both shoulders pressed back into the pad evenly")
        penalty += 15

    # Elbow symmetry
    if abs(l_elbow[1] - r_elbow[1]) > 0.07:
        issues.append("Elbows at different heights")
        suggestions.append("Keep both elbows at the same height throughout the movement")
        penalty += 15

    return issues, suggestions, penalty


# ── exercise → checker map ────────────────────────────────────────────────────

EXERCISE_CHECKERS = {
    "deadlift":             _check_deadlift,
    "romanian_deadlift":    _check_romanian_deadlift,
    "sumo_deadlift":        _check_sumo_deadlift,
    "squat":                lambda lm: _check_squat(lm, "squat"),
    "front_squat":          lambda lm: _check_squat(lm, "front_squat"),
    "zercher_squat":        lambda lm: _check_squat(lm, "zercher_squat"),
    "lateral_raise":        _check_lateral_raise,
    "bench_press":          _check_bench_press,
    "incline_bench_press":  _check_incline_bench_press,
    "decline_bench_press":  _check_decline_bench_press,
    "barbell_biceps_curl":  _check_barbell_biceps_curl,
    "hammer_curl":          _check_hammer_curl,
    "shoulder_press":       _check_shoulder_press,
    "lat_pulldown":         _check_lat_pulldown,
    "pull_up":              _check_pull_up,
    "push_up":              _check_push_up,
    "leg_extension":        _check_leg_extension,
    "leg_raises":           _check_leg_raises,
    "hip_thrust":           _check_hip_thrust,
    "plank":                _check_plank,
    "tricep_dips":          _check_tricep_dips,
    "tricep_pushdown":      _check_tricep_pushdown,
    "t_bar_row":            _check_t_bar_row,
    "russian_twist":        _check_russian_twist,
    "chest_fly_machine":    _check_chest_fly_machine,
}


# ── public API ────────────────────────────────────────────────────────────────

# ── pose-based exercise disambiguation ───────────────────────────────────────
# These geometric rules fire AFTER YOLO/classifier to catch the most common
# misclassifications (e.g. chest_fly → deadlift).

def _arm_spread_ratio(landmarks) -> float:
    """
    Returns the ratio of arm spread (wrist-to-wrist width) to shoulder width.
    Chest fly: arms wide → ratio >> 1.0
    Deadlift:  arms close to body → ratio ≈ 0.5–0.8
    """
    l_wrist   = _xy(landmarks, LM.LEFT_WRIST)
    r_wrist   = _xy(landmarks, LM.RIGHT_WRIST)
    l_shoulder = _xy(landmarks, LM.LEFT_SHOULDER)
    r_shoulder = _xy(landmarks, LM.RIGHT_SHOULDER)

    wrist_span    = abs(l_wrist[0] - r_wrist[0])
    shoulder_span = abs(l_shoulder[0] - r_shoulder[0]) + 1e-6
    return wrist_span / shoulder_span


def _elbow_height_relative_to_shoulder(landmarks) -> float:
    """
    Returns average elbow Y relative to shoulder Y (positive = elbow below shoulder).
    Chest fly: elbows roughly at shoulder height → near 0
    Deadlift:  elbows well below shoulders → positive
    """
    l_elbow    = _xy(landmarks, LM.LEFT_ELBOW)
    r_elbow    = _xy(landmarks, LM.RIGHT_ELBOW)
    l_shoulder = _xy(landmarks, LM.LEFT_SHOULDER)
    r_shoulder = _xy(landmarks, LM.RIGHT_SHOULDER)

    avg_elbow_y    = (l_elbow[1] + r_elbow[1]) / 2
    avg_shoulder_y = (l_shoulder[1] + r_shoulder[1]) / 2
    return avg_elbow_y - avg_shoulder_y   # positive = elbow lower than shoulder


def _pose_based_detect(landmarks) -> str | None:
    """
    Purely geometry-driven exercise detector.
    Returns a label if the pose strongly matches a known pattern,
    or None if no strong match found.

    This runs BEFORE YOLO's class label and overrides it when confident.
    Thresholds tuned for real gym footage.
    """
    try:
        arm_spread = _arm_spread_ratio(landmarks)
        elbow_drop = _elbow_height_relative_to_shoulder(landmarks)

        l_shoulder = _xy(landmarks, LM.LEFT_SHOULDER)
        r_shoulder = _xy(landmarks, LM.RIGHT_SHOULDER)
        l_hip      = _xy(landmarks, LM.LEFT_HIP)
        r_hip      = _xy(landmarks, LM.RIGHT_HIP)
        l_wrist    = _xy(landmarks, LM.LEFT_WRIST)
        r_wrist    = _xy(landmarks, LM.RIGHT_WRIST)
        l_elbow    = _xy(landmarks, LM.LEFT_ELBOW)
        r_elbow    = _xy(landmarks, LM.RIGHT_ELBOW)

        avg_shoulder_y = (l_shoulder[1] + r_shoulder[1]) / 2
        avg_hip_y      = (l_hip[1]      + r_hip[1])      / 2
        avg_elbow_y    = (l_elbow[1]    + r_elbow[1])    / 2
        avg_wrist_y    = (l_wrist[1]    + r_wrist[1])    / 2

        # ── CHEST FLY ─────────────────────────────────────────────────────────
        # Signature: arms spread very wide (>1.4x shoulder width),
        #            wrists roughly at shoulder height (not raised above head),
        #            elbows near shoulder height (not dropped to hips)
        wrists_near_shoulder_height = abs(avg_wrist_y - avg_shoulder_y) < 0.25
        elbows_near_shoulder_height = abs(avg_elbow_y - avg_shoulder_y) < 0.20
        if (arm_spread > 1.4
                and wrists_near_shoulder_height
                and elbows_near_shoulder_height):
            return "chest_fly_machine"

        # ── LATERAL RAISE ─────────────────────────────────────────────────────
        # Signature: arms spread wide (1.2–1.8x), wrists ABOVE shoulder level,
        #            person standing upright (hip well below shoulder)
        wrists_above_shoulders = avg_wrist_y < avg_shoulder_y  # y increases downward
        torso_upright = (avg_hip_y - avg_shoulder_y) > 0.15
        if (1.2 < arm_spread < 2.2
                and wrists_above_shoulders
                and torso_upright):
            return "lateral_raise"

        # ── BENCH PRESS ───────────────────────────────────────────────────────
        # Signature: person horizontal (hip Y ≈ shoulder Y),
        #            arms pushing upward (wrists above chest)
        person_horizontal = abs(avg_hip_y - avg_shoulder_y) < 0.10
        if person_horizontal and arm_spread < 1.5:
            return "bench_press"

    except Exception:
        pass

    return None


def disambiguate_exercise(exercise_name: str, landmarks) -> str:
    """
    Two-stage correction:
    1. Run pose-based detector — if it fires with high geometric confidence, use it.
    2. Apply per-class correction rules for known confusion pairs.
    """
    if landmarks is None:
        return exercise_name

    try:
        # Stage 1: pose-based override (catches misclassification regardless of
        # what YOLO predicted)
        pose_label = _pose_based_detect(landmarks)
        if pose_label is not None:
            return pose_label

        # Stage 2: targeted correction rules
        arm_spread = _arm_spread_ratio(landmarks)
        elbow_drop = _elbow_height_relative_to_shoulder(landmarks)

        # deadlift misclassified as chest fly
        if exercise_name == "chest_fly_machine":
            if arm_spread < 1.0 and elbow_drop > 0.10:
                return "deadlift"

        # bench press: person lying horizontal
        if exercise_name == "deadlift":
            hip      = _bilateral_xy(landmarks, LM.LEFT_HIP, LM.RIGHT_HIP)
            shoulder = _bilateral_xy(landmarks, LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER)
            if abs(hip[1] - shoulder[1]) < 0.08:
                return "bench_press"

    except Exception:
        pass

    return exercise_name


def analyze_posture(image_rgb: np.ndarray, exercise_name: str) -> dict:
    """
    Run MediaPipe Pose Landmarker on image_rgb and apply exercise-specific rules.

    Args:
        image_rgb: numpy array (H, W, 3) in RGB
        exercise_name: exercise key string

    Returns:
        dict with keys: is_correct, score, issues, suggestions, keypoints
    """
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)

    result = _landmarker.detect(mp_image)

    if not result.pose_landmarks or len(result.pose_landmarks) == 0:
        return {
            "is_correct": False,
            "score": 0,
            "issues": ["No person detected in image"],
            "suggestions": ["Ensure the full body is visible in the frame"],
            "keypoints": [],
        }

    landmarks = result.pose_landmarks[0]   # first detected pose

    # Apply geometric disambiguation before running the checker
    exercise_name = disambiguate_exercise(exercise_name, landmarks)

    checker   = EXERCISE_CHECKERS.get(exercise_name, _check_generic)
    issues, suggestions, penalty = checker(landmarks)

    score      = max(0, 100 - penalty)
    is_correct = len(issues) == 0

    keypoints = [
        {"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility}
        for lm in landmarks
    ]

    return {
        "is_correct": is_correct,
        "score": score,
        "issues": issues,
        "suggestions": suggestions,
        "keypoints": keypoints,
    }
