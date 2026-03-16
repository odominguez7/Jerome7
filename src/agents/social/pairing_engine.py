"""Pairing Engine — find the ONE person who could transform your journey.

'YU are one person away from someone who will transform your life.'
Omar met Miguel through a cold LinkedIn message. This engine recreates that magic.

Powered by Google Gemini 2.5 Flash.
"""

import asyncio
import json
import os
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from src.db.models import (
    User, Streak, Session, SessionFeedback, Event, generate_uuid,
)


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


ICE_BREAKER_PROMPT = """You are Jerome — you introduce two people who could become
accountability partners and maybe even friends.

Given two user profiles, write a short ice-breaker message that one could send to the other.
Make it feel like a warm introduction from a mutual friend, not a dating app.

Output JSON only:
{"ice_breaker": "The message. 2-3 sentences max. Mention something specific they share."}

Rules:
- Reference something concrete (their goal, streak, timezone).
- Never corporate. Never cringe. Talk like a real person.
- End with a question that's easy to answer."""


class PairingEngine:
    """'YU are one person away from someone who will transform your life.'

    Omar met Miguel through a cold LinkedIn message. This engine recreates that magic.
    """

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")

    async def find_your_person(self, user_id: str, db: DBSession) -> dict:
        """Find the ONE person who could transform this user's journey.

        Matching criteria:
        - Similar goals but different strengths
        - Compatible timezone (can message during similar hours)
        - Complementary personality (based on feedback patterns)
        Returns: {match_id, match_name, why_matched, ice_breaker}
        """
        user = db.query(User).filter(User.id == user_id).first()
        user_streak = db.query(Streak).filter(Streak.user_id == user_id).first()

        if not user:
            return {"error": "User not found."}

        # Check if already paired recently (last 30 days)
        thirty_days_ago = date.today() - timedelta(days=30)
        recent_pair = (
            db.query(Event)
            .filter(
                Event.user_id == user_id,
                Event.event_type == "pair_created",
                func.date(Event.created_at) >= thirty_days_ago,
            )
            .first()
        )
        if recent_pair:
            return {
                "already_paired": True,
                "pair_id": recent_pair.payload.get("pair_id") if recent_pair.payload else None,
                "match_id": recent_pair.payload.get("match_id") if recent_pair.payload else None,
                "message": "You were paired recently. Give it time to grow.",
            }

        # Build user profile for matching
        user_profile = self._build_profile(user, user_streak, db)

        # Find candidates: exclude self, exclude recent pairs
        recent_pair_ids = set()
        past_pairs = (
            db.query(Event)
            .filter(
                Event.user_id == user_id,
                Event.event_type == "pair_created",
            )
            .all()
        )
        for evt in past_pairs:
            if evt.payload:
                mid = evt.payload.get("match_id")
                if mid:
                    recent_pair_ids.add(mid)

        # Get all active users with streaks
        candidates = (
            db.query(User, Streak)
            .join(Streak, Streak.user_id == User.id)
            .filter(
                User.id != user_id,
                User.id.notin_(recent_pair_ids) if recent_pair_ids else True,
                Streak.current_streak > 0,
            )
            .all()
        )

        if not candidates:
            return {
                "match_id": None,
                "message": "No matches found yet. The community is growing — check back soon.",
            }

        # Score each candidate
        best_match = None
        best_score = -1

        for candidate_user, candidate_streak in candidates:
            score = self._compatibility_score(
                user, user_streak, user_profile,
                candidate_user, candidate_streak, db,
            )
            if score > best_score:
                best_score = score
                best_match = (candidate_user, candidate_streak)

        if not best_match:
            return {
                "match_id": None,
                "message": "No strong match found today. We'll keep looking.",
            }

        match_user, match_streak = best_match

        # Generate why they matched
        why_matched = self._explain_match(
            user, user_streak, match_user, match_streak
        )

        # Generate ice breaker
        ice_breaker = await self.generate_ice_breaker(
            {"name": user.name, "goal": str(user.goal) if user.goal else None,
             "streak": user_streak.current_streak if user_streak else 0},
            {"name": match_user.name, "goal": str(match_user.goal) if match_user.goal else None,
             "streak": match_streak.current_streak if match_streak else 0},
        )

        # Log the pairing
        pair_id = generate_uuid()
        for uid in [user_id, match_user.id]:
            event = Event(
                event_type="pair_created",
                user_id=uid,
                payload={
                    "pair_id": pair_id,
                    "match_id": match_user.id if uid == user_id else user_id,
                    "match_name": match_user.name if uid == user_id else user.name,
                    "compatibility_score": round(best_score, 2),
                    "why": why_matched,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            db.add(event)

        db.commit()

        return {
            "pair_id": pair_id,
            "match_id": match_user.id,
            "match_name": match_user.name,
            "compatibility_score": round(best_score, 2),
            "why_matched": why_matched,
            "ice_breaker": ice_breaker,
        }

    async def generate_ice_breaker(self, user_a: dict, user_b: dict) -> str:
        """Generate a personalized ice-breaker message.

        Uses Gemini to craft something authentic, not corporate.
        """
        default = (
            f"Hey {user_b['name']}! I'm {user_a['name']} — "
            f"we're both on a streak and figured we could keep each other going. "
            f"What's been the hardest part of showing up daily for you?"
        )

        if not self.api_key:
            return default

        user_content = (
            f"Person A: {user_a['name']}, goal: {user_a.get('goal', 'unknown')}, "
            f"streak: {user_a.get('streak', 0)} days.\n"
            f"Person B: {user_b['name']}, goal: {user_b.get('goal', 'unknown')}, "
            f"streak: {user_b.get('streak', 0)} days."
        )

        try:
            content = await asyncio.wait_for(
                asyncio.to_thread(
                    _call_gemini, ICE_BREAKER_PROMPT, user_content, self.api_key
                ),
                timeout=15,
            )
            data = json.loads(content)
            return data.get("ice_breaker", default)
        except Exception:
            return default

    async def track_pair_outcome(self, pair_id: str, db: DBSession) -> dict:
        """Track how paired users are doing.

        - Did they both improve?
        - Are their streaks correlated?
        """
        # Find the pair events
        pair_events = (
            db.query(Event)
            .filter(
                Event.event_type == "pair_created",
            )
            .all()
        )

        user_ids = []
        created_at = None
        for evt in pair_events:
            if evt.payload and evt.payload.get("pair_id") == pair_id:
                user_ids.append(evt.user_id)
                if not created_at:
                    created_at = evt.created_at

        if len(user_ids) < 2:
            return {"error": "Pair not found."}

        user_a_id, user_b_id = user_ids[0], user_ids[1]

        # Get streaks
        streak_a = db.query(Streak).filter(Streak.user_id == user_a_id).first()
        streak_b = db.query(Streak).filter(Streak.user_id == user_b_id).first()

        # Sessions since pairing
        pair_date = created_at.date() if created_at else date.today() - timedelta(days=30)

        sessions_a = (
            db.query(Session)
            .filter(
                Session.user_id == user_a_id,
                func.date(Session.logged_at) >= pair_date,
            )
            .count()
        )
        sessions_b = (
            db.query(Session)
            .filter(
                Session.user_id == user_b_id,
                func.date(Session.logged_at) >= pair_date,
            )
            .count()
        )

        days_since_pair = (date.today() - pair_date).days or 1

        user_a = db.query(User).filter(User.id == user_a_id).first()
        user_b = db.query(User).filter(User.id == user_b_id).first()

        return {
            "pair_id": pair_id,
            "days_since_paired": days_since_pair,
            "user_a": {
                "name": user_a.name if user_a else "Unknown",
                "sessions_since_pair": sessions_a,
                "completion_rate": round(sessions_a / days_since_pair * 100, 1),
                "current_streak": streak_a.current_streak if streak_a else 0,
            },
            "user_b": {
                "name": user_b.name if user_b else "Unknown",
                "sessions_since_pair": sessions_b,
                "completion_rate": round(sessions_b / days_since_pair * 100, 1),
                "current_streak": streak_b.current_streak if streak_b else 0,
            },
            "both_improved": sessions_a > 0 and sessions_b > 0,
            "correlation": (
                "strong"
                if abs(sessions_a - sessions_b) <= 2
                else "weak"
            ),
        }

    def _build_profile(
        self, user: User, streak: Streak | None, db: DBSession
    ) -> dict:
        """Build a matching profile from user data."""
        week_ago = date.today() - timedelta(days=7)
        feedback = (
            db.query(SessionFeedback)
            .filter(
                SessionFeedback.user_id == user.id,
                SessionFeedback.session_date >= week_ago,
            )
            .all()
        )

        avg_difficulty = None
        avg_enjoyment = None
        if feedback:
            diffs = [f.difficulty_rating for f in feedback if f.difficulty_rating]
            enjoys = [f.enjoyment_rating for f in feedback if f.enjoyment_rating]
            if diffs:
                avg_difficulty = sum(diffs) / len(diffs)
            if enjoys:
                avg_enjoyment = sum(enjoys) / len(enjoys)

        return {
            "goal": str(user.goal) if user.goal else None,
            "fitness_level": str(user.fitness_level) if user.fitness_level else None,
            "timezone": user.timezone,
            "streak": streak.current_streak if streak else 0,
            "avg_difficulty": avg_difficulty,
            "avg_enjoyment": avg_enjoyment,
        }

    def _compatibility_score(
        self,
        user_a: User, streak_a: Streak | None, profile_a: dict,
        user_b: User, streak_b: Streak | None,
        db: DBSession,
    ) -> float:
        """Score compatibility between two users (0-1)."""
        score = 0.0

        # Same goal = strong signal (0.3)
        if user_a.goal and user_b.goal and user_a.goal == user_b.goal:
            score += 0.3
        elif user_a.goal and user_b.goal:
            score += 0.1  # Different goals still have some value

        # Compatible timezone: within 3 hours (0.25)
        tz_a = user_a.timezone or "UTC"
        tz_b = user_b.timezone or "UTC"
        if tz_a == tz_b:
            score += 0.25
        elif tz_a.split("/")[0] == tz_b.split("/")[0]:
            score += 0.15  # Same continent

        # Complementary fitness level: different levels learn from each other (0.2)
        if user_a.fitness_level and user_b.fitness_level:
            if user_a.fitness_level != user_b.fitness_level:
                score += 0.2  # Different = complementary
            else:
                score += 0.1

        # Similar streak range: close enough to relate (0.15)
        sa = streak_a.current_streak if streak_a else 0
        sb = streak_b.current_streak if streak_b else 0
        streak_diff = abs(sa - sb)
        if streak_diff <= 3:
            score += 0.15
        elif streak_diff <= 7:
            score += 0.1
        elif streak_diff <= 14:
            score += 0.05

        # Active recently (0.1)
        if streak_b and streak_b.last_session_date:
            days_since = (date.today() - streak_b.last_session_date).days
            if days_since <= 1:
                score += 0.1
            elif days_since <= 3:
                score += 0.05

        return min(score, 1.0)

    def _explain_match(
        self,
        user_a: User, streak_a: Streak | None,
        user_b: User, streak_b: Streak | None,
    ) -> str:
        """Generate a human-readable explanation of why two users matched."""
        reasons = []

        if user_a.goal and user_b.goal and user_a.goal == user_b.goal:
            reasons.append(f"You're both working toward {user_a.goal.value.replace('_', ' ')}")

        sa = streak_a.current_streak if streak_a else 0
        sb = streak_b.current_streak if streak_b else 0
        if abs(sa - sb) <= 3:
            reasons.append(f"Similar streak ({sa} and {sb} days)")

        if user_a.timezone and user_b.timezone:
            if user_a.timezone == user_b.timezone:
                reasons.append("Same timezone")
            elif user_a.timezone.split("/")[0] == user_b.timezone.split("/")[0]:
                reasons.append("Similar timezone")

        if user_a.fitness_level and user_b.fitness_level:
            if user_a.fitness_level != user_b.fitness_level:
                reasons.append(
                    f"Complementary levels ({user_a.fitness_level.value} + {user_b.fitness_level.value})"
                )

        if not reasons:
            reasons.append("Both showing up consistently")

        return ". ".join(reasons) + "."
