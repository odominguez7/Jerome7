"""Burnout Detector — early warning system for chain breaks.

Analyzes behavioral signals (timing drift, difficulty creep, engagement
drop) to flag burnout before the user actually quits.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from src.db.models import (
    User, Streak, Session, SessionFeedback,
)


def _call_gemini(system_prompt: str, user_content: str, api_key: str) -> str:
    """Call Gemini 2.5 Flash for burnout intervention copy."""
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


INTERVENTION_PROMPT = """You are Jerome — a wellness coach who genuinely cares.
A user is showing burnout signals. Write a short, warm intervention message.

RULES:
- Never shame. Never use "you should" or "you need to".
- Acknowledge their effort first.
- Be specific to their signals (provided below).
- Suggest ONE concrete, easy action.
- 2-3 sentences max.
- Tone: a friend who notices you're tired, not a coach who's disappointed.

Output JSON only:
{"message": "the intervention text", "suggested_action": "one specific thing to try"}"""


class BurnoutDetector:
    """Detect burnout signals before they become chain breaks."""

    BURNOUT_SIGNALS = {
        "declining_consistency": "Sessions becoming less regular",
        "increasing_difficulty": "Rating sessions as harder over time",
        "skipping_feedback": "Not providing feedback anymore",
        "late_sessions": "Sessions happening later and later in the day",
        "long_gaps": "Gaps between sessions getting longer",
    }

    def __init__(self, user_id: str, db: DBSession):
        self.user_id = user_id
        self.db = db
        self.api_key = os.getenv("GEMINI_API_KEY")

    # ------------------------------------------------------------------
    # Full assessment
    # ------------------------------------------------------------------

    async def assess(self) -> dict:
        """Run full burnout assessment.

        Returns:
            {
                risk_level: 'low' | 'medium' | 'high' | 'critical',
                signals: [{'signal': key, 'description': str, 'detail': str}],
                recommendation: str,
            }
        """
        signals = await self._detect_signals()

        signal_count = len(signals)
        if signal_count == 0:
            risk_level = "low"
        elif signal_count <= 1:
            risk_level = "medium"
        elif signal_count <= 3:
            risk_level = "high"
        else:
            risk_level = "critical"

        # Escalate if specific dangerous combos are present
        signal_keys = {s["signal"] for s in signals}
        if "long_gaps" in signal_keys and "declining_consistency" in signal_keys:
            risk_level = max(risk_level, "high", key=["low", "medium", "high", "critical"].index)

        intervention = await self.get_intervention(risk_level, signals)

        return {
            "risk_level": risk_level,
            "signals": signals,
            "recommendation": intervention.get("message", "Keep going. You're doing great."),
        }

    # ------------------------------------------------------------------
    # Intervention
    # ------------------------------------------------------------------

    async def get_intervention(self, risk_level: str, signals: Optional[list] = None) -> dict:
        """Get appropriate intervention based on risk level.

        - low:      encouraging message
        - medium:   suggest easier session, check in
        - high:     activate accountability partner, adjust difficulty
        - critical: direct outreach, offer break without chain penalty
        """
        if signals is None:
            full = await self.assess()
            signals = full["signals"]

        user = self.db.query(User).filter(User.id == self.user_id).first()
        streak = self.db.query(Streak).filter(Streak.user_id == self.user_id).first()
        name = user.name if user else "friend"
        current_streak = streak.current_streak if streak else 0

        # Build context for Gemini
        signal_descriptions = "; ".join(
            f"{s['signal']}: {s['detail']}" for s in signals
        ) if signals else "none detected"

        context = (
            f"User: {name}\n"
            f"Current streak: {current_streak} days\n"
            f"Risk level: {risk_level}\n"
            f"Burnout signals: {signal_descriptions}\n"
        )

        # Static fallbacks per risk level
        fallbacks = {
            "low": {
                "message": f"{name}, you're in a good rhythm. Keep showing up.",
                "suggested_action": "Do today's Seven 7 at your usual time.",
            },
            "medium": {
                "message": (
                    f"{name}, it's okay if things feel a bit harder lately. "
                    f"Try a lighter session today — just the first 3 blocks if that's all you have."
                ),
                "suggested_action": "Try just the PRIME and first BUILD block today.",
            },
            "high": {
                "message": (
                    f"{name}, I notice you've been pushing through some tough days. "
                    f"That takes real effort. Would it help to connect with someone "
                    f"who's on a similar streak?"
                ),
                "suggested_action": "Let me find you an accountability partner.",
            },
            "critical": {
                "message": (
                    f"{name}, showing up {current_streak} days is something to be proud of. "
                    f"If you need a breather, take it — your chain is safe for one day. "
                    f"Rest is part of the process."
                ),
                "suggested_action": "Use your streak save if you need rest today.",
            },
        }

        if not self.api_key:
            return fallbacks.get(risk_level, fallbacks["low"])

        try:
            content = await asyncio.wait_for(
                asyncio.to_thread(
                    _call_gemini, INTERVENTION_PROMPT, context, self.api_key
                ),
                timeout=15,
            )
            data = json.loads(content)
            return {
                "message": data.get("message", fallbacks[risk_level]["message"]),
                "suggested_action": data.get(
                    "suggested_action", fallbacks[risk_level]["suggested_action"]
                ),
            }
        except Exception:
            return fallbacks.get(risk_level, fallbacks["low"])

    # ------------------------------------------------------------------
    # Signal detection (private)
    # ------------------------------------------------------------------

    async def _detect_signals(self) -> list:
        """Scan all burnout signals and return the active ones."""
        signals = []
        now = datetime.utcnow()
        fourteen_days_ago = now - timedelta(days=14)
        seven_days_ago = now - timedelta(days=7)

        # Fetch data once
        recent_sessions = (
            self.db.query(Session)
            .filter(
                Session.user_id == self.user_id,
                Session.logged_at >= fourteen_days_ago,
            )
            .order_by(Session.logged_at.asc())
            .all()
        )

        recent_feedback = (
            self.db.query(SessionFeedback)
            .filter(
                SessionFeedback.user_id == self.user_id,
                SessionFeedback.created_at >= fourteen_days_ago,
            )
            .order_by(SessionFeedback.created_at.asc())
            .all()
        )

        # 1. declining_consistency — fewer sessions in last 7d vs prior 7d
        if len(recent_sessions) >= 2:
            first_week = [
                s for s in recent_sessions
                if s.logged_at and s.logged_at < seven_days_ago
            ]
            second_week = [
                s for s in recent_sessions
                if s.logged_at and s.logged_at >= seven_days_ago
            ]
            if len(first_week) > 0 and len(second_week) < len(first_week):
                drop = len(first_week) - len(second_week)
                signals.append({
                    "signal": "declining_consistency",
                    "description": self.BURNOUT_SIGNALS["declining_consistency"],
                    "detail": f"Dropped from {len(first_week)} to {len(second_week)} sessions week-over-week (down {drop})",
                })

        # 2. increasing_difficulty — last 3 feedbacks trending up
        difficulty_rated = [
            fb for fb in recent_feedback
            if fb.difficulty_rating is not None
        ]
        if len(difficulty_rated) >= 3:
            last_three = difficulty_rated[-3:]
            if (
                last_three[0].difficulty_rating is not None
                and last_three[2].difficulty_rating is not None
                and last_three[2].difficulty_rating > last_three[0].difficulty_rating
                and last_three[2].difficulty_rating >= 4
            ):
                signals.append({
                    "signal": "increasing_difficulty",
                    "description": self.BURNOUT_SIGNALS["increasing_difficulty"],
                    "detail": (
                        f"Difficulty went from {last_three[0].difficulty_rating} "
                        f"to {last_three[2].difficulty_rating}/5 over last 3 ratings"
                    ),
                })

        # 3. skipping_feedback — sessions in last 7d but no feedback
        sessions_last_7 = [
            s for s in recent_sessions
            if s.logged_at and s.logged_at >= seven_days_ago
        ]
        feedback_last_7 = [
            fb for fb in recent_feedback
            if fb.created_at and fb.created_at >= seven_days_ago
        ]
        if len(sessions_last_7) >= 3 and len(feedback_last_7) == 0:
            signals.append({
                "signal": "skipping_feedback",
                "description": self.BURNOUT_SIGNALS["skipping_feedback"],
                "detail": f"{len(sessions_last_7)} sessions in the last 7 days but zero feedback submitted",
            })

        # 4. late_sessions — session times drifting later
        timed_sessions = [
            s for s in recent_sessions if s.logged_at is not None
        ]
        if len(timed_sessions) >= 4:
            first_half = timed_sessions[: len(timed_sessions) // 2]
            second_half = timed_sessions[len(timed_sessions) // 2 :]
            avg_first = sum(s.logged_at.hour for s in first_half) / len(first_half)
            avg_second = sum(s.logged_at.hour for s in second_half) / len(second_half)
            if avg_second - avg_first >= 2.0:
                signals.append({
                    "signal": "late_sessions",
                    "description": self.BURNOUT_SIGNALS["late_sessions"],
                    "detail": (
                        f"Average session time shifted from ~{avg_first:.0f}:00 "
                        f"to ~{avg_second:.0f}:00"
                    ),
                })

        # 5. long_gaps — gaps between sessions growing
        if len(timed_sessions) >= 3:
            gaps = []
            for i in range(1, len(timed_sessions)):
                gap = (timed_sessions[i].logged_at - timed_sessions[i - 1].logged_at).total_seconds() / 3600
                gaps.append(gap)

            if len(gaps) >= 2:
                first_half_gaps = gaps[: len(gaps) // 2]
                second_half_gaps = gaps[len(gaps) // 2 :]
                avg_early = sum(first_half_gaps) / len(first_half_gaps)
                avg_late = sum(second_half_gaps) / len(second_half_gaps)
                # If average gap grew by more than 12 hours
                if avg_late - avg_early > 12:
                    signals.append({
                        "signal": "long_gaps",
                        "description": self.BURNOUT_SIGNALS["long_gaps"],
                        "detail": (
                            f"Average gap between sessions grew from "
                            f"{avg_early:.0f}h to {avg_late:.0f}h"
                        ),
                    })

        return signals
