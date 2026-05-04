"""
voice_feedback.py
-----------------
Optional text-to-speech feedback using pyttsx3 (offline, no API key needed).
Falls back silently if pyttsx3 is unavailable.
"""

import threading

try:
    import pyttsx3
    _ENGINE = pyttsx3.init()
    _ENGINE.setProperty("rate", 160)   # words per minute
    _TTS_AVAILABLE = True
except Exception:
    _TTS_AVAILABLE = False


def speak(text: str):
    """Speak text in a background thread so it doesn't block the API."""
    if not _TTS_AVAILABLE:
        return
    def _run():
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 160)
            engine.say(text)
            engine.runAndWait()
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()


def build_feedback_message(exercise: str, posture: dict) -> str:
    """Build a short spoken sentence from posture analysis results."""
    if posture["is_correct"]:
        return f"Great form on your {exercise.replace('_', ' ')}! Keep it up."
    issues = posture.get("issues", [])
    if issues:
        return f"Posture issue detected: {issues[0]}"
    return "Please check your posture and try again."
