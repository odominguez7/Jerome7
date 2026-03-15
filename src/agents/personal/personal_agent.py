"""Personal Agent — each user's own Jerome.

Orchestrates wellness monitoring, burnout detection, agent-to-agent
communication (mesh), and daily checkups. This is the single entry
point for everything that is *personal* to one user.
"""

import asyncio
import json
import os
from datetime import datetime, date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from src.db.models import (
    User, Streak, Session, SessionFeedback, Pod, PodMember,
    PodMemberStatus,
)
from src.agents.personal.wellness_monitor import WellnessMonitor
from src.agents.personal.burnout_detector import BurnoutDetector


def _call_gemini(system_prompt: str, user_content: str, api_key: str) -> str:
    """Call Gemini 2.5 Flash for personalized recommendations."""
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


CHECKUP_PROMPT = """You are Jerome — a personal wellness companion.
Given a user's daily data snapshot, generate a short, warm daily recommendation.

RULES:
- 1-2 sentences. Specific to their data.
- If their streak is healthy: celebrate + small nudge forward.
- If burnout risk > low: acknowledge effort, suggest one easy adjustment.
- Never say "workout", "exercise", "rep", or "set".
- Talk like a friend, not a coach.

Output JSON only:
{"recommendation": "your message", "focus": "streak|recovery|celebration|rest"}"""


MESH_PROMPT = """You are an agent acting on behalf of a Jerome 7 user.
Another agent sent you a message. Respond briefly and helpfully.
You represent your user's interests. Be warm but concise.

Output JSON only:
{"response": "your reply", "action": "none|nudge_user|schedule_checkin"}"""


class PersonalAgent:
    """Each user's personal AI agent — their own Jerome."""

    def __init__(self, user_id: str, db_session: DBSession):
        self.user_id = user_id
        self.db = db_session
        self.wellness_monitor = WellnessMonitor(user_id, db_session)
        self.burnout_detector = BurnoutDetector(user_id, db_session)
        self.api_key = os.getenv("GEMINI_API_KEY")

    # ------------------------------------------------------------------
    # Daily checkup
    # ------------------------------------------------------------------

    async def daily_checkup(self) -> dict:
        """Run a daily health checkup for this user.

        Returns:
            {
                wellness_score: float,
                burnout_risk: str,
                streak_health: dict,
                recommendation: str,
                focus: str,
            }
        """
        wellness_score = await self.wellness_monitor.calculate_wellness_score()
        burnout = await self.burnout_detector.assess()
        streak = self.db.query(Streak).filter(Streak.user_id == self.user_id).first()
        user = self.db.query(User).filter(User.id == self.user_id).first()

        streak_health = {
            "current": streak.current_streak if streak else 0,
            "longest": streak.longest_streak if streak else 0,
            "total_sessions": streak.total_sessions if streak else 0,
            "last_session_date": (
                streak.last_session_date.isoformat()
                if streak and streak.last_session_date else None
            ),
        }

        # Generate recommendation via Gemini
        name = user.name if user else "friend"
        risk_factors = await self.wellness_monitor.get_risk_factors()
        trend = await self.wellness_monitor.get_trend()

        context = (
            f"User: {name}\n"
            f"Wellness score: {wellness_score}/100\n"
            f"Trend: {trend}\n"
            f"Current streak: {streak_health['current']} days\n"
            f"Burnout risk: {burnout['risk_level']}\n"
            f"Active signals: {', '.join(s['signal'] for s in burnout['signals']) or 'none'}\n"
            f"Risk factors: {', '.join(risk_factors) or 'none'}\n"
        )

        recommendation = f"Hey {name}, you've got this. Show up for 7 minutes today."
        focus = "streak"

        if self.api_key:
            try:
                content = await asyncio.wait_for(
                    asyncio.to_thread(
                        _call_gemini, CHECKUP_PROMPT, context, self.api_key
                    ),
                    timeout=15,
                )
                data = json.loads(content)
                recommendation = data.get("recommendation", recommendation)
                focus = data.get("focus", focus)
            except Exception:
                # Use static fallback based on burnout risk
                if burnout["risk_level"] == "critical":
                    recommendation = f"{name}, rest is strength. Your chain is safe today if you need it."
                    focus = "rest"
                elif burnout["risk_level"] == "high":
                    recommendation = f"{name}, try just the first 3 blocks today. Showing up is the win."
                    focus = "recovery"
                elif streak_health["current"] > 0 and streak_health["current"] % 7 == 0:
                    recommendation = f"{name}, {streak_health['current']} days. That's a real streak. Keep going."
                    focus = "celebration"
        else:
            # No API key — static fallbacks
            if burnout["risk_level"] in ("high", "critical"):
                recommendation = f"{name}, it's okay to go easy today. Just show up."
                focus = "recovery"

        return {
            "wellness_score": wellness_score,
            "burnout_risk": burnout["risk_level"],
            "burnout_signals": burnout["signals"],
            "streak_health": streak_health,
            "trend": trend,
            "risk_factors": risk_factors,
            "recommendation": recommendation,
            "focus": focus,
        }

    # ------------------------------------------------------------------
    # Wellness analysis
    # ------------------------------------------------------------------

    async def analyze_wellness(self, days: int = 7) -> dict:
        """Analyze wellness trends over the last N days.

        Returns:
            {
                trend: str,
                consistency: float,
                difficulty_avg: float | None,
                mood_trend: str,
                sessions_completed: int,
                sessions_missed: int,
            }
        """
        now = datetime.utcnow()
        start = now - timedelta(days=days)

        # Sessions completed
        sessions_completed = (
            self.db.query(func.count(Session.id))
            .filter(
                Session.user_id == self.user_id,
                Session.logged_at >= start,
            )
            .scalar()
        ) or 0

        sessions_missed = max(0, days - sessions_completed)

        # Consistency: ratio of sessions to days
        consistency = round(sessions_completed / max(days, 1), 2)

        # Difficulty average
        avg_difficulty = (
            self.db.query(func.avg(SessionFeedback.difficulty_rating))
            .filter(
                SessionFeedback.user_id == self.user_id,
                SessionFeedback.created_at >= start,
            )
            .scalar()
        )
        difficulty_avg = round(float(avg_difficulty), 1) if avg_difficulty else None

        # Mood/enjoyment trend — compare first half vs second half
        midpoint = now - timedelta(days=days // 2)

        first_enjoyment = (
            self.db.query(func.avg(SessionFeedback.enjoyment_rating))
            .filter(
                SessionFeedback.user_id == self.user_id,
                SessionFeedback.created_at >= start,
                SessionFeedback.created_at < midpoint,
            )
            .scalar()
        )
        second_enjoyment = (
            self.db.query(func.avg(SessionFeedback.enjoyment_rating))
            .filter(
                SessionFeedback.user_id == self.user_id,
                SessionFeedback.created_at >= midpoint,
                SessionFeedback.created_at <= now,
            )
            .scalar()
        )

        if first_enjoyment is not None and second_enjoyment is not None:
            diff = float(second_enjoyment) - float(first_enjoyment)
            if diff > 0.3:
                mood_trend = "improving"
            elif diff < -0.3:
                mood_trend = "declining"
            else:
                mood_trend = "stable"
        else:
            mood_trend = "insufficient_data"

        trend = await self.wellness_monitor.get_trend(days=days)

        return {
            "trend": trend,
            "consistency": consistency,
            "difficulty_avg": difficulty_avg,
            "mood_trend": mood_trend,
            "sessions_completed": sessions_completed,
            "sessions_missed": sessions_missed,
        }

    # ------------------------------------------------------------------
    # Agent card (for mesh network)
    # ------------------------------------------------------------------

    async def get_agent_card(self) -> dict:
        """Return this agent's card for the mesh network.

        Used by the observatory and other agents to understand
        this user's current state at a glance.
        """
        user = self.db.query(User).filter(User.id == self.user_id).first()
        streak = self.db.query(Streak).filter(Streak.user_id == self.user_id).first()
        wellness_score = await self.wellness_monitor.calculate_wellness_score()
        trend = await self.wellness_monitor.get_trend()

        # Determine status
        if not streak or (streak.total_sessions or 0) == 0:
            status = "new"
        elif streak.last_session_date and (date.today() - streak.last_session_date).days == 0:
            status = "completed_today"
        elif streak.last_session_date and (date.today() - streak.last_session_date).days == 1:
            status = "on_track"
        elif streak.last_session_date and (date.today() - streak.last_session_date).days >= 2:
            status = "at_risk"
        else:
            status = "unknown"

        return {
            "user_id": self.user_id,
            "name": user.name if user else "Unknown",
            "timezone": user.timezone if user else "UTC",
            "goal": user.goal.value if user and user.goal else None,
            "fitness_level": user.fitness_level.value if user and user.fitness_level else "beginner",
            "streak_length": streak.current_streak if streak else 0,
            "longest_streak": streak.longest_streak if streak else 0,
            "total_sessions": streak.total_sessions if streak else 0,
            "wellness_score": wellness_score,
            "trend": trend,
            "status": status,
            "last_active": (
                user.last_active_at.isoformat() if user and user.last_active_at else None
            ),
        }

    # ------------------------------------------------------------------
    # Agent-to-agent communication (mesh)
    # ------------------------------------------------------------------

    async def communicate(self, other_agent_id: str, message: str) -> dict:
        """Send a message to another user's agent via the mesh.

        The other agent processes the message through Gemini and
        returns a response plus any action it decides to take.
        """
        # Load context about both agents
        my_card = await self.get_agent_card()
        other_user = self.db.query(User).filter(User.id == other_agent_id).first()
        other_streak = self.db.query(Streak).filter(Streak.user_id == other_agent_id).first()

        if not other_user:
            return {"response": "Agent not found.", "action": "none"}

        context = (
            f"You represent: {other_user.name} (streak: {other_streak.current_streak if other_streak else 0})\n"
            f"Message from {my_card['name']}'s agent (streak: {my_card['streak_length']}): {message}\n"
        )

        if not self.api_key:
            return {
                "response": f"{other_user.name}'s agent acknowledges your message.",
                "action": "none",
            }

        try:
            content = await asyncio.wait_for(
                asyncio.to_thread(
                    _call_gemini, MESH_PROMPT, context, self.api_key
                ),
                timeout=15,
            )
            data = json.loads(content)
            return {
                "response": data.get("response", "Acknowledged."),
                "action": data.get("action", "none"),
            }
        except Exception:
            return {
                "response": f"{other_user.name}'s agent acknowledges your message.",
                "action": "none",
            }

    # ------------------------------------------------------------------
    # Status summary (for observatory / human-readable)
    # ------------------------------------------------------------------

    async def get_status_summary(self) -> str:
        """Return a human-readable status summary for the observatory."""
        user = self.db.query(User).filter(User.id == self.user_id).first()
        streak = self.db.query(Streak).filter(Streak.user_id == self.user_id).first()
        wellness_score = await self.wellness_monitor.calculate_wellness_score()
        burnout = await self.burnout_detector.assess()
        trend = await self.wellness_monitor.get_trend()

        name = user.name if user else "Unknown"
        current = streak.current_streak if streak else 0
        longest = streak.longest_streak if streak else 0
        total = streak.total_sessions if streak else 0

        lines = [
            f"[{name}]",
            f"  Streak: {current} days (longest: {longest}, total sessions: {total})",
            f"  Wellness: {wellness_score}/100 ({trend})",
            f"  Burnout risk: {burnout['risk_level']}",
        ]

        if burnout["signals"]:
            signal_names = ", ".join(s["signal"] for s in burnout["signals"])
            lines.append(f"  Signals: {signal_names}")

        # Pod info
        membership = (
            self.db.query(PodMember)
            .filter(
                PodMember.user_id == self.user_id,
                PodMember.status == PodMemberStatus.active,
            )
            .first()
        )
        if membership:
            pod = self.db.query(Pod).filter(Pod.id == membership.pod_id).first()
            if pod:
                lines.append(f"  Accountability: {pod.name}")

        # Last session
        last_session = (
            self.db.query(Session)
            .filter(Session.user_id == self.user_id)
            .order_by(Session.logged_at.desc())
            .first()
        )
        if last_session and last_session.logged_at:
            lines.append(f"  Last session: {last_session.logged_at.strftime('%b %d, %H:%M')}")

        lines.append(f"  Recommendation: {burnout['recommendation']}")

        return "\n".join(lines)
