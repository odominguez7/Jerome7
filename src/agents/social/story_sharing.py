"""Story Sharing — share anonymized transformation stories to inspire the community.

Every streak has a story. This module surfaces them.
Powered by Google Gemini 2.5 Flash.
"""

import asyncio
import json
import os
from datetime import date, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from src.db.models import User, Streak, Session, SessionFeedback, Event


def _call_gemini(system_prompt: str, user_content: str, api_key: str) -> str:
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


STORY_PROMPT = """You are Jerome — the storyteller for the Seven 7 community.
Given anonymized user data, craft a short transformation story (3-5 sentences).

Output JSON only:
{
  "title": "2-4 words. Memorable.",
  "story": "3-5 sentences. First person perspective. Anonymized.",
  "highlight_stat": "The single most impressive number from their journey."
}

Rules:
- NEVER use the user's real name. Use "someone" or "a member".
- Focus on the emotional journey, not the physical.
- Reference specific numbers (streak, sessions, comeback).
- End on a forward-looking note.
- Never preachy. Never fitness cliches. Real talk."""


class StorySharing:
    """Share anonymized transformation stories to inspire the community."""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")

    async def generate_story(self, user_id: str, db: DBSession) -> dict:
        """Generate an anonymized transformation story from a user's data.

        Uses Gemini to create a compelling narrative.
        Returns: {story_text, stats, anonymized: True}
        """
        user = db.query(User).filter(User.id == user_id).first()
        streak = db.query(Streak).filter(Streak.user_id == user_id).first()

        if not user or not streak:
            return {"error": "User not found."}

        # Gather stats for the story
        total_sessions = (
            db.query(Session)
            .filter(Session.user_id == user_id)
            .count()
        )

        # Days since signup
        days_active = (
            (date.today() - user.created_at.date()).days
            if user.created_at
            else 0
        )

        # Average enjoyment
        feedback = (
            db.query(SessionFeedback)
            .filter(SessionFeedback.user_id == user_id)
            .all()
        )
        avg_enjoyment = None
        if feedback:
            ratings = [f.enjoyment_rating for f in feedback if f.enjoyment_rating]
            if ratings:
                avg_enjoyment = round(sum(ratings) / len(ratings), 1)

        stats = {
            "current_streak": streak.current_streak,
            "longest_streak": streak.longest_streak,
            "total_sessions": total_sessions,
            "streak_breaks": streak.streak_broken_count,
            "days_active": days_active,
            "avg_enjoyment": avg_enjoyment,
            "goal": str(user.goal.value) if user.goal else None,
            "fitness_level": str(user.fitness_level.value) if user.fitness_level else None,
        }

        # Generate story via Gemini
        if self.api_key:
            story_data = await self._gemini_generate_story(stats)
            if story_data:
                # Log as event
                event = Event(
                    event_type="story_generated",
                    user_id=user_id,
                    payload={
                        "title": story_data.get("title"),
                        "stats": stats,
                        "generated_at": datetime.utcnow().isoformat(),
                    },
                )
                db.add(event)
                db.commit()

                return {
                    "title": story_data.get("title", "A Journey"),
                    "story_text": story_data.get("story", ""),
                    "highlight_stat": story_data.get("highlight_stat", ""),
                    "stats": stats,
                    "anonymized": True,
                }

        # Fallback: build a simple story without Gemini
        story = self._build_fallback_story(stats)
        return {
            "title": story["title"],
            "story_text": story["story"],
            "highlight_stat": story["highlight_stat"],
            "stats": stats,
            "anonymized": True,
        }

    async def get_community_stories(self, db: DBSession, limit: int = 5) -> list:
        """Get recent community transformation stories."""
        story_events = (
            db.query(Event)
            .filter(Event.event_type == "story_generated")
            .order_by(Event.created_at.desc())
            .limit(limit)
            .all()
        )

        stories = []
        for evt in story_events:
            if evt.payload:
                stories.append({
                    "title": evt.payload.get("title", "A Journey"),
                    "stats": evt.payload.get("stats", {}),
                    "generated_at": evt.payload.get("generated_at"),
                })

        return stories

    async def get_story_of_the_day(self, db: DBSession) -> dict:
        """Select the most inspiring story of the day.

        Criteria ranked by impact:
        1. Biggest comeback (restarted after breaks, now on a streak)
        2. Highest active streak
        3. Most total sessions
        """
        # Check if we already have a story of the day
        today = date.today()
        existing = (
            db.query(Event)
            .filter(
                Event.event_type == "story_of_the_day",
                func.date(Event.created_at) == today,
            )
            .first()
        )

        if existing and existing.payload:
            return existing.payload

        # Find the best candidate
        all_streaks = (
            db.query(Streak)
            .filter(Streak.current_streak > 0)
            .all()
        )

        if not all_streaks:
            return {
                "title": "The Community Awaits",
                "story_text": "No stories yet. Be the first.",
                "highlight_stat": "Day 1 starts now.",
                "stats": {},
                "anonymized": True,
            }

        # Score each user for "story worthiness"
        best_user_id = None
        best_score = -1

        for streak in all_streaks:
            score = 0

            # Comeback factor: had breaks but came back strong
            if streak.streak_broken_count > 0 and streak.current_streak >= 5:
                score += streak.streak_broken_count * 10 + streak.current_streak

            # Pure streak factor
            score += streak.current_streak * 2

            # Total dedication factor
            score += streak.total_sessions

            if score > best_score:
                best_score = score
                best_user_id = streak.user_id

        if not best_user_id:
            return {
                "title": "Day by Day",
                "story_text": "Every streak starts with one session.",
                "highlight_stat": "7 minutes.",
                "stats": {},
                "anonymized": True,
            }

        # Generate the story
        story = await self.generate_story(best_user_id, db)

        # Cache as story of the day
        event = Event(
            event_type="story_of_the_day",
            user_id=best_user_id,
            payload=story,
        )
        db.add(event)
        db.commit()

        return story

    async def _gemini_generate_story(self, stats: dict) -> dict | None:
        """Use Gemini to generate a transformation story."""
        user_content = (
            f"User stats (anonymized):\n"
            f"- Current streak: {stats['current_streak']} days\n"
            f"- Longest streak: {stats['longest_streak']} days\n"
            f"- Total sessions: {stats['total_sessions']}\n"
            f"- Times they broke their streak and came back: {stats['streak_breaks']}\n"
            f"- Days since joining: {stats['days_active']}\n"
            f"- Average enjoyment: {stats['avg_enjoyment']}/5\n"
            f"- Goal: {stats['goal']}\n"
            f"- Level: {stats['fitness_level']}"
        )

        try:
            content = await asyncio.wait_for(
                asyncio.to_thread(
                    _call_gemini, STORY_PROMPT, user_content, self.api_key
                ),
                timeout=15,
            )
            return json.loads(content)
        except Exception as e:
            print(f"[StorySharing] Gemini story generation failed: {e}")
            return None

    def _build_fallback_story(self, stats: dict) -> dict:
        """Build a simple story without Gemini."""
        streak = stats["current_streak"]
        breaks = stats["streak_breaks"]
        total = stats["total_sessions"]

        if breaks > 0 and streak >= 5:
            title = "The Comeback"
            story = (
                f"Someone broke their chain {breaks} time{'s' if breaks > 1 else ''} "
                f"and came back every time. "
                f"They're on day {streak} now. "
                f"{total} sessions total — each one a choice to show up. "
                f"The chain isn't about perfection. It's about returning."
            )
            highlight_stat = f"{breaks} comebacks, {streak}-day streak"
        elif streak >= 14:
            title = "The Chain"
            story = (
                f"Someone has shown up for {streak} days straight. "
                f"Not because it's easy — because 7 minutes is small enough to never skip. "
                f"{total} sessions and counting."
            )
            highlight_stat = f"{streak}-day streak"
        else:
            title = "Just Starting"
            story = (
                f"Someone is {streak} days in. "
                f"They haven't missed yet. "
                f"The hardest part was day 1. Everything after that is momentum."
            )
            highlight_stat = f"Day {streak}"

        return {
            "title": title,
            "story": story,
            "highlight_stat": highlight_stat,
        }
