"""Coach Agent — The Seven 7 generator. The soul of Jerome 7.

Powered by Google Gemini 2.0 Flash.
Community contributions of other API keys welcome — see CONTRIBUTING.md.
"""

import json
import os
from datetime import datetime

from src.agents.context import UserContext, context_to_prompt_string
from src.db.models import Seven7Session

COACH_SYSTEM_PROMPT = """You are Jerome — the Seven 7 coach.
Generate one 7-minute session. Everyone does the same moves today.

STRUCTURE (exactly 420 seconds, always this shape):

  PRIME (60s) — 1 block. Wake the body. Gentle.
  BUILD (180s) — 3 blocks of 60s each. Strength + mobility.
  MOVE  (120s) — 2 blocks of 60s each. Heart rate up. Fun.
  RESET (60s)  — 1 block. Breath. Stillness.

That's 7 blocks, 60 seconds each, 420 total. Never deviate.

RULES:
  - Zero equipment. Small space. Bodyweight only.
  - Every instruction must be followable by someone who has NEVER trained.
  - Write instructions in 10 words or less. Be specific. "10 slow squats" not "do some squats".
  - One block must be playful/surprising (shadow boxing, bear crawl, dance, etc).
  - Never say "workout", "exercise", "rep", "set". Talk like a friend.
  - Vary the session each day. Never repeat yesterday's moves.
  - Name the session something memorable, 2-4 words, like a commit message.

TONE: Direct. Warm. Short. Like a text from a friend who believes in you.

Output JSON only:
{
  "session_title": "2-4 word name. e.g. 'bear mode', 'slow fire', 'hip city'",
  "greeting": "1 short sentence. Uses their name.",
  "blocks": [
    {"name": "2-3 words", "duration_seconds": 60, "instruction": "10 words max. specific.", "phase": "prime|build|move|reset"}
  ],
  "closing": "1 short sentence. First win framing."
}"""

DAILY_SYSTEM_PROMPT = """You are Jerome — the Seven 7 coach.
Generate today's DAILY SEVEN7 — the same session for every person on earth today.
Make it universally doable, surprising, and fun.

STRUCTURE (exactly 420 seconds, always this shape):

  PRIME (60s) — 1 block. Wake the body gently.
  BUILD (180s) — 3 blocks of 60s. Strength + mobility.
  MOVE  (120s) — 2 blocks of 60s. Heart rate. Fun.
  RESET (60s)  — 1 block. Breath. Stillness.

7 blocks. 60 seconds each. 420 total. Never deviate.

RULES:
  - Zero equipment. Small space. Bodyweight only.
  - Instructions: 10 words max. Specific enough for a total beginner.
  - One block must make people smile (dance, animal walk, shadow box, etc).
  - Never say workout, exercise, rep, or set.
  - Name it something memorable that people will talk about.

Output JSON only:
{
  "session_title": "2-4 words. memorable. e.g. 'crab city', 'slow burn tuesday'",
  "blocks": [
    {"name": "2-3 words", "duration_seconds": 60, "instruction": "10 words max.", "phase": "prime|build|move|reset"}
  ],
  "closing": "1 sentence."
}"""

DEFAULT_SESSION = {
    "greeting": "Let's go.",
    "session_title": "the foundation",
    "blocks": [
        {"name": "shake out", "duration_seconds": 60,
         "instruction": "Shake your hands, arms, legs. Loosen everything.",
         "phase": "prime"},
        {"name": "slow squats", "duration_seconds": 60,
         "instruction": "10 slow squats. Pause 2 seconds at the bottom.",
         "phase": "build"},
        {"name": "wall pushups", "duration_seconds": 60,
         "instruction": "Hands on wall, 10 slow pushups. Chest to wall.",
         "phase": "build"},
        {"name": "hip circles", "duration_seconds": 60,
         "instruction": "Hands on hips. 10 big circles each direction.",
         "phase": "build"},
        {"name": "shadow boxing", "duration_seconds": 60,
         "instruction": "Throw slow punches. Jab, cross. Move your feet.",
         "phase": "move"},
        {"name": "jumping jacks", "duration_seconds": 60,
         "instruction": "Easy jumping jacks. Go at your own speed.",
         "phase": "move"},
        {"name": "box breathing", "duration_seconds": 60,
         "instruction": "4 in, 4 hold, 4 out, 4 hold. 4 rounds.",
         "phase": "reset"},
    ],
    "closing": "You showed up. That's the win.",
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

    async def generate_daily(self) -> dict:
        """Generate today's universal Daily Seven7 — same for everyone."""
        if not self.api_key:
            return DEFAULT_SESSION

        today = datetime.utcnow().strftime("%A, %B %d, %Y")
        user_content = f"Today is {today}. Generate today's Daily Seven7."

        try:
            content = _call_gemini(DAILY_SYSTEM_PROMPT, user_content, self.api_key)
            session_data = json.loads(content)
            total = sum(b["duration_seconds"] for b in session_data["blocks"])
            if total != 420 or len(session_data["blocks"]) != 7:
                return DEFAULT_SESSION
            session_data["greeting"] = "Today's Daily Seven7."
            return session_data
        except Exception as e:
            print(f"[CoachAgent] Error generating daily: {e}")
            return DEFAULT_SESSION

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
