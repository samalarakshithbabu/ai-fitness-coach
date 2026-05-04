"""
recommendation_engine.py
------------------------
Rule-based workout recommendation engine.
Takes user profile (age, weight, fitness_goal) and detected exercise,
returns a personalised workout plan.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class WorkoutPlan:
    level: str
    goal: str
    exercises: List[dict]
    tips: List[str]
    weekly_schedule: str


# ── exercise library ──────────────────────────────────────────────────────────

EXERCISE_DB = {
    "fat_loss": {
        "beginner": [
            {"name": "Bodyweight Squats",  "sets": 3, "reps": "15",  "rest": "60s"},
            {"name": "Walking Lunges",     "sets": 3, "reps": "12",  "rest": "60s"},
            {"name": "Jumping Jacks",      "sets": 3, "reps": "30s", "rest": "30s"},
            {"name": "Plank",              "sets": 3, "reps": "20s", "rest": "30s"},
        ],
        "intermediate": [
            {"name": "Goblet Squats",      "sets": 4, "reps": "12",  "rest": "45s"},
            {"name": "Deadlifts",          "sets": 3, "reps": "10",  "rest": "60s"},
            {"name": "Burpees",            "sets": 3, "reps": "10",  "rest": "45s"},
            {"name": "Mountain Climbers",  "sets": 3, "reps": "30s", "rest": "30s"},
        ],
        "advanced": [
            {"name": "Barbell Deadlifts",  "sets": 5, "reps": "8",   "rest": "90s"},
            {"name": "Front Squats",       "sets": 4, "reps": "10",  "rest": "60s"},
            {"name": "Box Jumps",          "sets": 4, "reps": "10",  "rest": "60s"},
            {"name": "Lateral Raises",     "sets": 3, "reps": "15",  "rest": "45s"},
        ],
    },
    "muscle_gain": {
        "beginner": [
            {"name": "Goblet Squats",      "sets": 3, "reps": "10",  "rest": "90s"},
            {"name": "Romanian Deadlift",  "sets": 3, "reps": "10",  "rest": "90s"},
            {"name": "Dumbbell Press",     "sets": 3, "reps": "10",  "rest": "90s"},
            {"name": "Lateral Raises",     "sets": 3, "reps": "12",  "rest": "60s"},
        ],
        "intermediate": [
            {"name": "Barbell Squats",     "sets": 4, "reps": "8",   "rest": "120s"},
            {"name": "Deadlifts",          "sets": 4, "reps": "6",   "rest": "120s"},
            {"name": "Overhead Press",     "sets": 4, "reps": "8",   "rest": "90s"},
            {"name": "Lateral Raises",     "sets": 4, "reps": "12",  "rest": "60s"},
        ],
        "advanced": [
            {"name": "Barbell Deadlifts",  "sets": 5, "reps": "5",   "rest": "180s"},
            {"name": "Zercher Squats",     "sets": 4, "reps": "6",   "rest": "150s"},
            {"name": "Front Squats",       "sets": 4, "reps": "6",   "rest": "150s"},
            {"name": "Arnold Press",       "sets": 4, "reps": "10",  "rest": "90s"},
        ],
    },
    "endurance": {
        "beginner": [
            {"name": "Bodyweight Squats",  "sets": 3, "reps": "20",  "rest": "30s"},
            {"name": "Step-ups",           "sets": 3, "reps": "15",  "rest": "30s"},
            {"name": "Arm Circles",        "sets": 3, "reps": "30s", "rest": "15s"},
            {"name": "Plank",              "sets": 3, "reps": "30s", "rest": "30s"},
        ],
        "intermediate": [
            {"name": "Jump Squats",        "sets": 4, "reps": "15",  "rest": "30s"},
            {"name": "Deadlifts",          "sets": 3, "reps": "15",  "rest": "45s"},
            {"name": "Lateral Raises",     "sets": 3, "reps": "20",  "rest": "30s"},
            {"name": "Burpees",            "sets": 4, "reps": "12",  "rest": "30s"},
        ],
        "advanced": [
            {"name": "Barbell Deadlifts",  "sets": 4, "reps": "15",  "rest": "60s"},
            {"name": "Front Squats",       "sets": 4, "reps": "15",  "rest": "60s"},
            {"name": "Lateral Raises",     "sets": 4, "reps": "20",  "rest": "30s"},
            {"name": "Box Jumps",          "sets": 5, "reps": "15",  "rest": "45s"},
        ],
    },
}

SCHEDULES = {
    "beginner":     "3 days/week (Mon, Wed, Fri) — full body each session",
    "intermediate": "4 days/week (Mon, Tue, Thu, Fri) — upper/lower split",
    "advanced":     "5 days/week (Mon–Fri) — push/pull/legs split",
}

TIPS = {
    "fat_loss":    ["Stay in a caloric deficit (~300–500 kcal/day)",
                    "Add 20–30 min cardio after each session",
                    "Drink at least 2.5 L water daily"],
    "muscle_gain": ["Eat in a slight caloric surplus (~200–300 kcal/day)",
                    "Prioritise protein (1.6–2.2 g per kg bodyweight)",
                    "Sleep 7–9 hours for optimal recovery"],
    "endurance":   ["Focus on progressive overload with higher reps",
                    "Include active recovery (yoga, walking) on rest days",
                    "Track heart rate to stay in aerobic zone (60–75% max HR)"],
}


# ── BMI helper ────────────────────────────────────────────────────────────────

def _bmi_category(weight_kg: float, height_cm: float) -> str:
    if height_cm <= 0:
        return "normal"
    bmi = weight_kg / ((height_cm / 100) ** 2)
    if bmi < 18.5:
        return "underweight"
    elif bmi < 25:
        return "normal"
    elif bmi < 30:
        return "overweight"
    else:
        return "obese"


def _fitness_level(age: int, fitness_goal: str, bmi_cat: str) -> str:
    """Assign beginner/intermediate/advanced based on BMI, age, and goal."""
    # Safety first — obese or very old users start at beginner regardless of goal
    if bmi_cat == "obese" or age > 60:
        return "beginner"
    if bmi_cat == "overweight" or age > 50:
        return "beginner" if fitness_goal == "muscle_gain" else "intermediate"
    if fitness_goal == "muscle_gain" and age < 35 and bmi_cat == "normal":
        return "advanced"
    if age < 40 and bmi_cat in ("normal", "underweight"):
        return "intermediate"
    return "beginner"


# ── public API ────────────────────────────────────────────────────────────────

def get_recommendation(
    age: int,
    weight_kg: float,
    height_cm: float,
    fitness_goal: str,          # fat_loss | muscle_gain | endurance
    detected_exercise: str = "",
) -> dict:
    """
    Generate a personalised workout plan.

    Returns a dict suitable for JSON serialisation.
    """
    # Normalise goal
    goal = fitness_goal.lower().replace(" ", "_")
    if goal not in EXERCISE_DB:
        goal = "fat_loss"

    bmi_cat = _bmi_category(weight_kg, height_cm)
    level   = _fitness_level(age, goal, bmi_cat)

    exercises = EXERCISE_DB[goal][level]
    tips      = TIPS[goal]
    schedule  = SCHEDULES[level]

    # If we know which exercise was detected, highlight it in the plan
    highlight = None
    if detected_exercise:
        highlight = f"Great choice! {detected_exercise.replace('_', ' ').title()} is included in your plan."

    return {
        "level":           level,
        "goal":            goal,
        "bmi_category":    bmi_cat,
        "exercises":       exercises,
        "tips":            tips,
        "weekly_schedule": schedule,
        "highlight":       highlight,
    }
