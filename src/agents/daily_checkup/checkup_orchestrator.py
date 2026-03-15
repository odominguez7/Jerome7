"""Checkup Orchestrator — run daily health checkups at scale across all users.

Powered by Google Gemini 2.5 Flash.
"""

import asyncio
import json
import os
from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from src.db.models import User, Streak, Session, SessionFeedback, Event


def _call_gemini(system_prompt: str, user_content: str, api_key: str) -> str:
    """Call Gemini 2.5 Flash and return raw text response."""
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


INSIGHT_SYSTEM_PROMPT = """You are Jerome's wellness analyst.
Given aggregate checkup data for a community, produce 3-5 actionable insights.

Output JSON only:
{"insights": ["insight 1", "insight 2", ...]}

Rules:
- Be specific. Reference numbers.
- Suggest one concrete action per insight.
- Never generic motivational fluff."""


class CheckupOrchestrator:
    """Run daily health checkups at scale across all users."""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")

    async def run_all_checkups(self, db: DBSession) -> dict:
        """Run checkups for all active users. Returns summary.

        - Get all users with active streaks
        - Calculate wellness score for each
        - Identify at-risk users
        - Generate collective report
        Returns: {total_checked, healthy, at_risk, critical, insights}
        """
        # Get all users with active streaks (current_streak > 0)
        active_streaks = (
            db.query(Streak)
            .filter(Streak.current_streak > 0)
            .all()
        )

        results = {
            "total_checked": 0,
            "healthy": 0,
            "at_risk": 0,
            "critical": 0,
            "user_reports": [],
            "insights": [],
        }

        for streak in active_streaks:
            report = await self.run_single_checkup(streak.user_id, db)
            results["total_checked"] += 1
            results["user_reports"].append(report)

            score = report["wellness_score"]
            if score >= 70:
                results["healthy"] += 1
            elif score >= 40:
                results["at_risk"] += 1
            else:
                results["critical"] += 1

        # Generate collective insights via Gemini
        if results["total_checked"] > 0 and self.api_key:
            results["insights"] = await self._generate_insights(results)

        # Log the checkup run as an event
        event = Event(
            event_type="daily_checkup_run",
            payload={
                "total_checked": results["total_checked"],
                "healthy": results["healthy"],
                "at_risk": results["at_risk"],
                "critical": results["critical"],
                "run_at": datetime.utcnow().isoformat(),
            },
        )
        db.add(event)
        db.commit()

        return results

    async def run_single_checkup(self, user_id: str, db: DBSession) -> dict:
        """Run checkup for one user.

        Returns: {user_id, wellness_score, trend, risk_factors, recommendation}
        """
        streak = db.query(Streak).filter(Streak.user_id == user_id).first()
        user = db.query(User).filter(User.id == user_id).first()

        if not streak or not user:
            return {
                "user_id": user_id,
                "wellness_score": 0,
                "trend": "unknown",
                "risk_factors": ["user_not_found"],
                "recommendation": "Re-engage user.",
            }

        # Gather data points for wellness score calculation
        today = date.today()
        week_ago = today - timedelta(days=7)
        two_weeks_ago = today - timedelta(days=14)

        # Sessions in last 7 days
        recent_sessions = (
            db.query(Session)
            .filter(
                Session.user_id == user_id,
                func.date(Session.logged_at) >= week_ago,
            )
            .all()
        )

        # Sessions in prior 7 days (for trend)
        prior_sessions = (
            db.query(Session)
            .filter(
                Session.user_id == user_id,
                func.date(Session.logged_at) >= two_weeks_ago,
                func.date(Session.logged_at) < week_ago,
            )
            .all()
        )

        # Recent feedback
        recent_feedback = (
            db.query(SessionFeedback)
            .filter(
                SessionFeedback.user_id == user_id,
                SessionFeedback.session_date >= week_ago,
            )
            .order_by(SessionFeedback.session_date.desc())
            .limit(7)
            .all()
        )

        # Calculate wellness score (0-100)
        score = self._calculate_wellness_score(
            streak=streak,
            recent_sessions=recent_sessions,
            recent_feedback=recent_feedback,
        )

        # Determine trend
        recent_count = len(recent_sessions)
        prior_count = len(prior_sessions)
        if recent_count > prior_count:
            trend = "improving"
        elif recent_count < prior_count:
            trend = "declining"
        else:
            trend = "stable"

        # Identify risk factors
        risk_factors = self._identify_risk_factors(
            streak=streak,
            recent_sessions=recent_sessions,
            recent_feedback=recent_feedback,
            today=today,
        )

        # Generate recommendation
        recommendation = self._generate_recommendation(score, risk_factors, user.name)

        return {
            "user_id": user_id,
            "wellness_score": score,
            "trend": trend,
            "risk_factors": risk_factors,
            "recommendation": recommendation,
        }

    def _calculate_wellness_score(
        self,
        streak: Streak,
        recent_sessions: list,
        recent_feedback: list,
    ) -> int:
        """Calculate a 0-100 wellness score from multiple signals."""
        score = 0

        # Consistency: sessions in last 7 days (max 35 pts)
        session_count = len(recent_sessions)
        score += min(session_count * 5, 35)

        # Streak health: current streak length (max 25 pts)
        streak_pts = min(streak.current_streak * 2.5, 25)
        score += int(streak_pts)

        # Enjoyment: average enjoyment rating (max 20 pts)
        if recent_feedback:
            enjoyment_ratings = [
                f.enjoyment_rating for f in recent_feedback
                if f.enjoyment_rating is not None
            ]
            if enjoyment_ratings:
                avg_enjoy = sum(enjoyment_ratings) / len(enjoyment_ratings)
                score += int(avg_enjoy * 4)  # 5 * 4 = 20 max

        # Completion: average blocks completed (max 20 pts)
        if recent_feedback:
            completion_ratings = [
                f.completed_blocks for f in recent_feedback
                if f.completed_blocks is not None
            ]
            if completion_ratings:
                avg_completion = sum(completion_ratings) / len(completion_ratings)
                score += int((avg_completion / 7) * 20)

        return min(score, 100)

    def _identify_risk_factors(
        self,
        streak: Streak,
        recent_sessions: list,
        recent_feedback: list,
        today: date,
    ) -> list:
        """Identify risk factors for a user."""
        risks = []

        # No session today
        if streak.last_session_date and streak.last_session_date < today:
            days_gap = (today - streak.last_session_date).days
            if days_gap >= 2:
                risks.append(f"no_session_in_{days_gap}_days")
            elif days_gap == 1:
                risks.append("no_session_today")

        # Low session count this week
        if len(recent_sessions) < 3:
            risks.append("low_weekly_frequency")

        # Declining enjoyment
        if recent_feedback and len(recent_feedback) >= 3:
            enjoyment = [
                f.enjoyment_rating for f in recent_feedback
                if f.enjoyment_rating is not None
            ]
            if len(enjoyment) >= 3 and enjoyment[0] is not None and enjoyment[-1] is not None:
                if enjoyment[0] < enjoyment[-1]:  # most recent < oldest (desc order)
                    risks.append("declining_enjoyment")

        # Pain / body notes
        if recent_feedback:
            pain_keywords = {"pain", "hurt", "sore", "injured", "ache"}
            for fb in recent_feedback[:3]:
                if fb.body_note:
                    if any(kw in fb.body_note.lower() for kw in pain_keywords):
                        risks.append("reported_pain")
                        break

        # High difficulty
        if recent_feedback:
            diff_ratings = [
                f.difficulty_rating for f in recent_feedback
                if f.difficulty_rating is not None
            ]
            if diff_ratings:
                avg_diff = sum(diff_ratings) / len(diff_ratings)
                if avg_diff > 4.0:
                    risks.append("sessions_too_hard")

        # Streak broken recently
        if streak.streak_broken_count > 0 and streak.current_streak < 3:
            risks.append("recently_restarted")

        return risks

    def _generate_recommendation(
        self, score: int, risk_factors: list, name: str
    ) -> str:
        """Generate a simple recommendation string based on score and risks."""
        if score >= 80:
            return f"{name} is thriving. Keep the current rhythm."
        if score >= 60:
            if "declining_enjoyment" in risk_factors:
                return f"Mix it up for {name} — variety could reignite the spark."
            return f"{name} is steady. A small challenge could level them up."
        if score >= 40:
            if "reported_pain" in risk_factors:
                return f"Check in with {name} about physical discomfort. Suggest gentler sessions."
            if "sessions_too_hard" in risk_factors:
                return f"Ease the difficulty for {name}. Completion matters more than intensity."
            return f"{name} needs encouragement. A nudge and an easier session could help."
        # Critical
        if "recently_restarted" in risk_factors:
            return f"{name} just came back. Go extra gentle — the goal is just showing up."
        return f"{name} is at risk of dropping off. Activate buddy system or offer a pause."

    async def _generate_insights(self, results: dict) -> list:
        """Use Gemini to generate collective insights from checkup data."""
        summary = (
            f"Total users checked: {results['total_checked']}. "
            f"Healthy: {results['healthy']}. "
            f"At risk: {results['at_risk']}. "
            f"Critical: {results['critical']}. "
        )

        # Aggregate risk factors
        all_risks = {}
        for report in results["user_reports"]:
            for risk in report["risk_factors"]:
                all_risks[risk] = all_risks.get(risk, 0) + 1

        summary += f"Top risk factors: {json.dumps(all_risks)}."

        try:
            content = await asyncio.wait_for(
                asyncio.to_thread(
                    _call_gemini, INSIGHT_SYSTEM_PROMPT, summary, self.api_key
                ),
                timeout=20,
            )
            data = json.loads(content)
            return data.get("insights", [])
        except Exception as e:
            print(f"[CheckupOrchestrator] Insight generation failed: {e}")
            return [
                f"{results['at_risk'] + results['critical']} users need attention today."
            ]
