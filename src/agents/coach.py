"""Coach Agent — The Seven 7 generator. The soul of Jerome 7.

Powered by Google Gemini 2.0 Flash.
Community contributions of other API keys welcome — see CONTRIBUTING.md.
"""

import json
import os
from datetime import datetime

from src.agents.context import UserContext, context_to_prompt_string
from src.db.models import Seven7Session

COACH_SYSTEM_PROMPT = """You are the Seven 7 coach. Your job is to generate a single,
personalized 7-minute session for a specific person today.
You are not a motivational poster. You are not a fitness app.
You are the quiet voice that knows them better than they
know themselves right now.
Rules you never break:
  - Total duration of all blocks: exactly 420 seconds.
  - Always start with movement. The body leads.
  - Always end with breath or stillness.
  - If streak > 30 days: acknowledge it in one sentence, then move on.
  - If streak is at risk: name it directly. No softening.
  - If energy_today is low: scale intensity down, not time.
  - Never use the word workout.
  - Tone: direct, warm, like a friend who knows what it took.
Output JSON only. No preamble. No explanation.
Schema: {
  "greeting": "1 sentence. Personal. Uses their name.",
  "session_title": "e.g. 'The reset morning', 'Low and slow'",
  "blocks": [
    {
      "name": "e.g. 'spinal roll', 'box breathing'",
      "duration_seconds": 90,
      "instruction": "one sentence, specific",
      "why_today": "one sentence. Why THIS for them TODAY."
    }
  ],
  "closing": "1 sentence. The first win framing."
}"""

DEFAULT_SESSION = {
    "greeting": "Good morning. Let's begin.",
    "session_title": "The foundation",
    "blocks": [
        {"name": "walk in place", "duration_seconds": 60,
         "instruction": "Walk in place slowly. Feel your feet on the ground.",
         "why_today": "Movement first. Always."},
        {"name": "shoulder rolls", "duration_seconds": 60,
         "instruction": "Roll your shoulders back 10 times, then forward 10 times.",
         "why_today": "Release the tension from yesterday."},
        {"name": "bodyweight squats", "duration_seconds": 90,
         "instruction": "10 slow squats. Pause at the bottom for 2 seconds each.",
         "why_today": "Wake up the biggest muscles in your body."},
        {"name": "standing stretch", "duration_seconds": 90,
         "instruction": "Reach up, lean left 30 seconds, lean right 30 seconds, fold forward 30 seconds.",
         "why_today": "Open the sides. Decompress the spine."},
        {"name": "box breathing", "duration_seconds": 120,
         "instruction": "4 seconds in, 4 hold, 4 out, 4 hold. 5 rounds.",
         "why_today": "Reset the nervous system before the day begins."},
    ],
    "closing": "You showed up. That is the first win. Everything after this is downstream.",
}


def _call_gemini(system_prompt: str, user_content: str, api_key: str) -> str:
    """Call Gemini 2.0 Flash and return raw text response."""
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
        ),
    )
    return response.text


class CoachAgent:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")

    async def generate(self, ctx: UserContext, db=None) -> dict:
        """Generate today's Seven 7 session using Gemini 2.0 Flash."""
        user_data = context_to_prompt_string(ctx)

        if not self.api_key:
            return self._fallback_session(ctx)

        try:
            content = _call_gemini(COACH_SYSTEM_PROMPT, user_data, self.api_key)
            session_data = json.loads(content)

            total = sum(b["duration_seconds"] for b in session_data["blocks"])
            if total != 420:
                retry_prompt = (
                    COACH_SYSTEM_PROMPT
                    + f"\nCRITICAL: blocks must sum to exactly 420 seconds. Previous attempt summed to {total}."
                )
                content = _call_gemini(retry_prompt, user_data, self.api_key)
                session_data = json.loads(content)
                total = sum(b["duration_seconds"] for b in session_data["blocks"])
                if total != 420:
                    return self._fallback_session(ctx)

            if db:
                seven7 = Seven7Session(
                    user_id=ctx.user_id,
                    greeting=session_data["greeting"],
                    session_title=session_data["session_title"],
                    closing=session_data["closing"],
                    blocks=session_data["blocks"],
                )
                db.add(seven7)
                db.commit()

            return session_data

        except Exception as e:
            print(f"[CoachAgent] Error generating session: {e}")
            return self._fallback_session(ctx)

    async def generate_restart(self, ctx: UserContext, db=None) -> dict:
        """Generate a restart session after a broken streak. Slower, kinder."""
        if not self.api_key:
            return self._fallback_session(ctx)

        restart_prompt = COACH_SYSTEM_PROMPT + """
Additional context: This person's streak just broke. They are returning.
Be kinder. Be slower. Focus on re-entry, not intensity.
The greeting should acknowledge the break without shame.
Start with the gentlest movement possible."""

        user_data = context_to_prompt_string(ctx)

        try:
            content = _call_gemini(restart_prompt, user_data, self.api_key)
            session_data = json.loads(content)

            if db:
                seven7 = Seven7Session(
                    user_id=ctx.user_id,
                    greeting=session_data["greeting"],
                    session_title=session_data["session_title"],
                    closing=session_data["closing"],
                    blocks=session_data["blocks"],
                )
                db.add(seven7)
                db.commit()

            return session_data

        except Exception:
            return self._fallback_session(ctx)

    def _fallback_session(self, ctx: UserContext) -> dict:
        session = DEFAULT_SESSION.copy()
        session["greeting"] = f"Good morning, {ctx.name}. Let's begin."
        return session
