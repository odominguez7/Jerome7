"""Trend Analyzer — track and analyze wellness trends over time.

Uses session data, feedback, and streak history to surface patterns.
"""

from datetime import date, timedelta
from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from src.db.models import User, Streak, Session, SessionFeedback


class TrendAnalyzer:
    """Track and analyze wellness trends over time."""

    async def analyze_user_trend(
        self, user_id: str, db: DBSession, days: int = 14
    ) -> dict:
        """Analyze a user's wellness trend.

        Returns: {direction, confidence, data_points, prediction_next_7_days}
        """
        today = date.today()
        start_date = today - timedelta(days=days)

        # Get sessions grouped by date
        sessions = (
            db.query(Session)
            .filter(
                Session.user_id == user_id,
                func.date(Session.logged_at) >= start_date,
            )
            .order_by(Session.logged_at)
            .all()
        )

        # Get feedback in the same window
        feedback = (
            db.query(SessionFeedback)
            .filter(
                SessionFeedback.user_id == user_id,
                SessionFeedback.session_date >= start_date,
            )
            .order_by(SessionFeedback.session_date)
            .all()
        )

        # Build daily data points
        data_points = []
        sessions_by_date = defaultdict(list)
        for s in sessions:
            d = s.logged_at.date() if s.logged_at else None
            if d:
                sessions_by_date[d].append(s)

        feedback_by_date = {}
        for fb in feedback:
            feedback_by_date[fb.session_date] = fb

        for i in range(days):
            d = start_date + timedelta(days=i)
            day_sessions = sessions_by_date.get(d, [])
            day_fb = feedback_by_date.get(d)
            data_points.append({
                "date": d.isoformat(),
                "completed": len(day_sessions) > 0,
                "blocks_completed": (
                    day_fb.completed_blocks if day_fb and day_fb.completed_blocks else None
                ),
                "enjoyment": (
                    day_fb.enjoyment_rating if day_fb and day_fb.enjoyment_rating else None
                ),
                "difficulty": (
                    day_fb.difficulty_rating if day_fb and day_fb.difficulty_rating else None
                ),
            })

        # Calculate direction using two-halves comparison
        mid = days // 2
        first_half = data_points[:mid]
        second_half = data_points[mid:]

        first_completion = sum(1 for dp in first_half if dp["completed"])
        second_completion = sum(1 for dp in second_half if dp["completed"])

        first_enjoyment = [
            dp["enjoyment"] for dp in first_half if dp["enjoyment"] is not None
        ]
        second_enjoyment = [
            dp["enjoyment"] for dp in second_half if dp["enjoyment"] is not None
        ]

        # Determine direction
        completion_delta = second_completion - first_completion
        enjoy_delta = 0.0
        if first_enjoyment and second_enjoyment:
            enjoy_delta = (
                sum(second_enjoyment) / len(second_enjoyment)
                - sum(first_enjoyment) / len(first_enjoyment)
            )

        if completion_delta > 1 or enjoy_delta > 0.5:
            direction = "improving"
        elif completion_delta < -1 or enjoy_delta < -0.5:
            direction = "declining"
        else:
            direction = "stable"

        # Confidence based on data availability
        total_data_points = sum(
            1 for dp in data_points
            if dp["completed"] or dp["enjoyment"] is not None
        )
        confidence = min(total_data_points / days, 1.0)

        # Simple prediction: project recent 7-day rate forward
        last_7 = data_points[-7:] if len(data_points) >= 7 else data_points
        recent_rate = sum(1 for dp in last_7 if dp["completed"]) / len(last_7)
        predicted_sessions = round(recent_rate * 7, 1)

        return {
            "direction": direction,
            "confidence": round(confidence, 2),
            "data_points": data_points,
            "prediction_next_7_days": {
                "expected_sessions": predicted_sessions,
                "based_on_recent_rate": round(recent_rate, 2),
            },
        }

    async def analyze_global_trend(self, db: DBSession, days: int = 7) -> dict:
        """Analyze global community trends.

        Returns: {avg_wellness, participation_rate, trending_up_pct, trending_down_pct}
        """
        today = date.today()
        start_date = today - timedelta(days=days)

        # Total active users (have a streak record)
        total_users = db.query(Streak).count()
        if total_users == 0:
            return {
                "avg_wellness": 0,
                "participation_rate": 0,
                "trending_up_pct": 0,
                "trending_down_pct": 0,
                "total_users": 0,
                "active_in_period": 0,
            }

        # Users who logged at least one session in the period
        active_user_ids = (
            db.query(Session.user_id)
            .filter(func.date(Session.logged_at) >= start_date)
            .distinct()
            .all()
        )
        active_count = len(active_user_ids)
        participation_rate = round(active_count / total_users * 100, 1)

        # For each active user, determine if trending up or down
        trending_up = 0
        trending_down = 0

        for (uid,) in active_user_ids:
            user_trend = await self.analyze_user_trend(uid, db, days=days)
            if user_trend["direction"] == "improving":
                trending_up += 1
            elif user_trend["direction"] == "declining":
                trending_down += 1

        trending_up_pct = round(trending_up / max(active_count, 1) * 100, 1)
        trending_down_pct = round(trending_down / max(active_count, 1) * 100, 1)

        # Average wellness approximation: avg streak / 7 * 100 capped at 100
        avg_streak_result = db.query(func.avg(Streak.current_streak)).scalar()
        avg_streak = float(avg_streak_result) if avg_streak_result else 0
        avg_wellness = min(round(avg_streak / 7 * 100, 1), 100)

        return {
            "avg_wellness": avg_wellness,
            "participation_rate": participation_rate,
            "trending_up_pct": trending_up_pct,
            "trending_down_pct": trending_down_pct,
            "total_users": total_users,
            "active_in_period": active_count,
        }

    async def predict_churn(self, user_id: str, db: DBSession) -> dict:
        """Predict likelihood of user churning (breaking chain permanently).

        Returns: {churn_probability, risk_factors, suggested_intervention}
        """
        streak = db.query(Streak).filter(Streak.user_id == user_id).first()
        user = db.query(User).filter(User.id == user_id).first()

        if not streak or not user:
            return {
                "churn_probability": 1.0,
                "risk_factors": ["user_not_found"],
                "suggested_intervention": "re_engage",
            }

        risk_score = 0.0
        risk_factors = []
        today = date.today()

        # Factor 1: Days since last session (strongest signal)
        if streak.last_session_date:
            gap = (today - streak.last_session_date).days
            if gap >= 3:
                risk_score += 0.4
                risk_factors.append(f"inactive_{gap}_days")
            elif gap == 2:
                risk_score += 0.2
                risk_factors.append("missed_yesterday")
            elif gap == 1:
                risk_score += 0.05
        else:
            risk_score += 0.3
            risk_factors.append("never_logged_session")

        # Factor 2: Short streak after multiple breaks
        if streak.streak_broken_count >= 3 and streak.current_streak < 5:
            risk_score += 0.2
            risk_factors.append("repeated_streak_breaks")
        elif streak.streak_broken_count >= 2 and streak.current_streak < 3:
            risk_score += 0.15
            risk_factors.append("fragile_restart")

        # Factor 3: Low recent engagement
        week_ago = today - timedelta(days=7)
        recent_count = (
            db.query(Session)
            .filter(
                Session.user_id == user_id,
                func.date(Session.logged_at) >= week_ago,
            )
            .count()
        )
        if recent_count == 0:
            risk_score += 0.2
            risk_factors.append("zero_sessions_this_week")
        elif recent_count <= 2:
            risk_score += 0.1
            risk_factors.append("low_weekly_sessions")

        # Factor 4: Declining enjoyment (from feedback)
        recent_feedback = (
            db.query(SessionFeedback)
            .filter(
                SessionFeedback.user_id == user_id,
                SessionFeedback.session_date >= week_ago,
            )
            .order_by(SessionFeedback.session_date.desc())
            .limit(5)
            .all()
        )
        if recent_feedback:
            enjoyment = [
                f.enjoyment_rating for f in recent_feedback
                if f.enjoyment_rating is not None
            ]
            if len(enjoyment) >= 2 and all(e <= 2 for e in enjoyment[:2]):
                risk_score += 0.15
                risk_factors.append("low_enjoyment")

        # Factor 5: Account age vs streak (signed up long ago, low streak)
        if user.created_at:
            account_age_days = (today - user.created_at.date()).days
            if account_age_days > 30 and streak.current_streak < 5:
                risk_score += 0.1
                risk_factors.append("old_account_low_engagement")

        churn_probability = min(round(risk_score, 2), 1.0)

        # Suggest intervention
        if churn_probability >= 0.7:
            suggested = "offer_break"
        elif churn_probability >= 0.5:
            suggested = "activate_buddy"
        elif churn_probability >= 0.3:
            suggested = "ease_difficulty"
        else:
            suggested = "encourage"

        return {
            "churn_probability": churn_probability,
            "risk_factors": risk_factors,
            "suggested_intervention": suggested,
        }
