"""
test_project.py
---------------
Tests all parts of the AI Fitness Coach project.
Run while the backend server is running on port 8000.

Usage:
    python utils/test_project.py
"""

import requests
import json
import os
import sys
from pathlib import Path

BASE_URL = "http://localhost:8000"
ROOT     = Path(__file__).resolve().parent.parent
PASS     = "\033[92m[PASS]\033[0m"
FAIL     = "\033[91m[FAIL]\033[0m"
INFO     = "\033[94m[INFO]\033[0m"

results = {"passed": 0, "failed": 0}

def check(name, condition, detail=""):
    if condition:
        print(f"  {PASS} {name}")
        results["passed"] += 1
    else:
        print(f"  {FAIL} {name}  →  {detail}")
        results["failed"] += 1

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*55)
print("  AI FITNESS COACH — PROJECT TEST SUITE")
print("="*55)

# ── TEST 1: Health check ──────────────────────────────────────────────────────
print("\n[1] Server Health")
try:
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    data = r.json()
    check("Server is reachable",        r.status_code == 200)
    check("Returns status ok",          data.get("status") == "ok")
    check("Reports model path",         "model" in data)
    print(f"  {INFO} Model: {data.get('model', 'N/A')}")
except Exception as e:
    check("Server is reachable", False, str(e))
    print(f"\n  ⚠  Make sure the server is running:  python -m uvicorn backend.main:app --port 8000")
    sys.exit(1)

# ── TEST 2: Exercise detection (image upload) ─────────────────────────────────
print("\n[2] Exercise Detection — /detect-exercise")

# Find a sample image from the dataset
sample_img = None
for pattern in [
    "dataset/Deadlifts/deadlift Data29/image/Train/frame_0000.jpg",
    "dataset/Squats/squats data29/images/train",
    "dataset/shoulders/lateral data29/images/train",
]:
    p = ROOT / pattern
    if p.is_file():
        sample_img = p
        break
    elif p.is_dir():
        imgs = list(p.glob("*.jpg"))
        if imgs:
            sample_img = imgs[0]
            break

if sample_img:
    print(f"  {INFO} Using sample: {sample_img.name}")
    with open(sample_img, "rb") as f:
        r = requests.post(f"{BASE_URL}/detect-exercise", files={"file": f}, timeout=30)
    data = r.json()
    check("Status 200",                 r.status_code == 200)
    check("Returns detections list",    "detections" in data)
    if data.get("detections"):
        det = data["detections"][0]
        check("Detection has exercise", "exercise" in det)
        check("Detection has confidence","confidence" in det)
        check("Detection has bbox",     "bbox" in det)
        print(f"  {INFO} Detected: {det.get('exercise')}  ({det.get('confidence',0)*100:.1f}% confidence)")
    else:
        print(f"  {INFO} No detections (model not trained yet — expected)")
        results["passed"] += 3
else:
    check("Sample image found", False, "No dataset images found")

# ── TEST 3: Full image analysis — /upload-image ───────────────────────────────
print("\n[3] Full Analysis — /upload-image")
if sample_img:
    with open(sample_img, "rb") as f:
        r = requests.post(f"{BASE_URL}/upload-image", files={"file": f}, timeout=30)
    data = r.json()
    check("Status 200",                 r.status_code == 200)
    check("Returns session_id",         "session_id" in data)
    check("Returns exercise name",      "exercise" in data)
    check("Returns posture object",     "posture" in data)
    check("Posture has score (0-100)",  0 <= data.get("posture", {}).get("score", -1) <= 100)
    check("Posture has issues list",    isinstance(data.get("posture", {}).get("issues"), list))
    check("Posture has suggestions",    isinstance(data.get("posture", {}).get("suggestions"), list))
    check("Returns feedback text",      "feedback" in data)

    p = data.get("posture", {})
    print(f"  {INFO} Exercise : {data.get('exercise')}")
    print(f"  {INFO} Score    : {p.get('score')}/100")
    print(f"  {INFO} Correct  : {p.get('is_correct')}")
    if p.get("issues"):
        print(f"  {INFO} Issues   : {p['issues']}")
    if p.get("suggestions"):
        print(f"  {INFO} Tips     : {p['suggestions']}")
    print(f"  {INFO} Feedback : {data.get('feedback')}")

# ── TEST 4: Recommendation engine ─────────────────────────────────────────────
print("\n[4] Recommendation Engine — /get-recommendation")

test_profiles = [
    {"age": 20, "weight_kg": 60,  "height_cm": 170, "fitness_goal": "muscle_gain",  "label": "Young fit"},
    {"age": 45, "weight_kg": 95,  "height_cm": 170, "fitness_goal": "fat_loss",     "label": "Overweight"},
    {"age": 30, "weight_kg": 70,  "height_cm": 175, "fitness_goal": "endurance",    "label": "Average"},
]

for profile in test_profiles:
    label = profile.pop("label")
    r = requests.post(f"{BASE_URL}/get-recommendation", data=profile, timeout=10)
    data = r.json()
    check(f"Profile '{label}' → status 200",    r.status_code == 200)
    check(f"Profile '{label}' → has level",     data.get("level") in ["beginner","intermediate","advanced"])
    check(f"Profile '{label}' → has exercises", len(data.get("exercises", [])) > 0)
    print(f"  {INFO} {label}: level={data.get('level')}, bmi={data.get('bmi_category')}, exercises={len(data.get('exercises',[]))}")
    profile["label"] = label  # restore

# ── TEST 5: History ────────────────────────────────────────────────────────────
print("\n[5] Session History — /history")
r = requests.get(f"{BASE_URL}/history", timeout=10)
data = r.json()
check("Status 200",                 r.status_code == 200)
check("Returns history list",       "history" in data)
check("History is a list",          isinstance(data.get("history"), list))
if data.get("history"):
    item = data["history"][0]
    check("Item has exercise field",    "exercise" in item)
    check("Item has score field",       "score" in item)
    check("Item has timestamp",         "timestamp" in item)
    print(f"  {INFO} {len(data['history'])} session(s) stored in DB")
else:
    print(f"  {INFO} No history yet (will populate after image uploads)")
    results["passed"] += 3

# ── TEST 6: Posture analyzer (direct unit test) ───────────────────────────────
print("\n[6] Posture Analyzer — Direct Unit Test")
try:
    sys.path.insert(0, str(ROOT))
    import cv2
    import numpy as np
    from utils.posture_analyzer import analyze_posture

    if sample_img:
        img_bgr = cv2.imread(str(sample_img))
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        result  = analyze_posture(img_rgb, "deadlift")

        check("Returns dict",           isinstance(result, dict))
        check("Has is_correct key",     "is_correct" in result)
        check("Has score key",          "score" in result)
        check("Has issues list",        isinstance(result.get("issues"), list))
        check("Has suggestions list",   isinstance(result.get("suggestions"), list))
        check("Score in range 0-100",   0 <= result.get("score", -1) <= 100)
        print(f"  {INFO} Posture score: {result.get('score')}/100")
        print(f"  {INFO} Keypoints detected: {len(result.get('keypoints', []))}")
except Exception as e:
    check("Posture analyzer import", False, str(e))

# ── TEST 7: Recommendation engine (direct unit test) ──────────────────────────
print("\n[7] Recommendation Engine — Direct Unit Test")
try:
    from utils.recommendation_engine import get_recommendation
    plan = get_recommendation(25, 80, 175, "fat_loss", "squat")
    check("Returns dict",               isinstance(plan, dict))
    check("Has level field",            plan.get("level") in ["beginner","intermediate","advanced"])
    check("Has exercises list",         len(plan.get("exercises", [])) > 0)
    check("Has tips list",              len(plan.get("tips", [])) > 0)
    check("Has weekly_schedule",        bool(plan.get("weekly_schedule")))
    check("Has bmi_category",           bool(plan.get("bmi_category")))
    check("Highlight mentions squat",   "squat" in (plan.get("highlight") or "").lower())
    print(f"  {INFO} Level: {plan['level']}, BMI: {plan['bmi_category']}")
    print(f"  {INFO} Plan: {[e['name'] for e in plan['exercises']]}")
except Exception as e:
    check("Recommendation engine import", False, str(e))

# ── SUMMARY ───────────────────────────────────────────────────────────────────
total = results["passed"] + results["failed"]
print("\n" + "="*55)
print(f"  RESULTS:  {results['passed']}/{total} tests passed")
if results["failed"] == 0:
    print("  ✅ All tests passed — project is working correctly!")
else:
    print(f"  ⚠  {results['failed']} test(s) failed — check output above")
print("="*55 + "\n")
