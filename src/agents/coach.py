"""Coach Agent — The Seven 7 generator. The soul of Jerome 7.

Powered by Google Gemini 2.0 Flash.
Community contributions of other API keys welcome — see CONTRIBUTING.md.
"""

import asyncio
import copy
import json
import logging
import os
from datetime import datetime, timezone

from src.agents.context import UserContext, context_to_prompt_string
# Seven7Session model removed in cleanup — session logging via Session model only

logger = logging.getLogger(__name__)

COACH_SYSTEM_PROMPT = """You are Jerome — the Seven 7 wellness guide.
Generate one 7-minute session. Everyone does the same practice today.

STRUCTURE (exactly 420 seconds, always this shape):

  ARRIVE (60s) — 1 block. Settle in. Ground yourself.
  BREATHE (180s) — 3 blocks of 60s each. Breathwork + mindful movement.
  FLOW   (120s) — 2 blocks of 60s each. Present and grounded.
  RESET  (60s)  — 1 block. Breath. Stillness.

That's 7 blocks, 60 seconds each, 420 total. Never deviate.

RULES:
  - No equipment needed. Small space. Just you.
  - Every instruction must be followable by someone who has NEVER practiced.
  - Write instructions in 10 words or less. Be specific. "4 deep breaths, exhale slowly" not "breathe".
  - One block must be calming/surprising (gentle stretching, body scan, gratitude, etc).
  - Never say "workout", "exercise", "rep", "set", "fitness", "bodyweight". Talk like a friend.
  - Vary the session each day. Never repeat yesterday's practice.
  - Name the session something memorable, 2-4 words, like a commit message.

ADAPT FROM FEEDBACK (if provided):
  - If avg difficulty > 4: scale back. More stillness, less intensity.
  - If avg difficulty < 2: add depth. Longer holds, deeper breathing.
  - If avg enjoyment < 3: add more calming/surprising blocks. Vary more.
  - If body notes mention pain: AVOID anything that aggravates those areas.
  - If avg completion < 5/7: session may be too demanding. Simplify.
  - If they skip certain phases: make those phases more engaging or accessible.

TONE: Direct. Warm. Short. Like a text from a friend who believes in you.

Output JSON only:
{
  "session_title": "2-4 word name. e.g. 'still waters', 'slow fire', 'open sky'",
  "greeting": "1 short sentence. Uses their name.",
  "blocks": [
    {"name": "2-3 words", "duration_seconds": 60, "instruction": "10 words max. specific.", "phase": "arrive|breathe|flow|reset"}
  ],
  "closing": "1 short sentence. First win framing."
}"""

DAILY_SYSTEM_PROMPT = """You are Jerome — the Seven 7 wellness guide.
Generate today's DAILY SEVEN7 — the same session for every person on earth today.
Make it universally doable, calming, and grounding.

STRUCTURE (exactly 420 seconds, always this shape):

  ARRIVE (60s) — 1 block. Settle in gently.
  BREATHE (180s) — 3 blocks of 60s. Breathwork + mindful movement.
  FLOW   (120s) — 2 blocks of 60s. Present and grounded.
  RESET  (60s)  — 1 block. Breath. Stillness.

7 blocks. 60 seconds each. 420 total. Never deviate.

RULES:
  - No equipment needed. Small space. Just you.
  - Instructions: 10 words max. Specific enough for a total beginner.
  - One block must bring a sense of wonder (gentle stretching, body scan, gratitude, etc).
  - Never say workout, exercise, rep, set, fitness, or bodyweight.
  - Name it something memorable that people will talk about.

Output JSON only:
{
  "session_title": "2-4 words. memorable. e.g. 'still morning', 'open sky tuesday'",
  "blocks": [
    {"name": "2-3 words", "duration_seconds": 60, "instruction": "10 words max.", "phase": "arrive|breathe|flow|reset"}
  ],
  "closing": "1 sentence."
}"""

# Wellness session prompts — the 4 rotating day types from the blueprint
WELLNESS_PROMPTS = {
    "breathwork": """You are Jerome — the Seven 7 wellness guide.
Generate today's 7-MINUTE GUIDED BREATHWORK session.

STRUCTURE (exactly 420 seconds):
  Welcome (30s) — Greet the community. Use "Jerome" identity.
  Intention (30s) — Set one intention for the session.
  Guided Breathwork (270s) — Box breathing: inhale 4, hold 4, exhale 4, hold 4.
  Body Scan (60s) — Cool-down. Scan from head to toes.
  Closing (30s) — Affirmation + streak encouragement.

RULES:
  - No equipment. Just earphones and a place to sit.
  - Warm, calm tone. Like a friend who believes in you.
  - Instructions must be followable with eyes closed.
  - Never say "workout" or "exercise". This is breathwork.
  - Name it something memorable, 2-3 words.

Output JSON only:
{
  "session_type": "breathwork",
  "session_title": "2-3 words",
  "greeting": "1 short sentence.",
  "blocks": [
    {"name": "2-3 words", "duration_seconds": N, "instruction": "Clear guidance.", "phase": "welcome|intention|breathwork|cooldown|closing"}
  ],
  "closing": "1 sentence. Affirming."
}""",
    "meditation": """You are Jerome — the Seven 7 wellness guide.
Generate today's 7-MINUTE GUIDED MEDITATION session.

STRUCTURE (exactly 420 seconds):
  Welcome (30s) — Greet + streak status.
  Grounding (30s) — 5 senses check-in.
  Guided Meditation (270s) — Breath awareness with gentle redirects.
  Gratitude (60s) — Name 3 things.
  Closing (30s) — Affirmation + community stat.

RULES:
  - No equipment. Eyes closed or soft gaze.
  - Gentle, present-tense guidance.
  - When mind wanders, redirect without judgment.
  - Name it something calming, 2-3 words.

Output JSON only:
{
  "session_type": "meditation",
  "session_title": "2-3 words",
  "greeting": "1 short sentence.",
  "blocks": [
    {"name": "2-3 words", "duration_seconds": N, "instruction": "Clear guidance.", "phase": "welcome|grounding|meditation|gratitude|closing"}
  ],
  "closing": "1 sentence. Community-aware."
}""",
    "reflection": """You are Jerome — the Seven 7 wellness guide.
Generate today's 7-MINUTE REFLECTION session.

STRUCTURE (exactly 420 seconds):
  Welcome + Prompt (30s) — Today's reflection question.
  Journaling Prompt (30s) — Spoken prompt, user reflects silently.
  Silent Reflection (240s) — Ambient space for thinking.
  Synthesis (60s) — "What's one thing you'll carry forward?"
  Community Share (30s) — Optional post to pod.
  Closing (30s) — Affirmation.

RULES:
  - Create a thought-provoking, non-judgmental prompt.
  - Prompts should be relevant to builders/creators.
  - Leave space for silence — don't over-guide.
  - Name it something introspective, 2-3 words.

Output JSON only:
{
  "session_type": "reflection",
  "session_title": "2-3 words",
  "greeting": "1 short sentence.",
  "blocks": [
    {"name": "2-3 words", "duration_seconds": N, "instruction": "Clear guidance.", "phase": "welcome|prompt|reflection|synthesis|share|closing"}
  ],
  "closing": "1 sentence."
}""",
    "preparation": """You are Jerome — the Seven 7 wellness guide.
Generate today's 7-MINUTE PREPARATION session.

STRUCTURE (exactly 420 seconds):
  Energy Check (30s) — Rate energy, no judgment.
  Visualization (60s) — See the day succeeding.
  Intentional Planning (180s) — 3 priorities, spoken aloud.
  Energizing Breathwork (90s) — Pattern: inhale 4, hold 2, exhale 6.
  Power Statement (30s) — "I am Jerome. I build. I show up."
  Launch (30s) — Into the day.

RULES:
  - Energizing, not relaxing. This is the launch sequence.
  - Focus on clarity and purpose.
  - Make the power statement feel earned, not cheesy.
  - Name it something motivating, 2-3 words.

Output JSON only:
{
  "session_type": "preparation",
  "session_title": "2-3 words",
  "greeting": "1 short sentence.",
  "blocks": [
    {"name": "2-3 words", "duration_seconds": N, "instruction": "Clear guidance.", "phase": "welcome|visualization|planning|breathwork|power|closing"}
  ],
  "closing": "1 sentence. Energizing."
}""",
}

DEFAULT_SESSION = {
    "greeting": "Let's begin.",
    "session_title": "the foundation",
    "blocks": [
        {"name": "deep breathing", "duration_seconds": 60,
         "instruction": "4 deep breaths. In through nose, out through mouth.",
         "phase": "arrive"},
        {"name": "body scan", "duration_seconds": 60,
         "instruction": "Scan from head to toes. Notice without judgment.",
         "phase": "breathe"},
        {"name": "gentle stretching", "duration_seconds": 60,
         "instruction": "Reach up, fold forward slowly. Breathe into it.",
         "phase": "breathe"},
        {"name": "gratitude reflection", "duration_seconds": 60,
         "instruction": "Name 3 things you are grateful for right now.",
         "phase": "breathe"},
        {"name": "mindful pause", "duration_seconds": 60,
         "instruction": "Close your eyes. Follow your natural breath.",
         "phase": "flow"},
        {"name": "intention setting", "duration_seconds": 60,
         "instruction": "Set one intention for today. Hold it clearly.",
         "phase": "flow"},
        {"name": "closing breath", "duration_seconds": 60,
         "instruction": "4 in, 4 hold, 4 out, 4 hold. 4 rounds.",
         "phase": "reset"},
    ],
    "closing": "You showed up. That's the win.",
}


# Reusable Gemini client (one connection pool for the process)
_gemini_client = None


def _get_gemini_client(api_key: str):
    """Get or create a reusable Gemini client."""
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def _call_gemini(system_prompt: str, user_content: str, api_key: str) -> str:
    """Call Gemini 2.5 Flash and return raw text response."""
    from google.genai import types
    client = _get_gemini_client(api_key)
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
            content = await asyncio.wait_for(
                asyncio.to_thread(_call_gemini, COACH_SYSTEM_PROMPT, user_data, self.api_key),
                timeout=25,
            )
            session_data = json.loads(content)

            total = sum(b["duration_seconds"] for b in session_data["blocks"])
            if total != 420:
                retry_prompt = (
                    COACH_SYSTEM_PROMPT
                    + f"\nCRITICAL: blocks must sum to exactly 420 seconds. Previous attempt summed to {total}."
                )
                content = await asyncio.wait_for(
                    asyncio.to_thread(_call_gemini, retry_prompt, user_data, self.api_key),
                    timeout=25,
                )
                session_data = json.loads(content)
                total = sum(b["duration_seconds"] for b in session_data["blocks"])
                if total != 420:
                    return self._fallback_session(ctx)

            return session_data

        except Exception as e:
            logger.error("Error generating session: %s", e)
            return self._fallback_session(ctx)

    async def generate_daily(self) -> dict:
        """Generate today's universal Daily Seven7 — same for everyone."""
        if not self.api_key:
            return DEFAULT_SESSION

        today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
        user_content = f"Today is {today}. Generate today's Daily Seven7."

        try:
            content = await asyncio.wait_for(
                asyncio.to_thread(_call_gemini, DAILY_SYSTEM_PROMPT, user_content, self.api_key),
                timeout=25,
            )
            session_data = json.loads(content)
            total = sum(b["duration_seconds"] for b in session_data["blocks"])
            if total != 420 or len(session_data["blocks"]) != 7:
                return DEFAULT_SESSION
            session_data["greeting"] = "Today's Daily Seven7."
            return session_data
        except Exception as e:
            logger.error("Error generating daily: %s", e)
            return DEFAULT_SESSION

    async def generate_wellness(self, session_type: str) -> dict:
        """Generate today's wellness session based on the rotating day type."""
        from src.agents.session_types import FALLBACK_SESSIONS

        if session_type not in WELLNESS_PROMPTS:
            return FALLBACK_SESSIONS.get("breathwork", DEFAULT_SESSION)

        if not self.api_key:
            return FALLBACK_SESSIONS.get(session_type, DEFAULT_SESSION)

        today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
        prompt = WELLNESS_PROMPTS[session_type]
        user_content = f"Today is {today}. Generate today's {session_type} session."

        try:
            content = await asyncio.wait_for(
                asyncio.to_thread(_call_gemini, prompt, user_content, self.api_key),
                timeout=25,
            )
            session_data = json.loads(content)
            total = sum(b["duration_seconds"] for b in session_data["blocks"])
            if total != 420:
                return FALLBACK_SESSIONS.get(session_type, DEFAULT_SESSION)
            session_data["session_type"] = session_type
            return session_data
        except Exception as e:
            logger.error("Error generating wellness %s: %s", session_type, e)
            return FALLBACK_SESSIONS.get(session_type, DEFAULT_SESSION)

    async def generate_restart(self, ctx: UserContext, db=None) -> dict:
        """Generate a restart session after a broken streak. Slower, kinder."""
        if not self.api_key:
            return self._fallback_session(ctx)

        restart_prompt = COACH_SYSTEM_PROMPT + """
Additional context: This person's streak just broke. They are returning.
Be kinder. Be slower. Focus on re-entry, not intensity.
The greeting should acknowledge the break without shame.
Start with the gentlest practice possible."""

        user_data = context_to_prompt_string(ctx)

        try:
            content = await asyncio.wait_for(
                asyncio.to_thread(_call_gemini, restart_prompt, user_data, self.api_key),
                timeout=25,
            )
            session_data = json.loads(content)

            return session_data

        except Exception:
            return self._fallback_session(ctx)

    def _fallback_session(self, ctx: UserContext) -> dict:
        session = copy.deepcopy(DEFAULT_SESSION)
        session["greeting"] = f"Good morning, {ctx.name}. Let's begin."
        return session
