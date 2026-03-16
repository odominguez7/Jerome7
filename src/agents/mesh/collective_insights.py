"""CollectiveInsights — Aggregate intelligence from the agent mesh.

Analyzes patterns across all users to generate community-level insights
and proactive interventions. Uses Gemini for natural-language insight
generation when an API key is available.
"""

import asyncio
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, date, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from src.db.models import (
    User, Streak, Session, SessionFeedback, Event,
)


INSIGHT_EVENT_TYPE = "mesh:collective_insight"

INSIGHT_SYSTEM_PROMPT = """You are the Jerome 7 collective intelligence engine.
Given aggregated community data, generate 3-5 short, actionable insights.

Rules:
- Each insight is 1 sentence max.
- Reference specific numbers (percentages, counts, averages).
- Focus on patterns that a coach could act on.
- Never generic. Always tied to real data provided.
- Tone: analytical, concise, caring.

Output JSON only:
[
  {"type": "risk"|"trend"|"opportunity"|"celebration", "message": "..."}
]"""


def _call_gemini(system_prompt: str, user_content: str, api_key: str) -> str:
    """Call Gemini and return raw text response."""
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


class CollectiveInsights:
    """Generate collective insights from the agent mesh."""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")

    async def generate_daily_insights(self, db: DBSession) -> list:
        """Analyze all agents' data to generate collective insights.

        Gathers community-wide statistics and either uses Gemini to
        synthesize them into natural-language insights, or falls back
        to rule-based insight generation.
        """
        stats = await self._gather_community_stats(db)

        if self.api_key:
            try:
                insights = await self._gemini_insights(stats)
            except Exception as e:
                print(f"[CollectiveInsights] Gemini error, using rules: {e}")
                insights = self._rule_based_insights(stats)
        else:
            insights = self._rule_based_insights(stats)

        # Persist insights as events
        for insight in insights:
            event = Event(
                event_type=INSIGHT_EVENT_TYPE,
                payload={
                    "insight": insight,
                    "stats_snapshot": stats,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            db.add(event)
        if insights:
            db.commit()

        return insights

    async def get_burnout_risk_by_timezone(self, db: DBSession) -> dict:
        """Calculate burnout risk scores grouped by timezone.

        Risk factors per timezone cluster:
        - Declining streak counts
        - Increasing skip rates
        - Low enjoyment feedback
        - High difficulty feedback
        """
        users = db.query(User).all()
        tz_groups: dict[str, list] = defaultdict(list)
        for u in users:
            tz_groups[u.timezone].append(u.id)

        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        fourteen_days_ago = datetime.now(timezone.utc) - timedelta(days=14)

        results = {}
        for tz, user_ids in tz_groups.items():
            if not user_ids:
                continue

            # Sessions this week vs last week
            this_week = (
                db.query(func.count(Session.id))
                .filter(
                    Session.user_id.in_(user_ids),
                    Session.logged_at >= seven_days_ago,
                )
                .scalar()
            ) or 0

            last_week = (
                db.query(func.count(Session.id))
                .filter(
                    Session.user_id.in_(user_ids),
                    Session.logged_at >= fourteen_days_ago,
                    Session.logged_at < seven_days_ago,
                )
                .scalar()
            ) or 0

            # Session trend: negative means declining
            trend = 0.0
            if last_week > 0:
                trend = (this_week - last_week) / last_week

            # Average enjoyment this week
            enjoyments = (
                db.query(func.avg(SessionFeedback.enjoyment_rating))
                .filter(
                    SessionFeedback.user_id.in_(user_ids),
                    SessionFeedback.created_at >= seven_days_ago,
                )
                .scalar()
            )
            avg_enjoyment = float(enjoyments) if enjoyments else 3.0

            # Average difficulty this week
            difficulties = (
                db.query(func.avg(SessionFeedback.difficulty_rating))
                .filter(
                    SessionFeedback.user_id.in_(user_ids),
                    SessionFeedback.created_at >= seven_days_ago,
                )
                .scalar()
            )
            avg_difficulty = float(difficulties) if difficulties else 3.0

            # Compute risk score (0-100, higher = more at risk)
            risk = 50.0  # baseline

            # Declining sessions increase risk
            if trend < -0.2:
                risk += 20.0
            elif trend < 0:
                risk += 10.0
            elif trend > 0.2:
                risk -= 10.0

            # Low enjoyment increases risk
            if avg_enjoyment < 2.5:
                risk += 15.0
            elif avg_enjoyment < 3.0:
                risk += 5.0
            elif avg_enjoyment > 4.0:
                risk -= 10.0

            # Extreme difficulty increases risk
            if avg_difficulty > 4.0 or avg_difficulty < 1.5:
                risk += 10.0

            risk = max(0.0, min(100.0, risk))

            results[tz] = {
                "risk_score": round(risk, 1),
                "user_count": len(user_ids),
                "sessions_this_week": this_week,
                "sessions_last_week": last_week,
                "session_trend": round(trend * 100, 1),
                "avg_enjoyment": round(avg_enjoyment, 1),
                "avg_difficulty": round(avg_difficulty, 1),
            }

        return results

    async def get_collective_wellness_score(self, db: DBSession) -> float:
        """Calculate the overall community wellness score (0-100).

        Weighted components:
        - Active rate (users who logged in last 7 days): 30%
        - Average streak health: 25%
        - Enjoyment scores: 20%
        - Completion rate: 15%
        - Growth (new users): 10%
        """
        total_users = db.query(func.count(User.id)).scalar() or 0
        if total_users == 0:
            return 0.0

        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

        # Active rate
        active_users = (
            db.query(func.count(func.distinct(Session.user_id)))
            .filter(Session.logged_at >= seven_days_ago)
            .scalar()
        ) or 0
        active_rate = active_users / total_users
        active_score = min(100.0, active_rate * 100.0) * 0.30

        # Average streak health: ratio of current/longest
        streaks = db.query(Streak).all()
        streak_health = 0.0
        if streaks:
            healths = []
            for s in streaks:
                if s.longest_streak > 0:
                    healths.append(s.current_streak / s.longest_streak)
                elif s.current_streak > 0:
                    healths.append(1.0)
                else:
                    healths.append(0.0)
            streak_health = (sum(healths) / len(healths)) * 100.0
        streak_score = streak_health * 0.25

        # Enjoyment
        avg_enjoyment = (
            db.query(func.avg(SessionFeedback.enjoyment_rating))
            .filter(SessionFeedback.created_at >= seven_days_ago)
            .scalar()
        )
        enjoyment_pct = ((float(avg_enjoyment) / 5.0) * 100.0) if avg_enjoyment else 50.0
        enjoyment_score = enjoyment_pct * 0.20

        # Completion (sessions per user per week)
        if active_users > 0:
            total_sessions_week = (
                db.query(func.count(Session.id))
                .filter(Session.logged_at >= seven_days_ago)
                .scalar()
            ) or 0
            sessions_per_user = total_sessions_week / active_users
            completion_pct = min(100.0, (sessions_per_user / 7.0) * 100.0)
        else:
            completion_pct = 0.0
        completion_score = completion_pct * 0.15

        # Growth: new users in last 7 days
        new_users = (
            db.query(func.count(User.id))
            .filter(User.created_at >= seven_days_ago)
            .scalar()
        ) or 0
        growth_pct = min(100.0, (new_users / max(1, total_users)) * 500.0)  # amplified
        growth_score = growth_pct * 0.10

        total = active_score + streak_score + enjoyment_score + completion_score + growth_score
        return round(min(100.0, max(0.0, total)), 1)

    async def suggest_interventions(self, db: DBSession) -> list:
        """Suggest proactive interventions based on collective patterns.

        Checks for:
        1. Users with declining streaks who need a nudge
        2. Timezone clusters with high burnout risk
        3. Difficulty calibration needs
        4. Celebration opportunities (milestones approaching)
        """
        interventions = []
        today = date.today()
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

        # 1. At-risk users: had a streak > 3, no session in last 2 days
        two_days_ago = today - timedelta(days=2)
        at_risk_streaks = (
            db.query(Streak)
            .filter(
                Streak.current_streak >= 3,
                Streak.last_session_date <= two_days_ago,
            )
            .all()
        )
        for s in at_risk_streaks:
            user = db.query(User).filter(User.id == s.user_id).first()
            if user:
                interventions.append({
                    "type": "nudge",
                    "priority": "high",
                    "target_user": s.user_id,
                    "reason": (
                        f"{user.name} has a {s.current_streak}-day streak "
                        f"but hasn't logged in {(today - s.last_session_date).days} days"
                    ),
                    "action": "send_personalized_nudge",
                })

        # 2. Timezone clusters with burnout risk
        burnout_data = await self.get_burnout_risk_by_timezone(db)
        for tz, data in burnout_data.items():
            if data["risk_score"] > 70 and data["user_count"] >= 2:
                interventions.append({
                    "type": "session_adjust",
                    "priority": "medium",
                    "target_timezone": tz,
                    "reason": (
                        f"{tz} cluster ({data['user_count']} users) has "
                        f"{data['risk_score']}% burnout risk — "
                        f"sessions down {abs(data['session_trend'])}% WoW"
                    ),
                    "action": "reduce_difficulty_for_timezone",
                })

        # 3. Difficulty calibration
        avg_diff = (
            db.query(func.avg(SessionFeedback.difficulty_rating))
            .filter(SessionFeedback.created_at >= seven_days_ago)
            .scalar()
        )
        if avg_diff:
            avg_diff = float(avg_diff)
            if avg_diff > 4.0:
                interventions.append({
                    "type": "calibration",
                    "priority": "high",
                    "reason": (
                        f"Community avg difficulty is {avg_diff:.1f}/5 — "
                        f"sessions are too hard, increase skip risk"
                    ),
                    "action": "reduce_global_difficulty",
                })
            elif avg_diff < 2.0:
                interventions.append({
                    "type": "calibration",
                    "priority": "low",
                    "reason": (
                        f"Community avg difficulty is {avg_diff:.1f}/5 — "
                        f"sessions may be too easy, engagement could drop"
                    ),
                    "action": "increase_global_challenge",
                })

        # 4. Milestone celebrations
        milestones = [7, 14, 30, 50, 100, 200, 365]
        for m in milestones:
            approaching = (
                db.query(Streak)
                .filter(Streak.current_streak == m - 1)
                .all()
            )
            for s in approaching:
                user = db.query(User).filter(User.id == s.user_id).first()
                if user:
                    interventions.append({
                        "type": "celebration",
                        "priority": "medium",
                        "target_user": s.user_id,
                        "reason": (
                            f"{user.name} is 1 day away from a "
                            f"{m}-day milestone"
                        ),
                        "action": "prepare_milestone_celebration",
                    })

        return interventions

    # ---- Internal helpers ----

    async def _gather_community_stats(self, db: DBSession) -> dict:
        """Gather aggregate stats for Gemini input."""
        total_users = db.query(func.count(User.id)).scalar() or 0
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

        active_7d = (
            db.query(func.count(func.distinct(Session.user_id)))
            .filter(Session.logged_at >= seven_days_ago)
            .scalar()
        ) or 0

        sessions_7d = (
            db.query(func.count(Session.id))
            .filter(Session.logged_at >= seven_days_ago)
            .scalar()
        ) or 0

        avg_streak = (
            db.query(func.avg(Streak.current_streak)).scalar()
        )

        avg_enjoyment = (
            db.query(func.avg(SessionFeedback.enjoyment_rating))
            .filter(SessionFeedback.created_at >= seven_days_ago)
            .scalar()
        )

        avg_difficulty = (
            db.query(func.avg(SessionFeedback.difficulty_rating))
            .filter(SessionFeedback.created_at >= seven_days_ago)
            .scalar()
        )

        # Timezone distribution
        tz_counts = defaultdict(int)
        users = db.query(User.timezone).all()
        for (tz,) in users:
            tz_counts[tz] += 1

        # Goal distribution
        goal_counts = defaultdict(int)
        goals = db.query(User.goal).filter(User.goal.isnot(None)).all()
        for (g,) in goals:
            goal_counts[str(g)] += 1

        burnout = await self.get_burnout_risk_by_timezone(db)

        return {
            "total_users": total_users,
            "active_last_7_days": active_7d,
            "sessions_last_7_days": sessions_7d,
            "avg_streak": round(float(avg_streak), 1) if avg_streak else 0,
            "avg_enjoyment": round(float(avg_enjoyment), 1) if avg_enjoyment else None,
            "avg_difficulty": round(float(avg_difficulty), 1) if avg_difficulty else None,
            "timezone_distribution": dict(tz_counts),
            "goal_distribution": dict(goal_counts),
            "burnout_risk_by_tz": {
                tz: data["risk_score"] for tz, data in burnout.items()
            },
            "date": date.today().isoformat(),
        }

    async def _gemini_insights(self, stats: dict) -> list:
        """Use Gemini to generate natural-language insights from stats."""
        user_content = f"Community stats for {stats['date']}:\n{json.dumps(stats, indent=2)}"

        content = await asyncio.wait_for(
            asyncio.to_thread(
                _call_gemini, INSIGHT_SYSTEM_PROMPT, user_content, self.api_key
            ),
            timeout=20,
        )
        insights = json.loads(content)
        # Validate shape
        if not isinstance(insights, list):
            return []
        return [
            {"type": i.get("type", "trend"), "message": i.get("message", "")}
            for i in insights
            if i.get("message")
        ]

    def _rule_based_insights(self, stats: dict) -> list:
        """Generate insights using simple rules when Gemini is unavailable."""
        insights = []

        total = stats.get("total_users", 0)
        active = stats.get("active_last_7_days", 0)
        if total > 0:
            active_pct = round((active / total) * 100)
            if active_pct < 50:
                insights.append({
                    "type": "risk",
                    "message": (
                        f"Only {active_pct}% of users were active this week "
                        f"({active}/{total}). Consider a re-engagement campaign."
                    ),
                })
            elif active_pct > 80:
                insights.append({
                    "type": "celebration",
                    "message": (
                        f"{active_pct}% active rate this week — "
                        f"the community is showing up strong."
                    ),
                })

        avg_diff = stats.get("avg_difficulty")
        if avg_diff and avg_diff > 4.0:
            insights.append({
                "type": "risk",
                "message": (
                    f"Average difficulty is {avg_diff}/5 — sessions are "
                    f"too hard. Expect higher skip rates tomorrow."
                ),
            })

        avg_enjoy = stats.get("avg_enjoyment")
        if avg_enjoy and avg_enjoy < 2.5:
            insights.append({
                "type": "risk",
                "message": (
                    f"Enjoyment dropped to {avg_enjoy}/5 this week. "
                    f"Add more playful blocks to upcoming sessions."
                ),
            })

        burnout = stats.get("burnout_risk_by_tz", {})
        high_risk_tzs = [tz for tz, score in burnout.items() if score > 70]
        if high_risk_tzs:
            insights.append({
                "type": "risk",
                "message": (
                    f"High burnout risk in {', '.join(high_risk_tzs)} — "
                    f"consider lighter sessions for those regions."
                ),
            })

        avg_streak = stats.get("avg_streak", 0)
        if avg_streak > 7:
            insights.append({
                "type": "trend",
                "message": (
                    f"Average streak is {avg_streak} days — "
                    f"the habit is forming across the community."
                ),
            })

        return insights[:5]
