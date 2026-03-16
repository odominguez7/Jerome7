"""Session type rotation — 4 day types cycling daily.

The blueprint specifies 4 session types that rotate every 24 hours,
so the entire community does the same type of session each day:
  A: Guided Breathwork (Box Breathing)
  B: Guided Meditation (Focus)
  C: Reflection
  D: Preparation for the Day

Uses a fixed epoch so the rotation is deterministic and globally consistent.
"""

from datetime import date

SESSION_TYPES = ["breathwork", "meditation", "reflection", "preparation"]

# Epoch: March 15, 2026 — first day of the rotation
_EPOCH = date(2026, 3, 15)


def today_session_type(target_date: date | None = None) -> str:
    """Return today's session type based on day rotation."""
    d = target_date or date.today()
    day_offset = (d - _EPOCH).days
    return SESSION_TYPES[day_offset % 4]


# Fallback sessions for each type (used when Gemini is unavailable)
FALLBACK_SESSIONS = {
    "breathwork": {
        "session_type": "breathwork",
        "session_title": "box breath",
        "greeting": "Welcome. Let's breathe.",
        "blocks": [
            {"name": "welcome", "duration_seconds": 30,
             "instruction": "Settle in. Close your eyes if comfortable.",
             "phase": "welcome"},
            {"name": "intention", "duration_seconds": 30,
             "instruction": "Set one intention for this session. Speak it or hold it.",
             "phase": "intention"},
            {"name": "box breath 1", "duration_seconds": 60,
             "instruction": "Inhale 4 counts, hold 4, exhale 4, hold 4. Repeat.",
             "phase": "breathwork"},
            {"name": "box breath 2", "duration_seconds": 60,
             "instruction": "Same rhythm. Inhale 4, hold 4, exhale 4, hold 4.",
             "phase": "breathwork"},
            {"name": "box breath 3", "duration_seconds": 90,
             "instruction": "Deepen the breath. Inhale 4, hold 4, exhale 4, hold 4.",
             "phase": "breathwork"},
            {"name": "box breath 4", "duration_seconds": 60,
             "instruction": "Last round. Let the breath carry you.",
             "phase": "breathwork"},
            {"name": "body scan", "duration_seconds": 60,
             "instruction": "Scan from head to toes. Notice where you hold tension.",
             "phase": "cooldown"},
            {"name": "closing", "duration_seconds": 30,
             "instruction": "You showed up. That's the win.",
             "phase": "closing"},
        ],
        "closing": "You showed up. That's the win.",
    },
    "meditation": {
        "session_type": "meditation",
        "session_title": "still focus",
        "greeting": "Welcome. Let's find stillness.",
        "blocks": [
            {"name": "welcome", "duration_seconds": 30,
             "instruction": "Settle in. Find a comfortable position.",
             "phase": "welcome"},
            {"name": "grounding", "duration_seconds": 30,
             "instruction": "5 things you see, 4 you hear, 3 you feel, 2 you smell, 1 you taste.",
             "phase": "grounding"},
            {"name": "breath awareness", "duration_seconds": 100,
             "instruction": "Follow your natural breath. Don't change it. Just notice.",
             "phase": "meditation"},
            {"name": "focus", "duration_seconds": 100,
             "instruction": "When your mind wanders, gently return to the breath.",
             "phase": "meditation"},
            {"name": "open awareness", "duration_seconds": 100,
             "instruction": "Expand awareness to sounds, sensations. Let everything in.",
             "phase": "meditation"},
            {"name": "gratitude", "duration_seconds": 30,
             "instruction": "Name 3 things you're grateful for right now.",
             "phase": "gratitude"},
            {"name": "closing", "duration_seconds": 30,
             "instruction": "You're not alone. Builders showed up today too.",
             "phase": "closing"},
        ],
        "closing": "Builders showed up today too.",
    },
    "reflection": {
        "session_type": "reflection",
        "session_title": "inner mirror",
        "greeting": "Welcome. Let's reflect.",
        "blocks": [
            {"name": "welcome", "duration_seconds": 30,
             "instruction": "Settle in. Today we look inward.",
             "phase": "welcome"},
            {"name": "prompt", "duration_seconds": 30,
             "instruction": "What's one thing you've been avoiding this week?",
             "phase": "prompt"},
            {"name": "silent reflection", "duration_seconds": 120,
             "instruction": "Sit with the question. Let thoughts come without judgment.",
             "phase": "reflection"},
            {"name": "deeper", "duration_seconds": 120,
             "instruction": "Why does this matter to you? What would change if you faced it?",
             "phase": "reflection"},
            {"name": "synthesis", "duration_seconds": 60,
             "instruction": "What's one thing you'll carry forward from this reflection?",
             "phase": "synthesis"},
            {"name": "share", "duration_seconds": 30,
             "instruction": "Optionally share your insight with your pod.",
             "phase": "share"},
            {"name": "closing", "duration_seconds": 30,
             "instruction": "Clarity is a superpower. You just practiced it.",
             "phase": "closing"},
        ],
        "closing": "Clarity is a superpower. You just practiced it.",
    },
    "preparation": {
        "session_type": "preparation",
        "session_title": "launch sequence",
        "greeting": "Welcome. Let's prepare for the day.",
        "blocks": [
            {"name": "energy check", "duration_seconds": 30,
             "instruction": "Rate your energy 1-10. No judgment. Just notice.",
             "phase": "welcome"},
            {"name": "visualization", "duration_seconds": 70,
             "instruction": "Close your eyes. See your day going well. Every detail.",
             "phase": "visualization"},
            {"name": "priority 1", "duration_seconds": 70,
             "instruction": "What is the ONE thing that matters most today? Say it.",
             "phase": "planning"},
            {"name": "priority 2-3", "duration_seconds": 70,
             "instruction": "Two more things. Not urgent — important. Name them.",
             "phase": "planning"},
            {"name": "energy breath", "duration_seconds": 90,
             "instruction": "Inhale 4, hold 2, exhale 6. Energizing pattern. 6 rounds.",
             "phase": "breathwork"},
            {"name": "power statement", "duration_seconds": 60,
             "instruction": "I am Jerome. I build. I show up.",
             "phase": "power"},
            {"name": "launch", "duration_seconds": 30,
             "instruction": "Go. The world is waiting for what you build.",
             "phase": "closing"},
        ],
        "closing": "Go. The world is waiting for what you build.",
    },
}
