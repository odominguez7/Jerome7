"""Nudge Agent — timing-aware skip prevention.

Shows up before you skip. Never shames. Always specific.
Powered by Google Gemini 2.0 Flash.
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.agents.context import UserContext
from src.db.models import Nudge


@dataclass
class NudgeMessage:
    subject: str
    body: str
    cta: str


class NudgeAgent:

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")

    def should_nudge(self, ctx: UserContext) -> bool:
        if ctx.current_streak == 0:
            return False

        from datetime import date
        if ctx.sessions_last_7_days:
            latest = ctx.sessions_last_7_days[0].get("date")
            if latest == date.today().isoformat():
                return False

        if ctx.last_nudge_at:
            if datetime.now(timezone.utc) - ctx.last_nudge_at < timedelta(hours=4):
                return False

        return True

    def get_optimal_window(self, ctx: UserContext) -> Optional[datetime]:
        if not ctx.skip_history:
            now = datetime.now(timezone.utc)
            return now.replace(hour=8, minute=0, second=0, microsecond=0)

        skip_hours = {}
        for skip in ctx.skip_history:
            if isinstance(skip, datetime):
                h = skip.hour
                skip_hours[h] = skip_hours.get(h, 0) + 1
            elif isinstance(skip, str):
                try:
                    dt = datetime.fromisoformat(skip)
                    h = dt.hour
                    skip_hours[h] = skip_hours.get(h, 0) + 1
                except ValueError:
                    continue

        if not skip_hours:
            return None

        peak_hour = max(skip_hours, key=skip_hours.get)
        nudge_hour = max(0, peak_hour - 1)
        now = datetime.now(timezone.utc)
        return now.replace(hour=nudge_hour, minute=30, second=0, microsecond=0)

    async def generate_nudge(self, ctx: UserContext) -> NudgeMessage:
        if not self.api_key:
            return self._default_nudge(ctx)

        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=self.api_key)

            prompt = f"""Generate a nudge message for {ctx.name}.
Current streak: {ctx.current_streak} days.
Today's Seven 7 title: {ctx.todays_seven7.get('title', 'not generated yet') if ctx.todays_seven7 else 'not generated yet'}.

Rules:
- Reference their actual streak number.
- Mention their Seven 7 title for today if available.
- End with one clear CTA.
- Never: generic motivation, fitness cliches, shame.
- 2-3 sentences max for the body.

Output JSON only:
{{"subject": "short subject line", "body": "2-3 sentences", "cta": "one specific action"}}"""

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            data = json.loads(response.text)
            return NudgeMessage(**data)
        except Exception:
            return self._default_nudge(ctx)

    async def send(self, ctx: UserContext, channel: str, db=None) -> None:
        nudge_msg = await self.generate_nudge(ctx)

        if db:
            nudge = Nudge(
                user_id=ctx.user_id,
                channel=channel,
                message_text=f"{nudge_msg.subject}: {nudge_msg.body} | {nudge_msg.cta}",
            )
            db.add(nudge)
            db.commit()

    def _default_nudge(self, ctx: UserContext) -> NudgeMessage:
        return NudgeMessage(
            subject=f"Day {ctx.current_streak + 1} is waiting",
            body=f"{ctx.name}, your streak is at {ctx.current_streak} days. "
                 f"Your Seven 7 is ready. 7 minutes is all it takes.",
            cta="Run `jerome7 seven7` to see today's session.",
        )
