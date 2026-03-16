"""Wellness Monitor — tracks a user's health patterns over time.

Combines streak data, session completion, feedback sentiment,
and nudge responsiveness into a single wellness score (0-100).
"""

from datetime import datetime, date, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from src.db.models import (
    Streak, Session, SessionFeedback, Nudge,
)


class WellnessMonitor:
    """Monitors a user's wellness patterns over time."""

    def __init__(self, user_id: str, db: DBSession):
        self.user_id = user_id
        self.db = db

    # ------------------------------------------------------------------
    # Core score
    # ------------------------------------------------------------------

    async def calculate_wellness_score(self) -> float:
        """Calculate a 0-100 wellness score.

        Weights:
            - Streak consistency   40%
            - Completion rate 7d   30%
            - Feedback sentiment   20%
            - Nudge responsiveness 10%
        """
        consistency = await self._streak_consistency_score()
        completion = await self._completion_rate_score()
        sentiment = await self._feedback_sentiment_score()
        nudge_resp = await self._nudge_response_score()

        score = (
            consistency * 0.40
            + completion * 0.30
            + sentiment * 0.20
            + nudge_resp * 0.10
        )
        return round(min(100.0, max(0.0, score)), 1)

    # ------------------------------------------------------------------
    # Trend
    # ------------------------------------------------------------------

    async def get_trend(self, days: int = 14) -> str:
        """Return trend direction over the last *days* days.

        Returns one of: 'improving', 'stable', 'declining', 'new_user'.
        Compares the first-half score proxy to the second-half score proxy.
        """
        streak = (
            self.db.query(Streak)
            .filter(Streak.user_id == self.user_id)
            .first()
        )
        if not streak or (streak.total_sessions or 0) < 4:
            return "new_user"

        now = datetime.now(timezone.utc)
        midpoint = now - timedelta(days=days // 2)
        start = now - timedelta(days=days)

        first_half_sessions = (
            self.db.query(func.count(Session.id))
            .filter(
                Session.user_id == self.user_id,
                Session.logged_at >= start,
                Session.logged_at < midpoint,
            )
            .scalar()
        ) or 0

        second_half_sessions = (
            self.db.query(func.count(Session.id))
            .filter(
                Session.user_id == self.user_id,
                Session.logged_at >= midpoint,
                Session.logged_at <= now,
            )
            .scalar()
        ) or 0

        # Also factor in difficulty trend
        first_diff = (
            self.db.query(func.avg(SessionFeedback.difficulty_rating))
            .filter(
                SessionFeedback.user_id == self.user_id,
                SessionFeedback.created_at >= start,
                SessionFeedback.created_at < midpoint,
            )
            .scalar()
        )
        second_diff = (
            self.db.query(func.avg(SessionFeedback.difficulty_rating))
            .filter(
                SessionFeedback.user_id == self.user_id,
                SessionFeedback.created_at >= midpoint,
                SessionFeedback.created_at <= now,
            )
            .scalar()
        )

        # Session count comparison (primary signal)
        half_days = max(days // 2, 1)
        first_rate = first_half_sessions / half_days
        second_rate = second_half_sessions / half_days

        delta = second_rate - first_rate

        # Difficulty going up = declining wellness
        diff_delta = 0.0
        if first_diff is not None and second_diff is not None:
            diff_delta = (second_diff - first_diff) * -0.1  # invert: harder = worse

        combined = delta + diff_delta

        if combined > 0.08:
            return "improving"
        elif combined < -0.08:
            return "declining"
        return "stable"

    # ------------------------------------------------------------------
    # Risk factors
    # ------------------------------------------------------------------

    async def get_risk_factors(self) -> list:
        """Identify current risk factors for this user."""
        risks = []
        now = datetime.now(timezone.utc)

        # 1. missed_2_days — close to chain break
        streak = (
            self.db.query(Streak)
            .filter(Streak.user_id == self.user_id)
            .first()
        )
        if streak and streak.last_session_date:
            days_since = (date.today() - streak.last_session_date).days
            if days_since >= 2 and streak.current_streak > 0:
                risks.append("missed_2_days")

        # 2. difficulty_too_high — rated hard (>=4) 3+ times in a row
        recent_fb = (
            self.db.query(SessionFeedback)
            .filter(SessionFeedback.user_id == self.user_id)
            .order_by(SessionFeedback.created_at.desc())
            .limit(3)
            .all()
        )
        if len(recent_fb) >= 3:
            all_hard = all(
                fb.difficulty_rating is not None and fb.difficulty_rating >= 4
                for fb in recent_fb
            )
            if all_hard:
                risks.append("difficulty_too_high")

        # 3. no_feedback — has sessions in the last 7 days but zero feedback
        seven_days_ago = now - timedelta(days=7)
        recent_session_count = (
            self.db.query(func.count(Session.id))
            .filter(
                Session.user_id == self.user_id,
                Session.logged_at >= seven_days_ago,
            )
            .scalar()
        ) or 0

        recent_feedback_count = (
            self.db.query(func.count(SessionFeedback.id))
            .filter(
                SessionFeedback.user_id == self.user_id,
                SessionFeedback.created_at >= seven_days_ago,
            )
            .scalar()
        ) or 0

        if recent_session_count >= 3 and recent_feedback_count == 0:
            risks.append("no_feedback")

        # 4. irregular_timing — session times vary wildly (std dev > 4 hours)
        recent_sessions = (
            self.db.query(Session)
            .filter(
                Session.user_id == self.user_id,
                Session.logged_at >= seven_days_ago,
            )
            .order_by(Session.logged_at.desc())
            .all()
        )
        if len(recent_sessions) >= 3:
            hours = [s.logged_at.hour + s.logged_at.minute / 60.0 for s in recent_sessions if s.logged_at]
            if hours:
                mean_h = sum(hours) / len(hours)
                variance = sum((h - mean_h) ** 2 for h in hours) / len(hours)
                std_dev = variance ** 0.5
                if std_dev > 4.0:
                    risks.append("irregular_timing")

        return risks

    # ------------------------------------------------------------------
    # Private scoring helpers
    # ------------------------------------------------------------------

    async def _streak_consistency_score(self) -> float:
        """0-100 based on current streak relative to longest, plus recency."""
        streak = (
            self.db.query(Streak)
            .filter(Streak.user_id == self.user_id)
            .first()
        )
        if not streak:
            return 0.0

        current = streak.current_streak or 0
        longest = streak.longest_streak or 1

        # Ratio of current to longest (max out at 1.0)
        ratio = min(current / max(longest, 1), 1.0)

        # Bonus for absolute streak length (caps at 30 days = full bonus)
        length_bonus = min(current / 30.0, 1.0) * 20

        # Penalty if last session was more than 1 day ago
        penalty = 0.0
        if streak.last_session_date:
            days_gap = (date.today() - streak.last_session_date).days
            if days_gap >= 2:
                penalty = min(days_gap * 10, 40)

        return min(100.0, ratio * 80 + length_bonus - penalty)

    async def _completion_rate_score(self) -> float:
        """0-100 based on sessions completed in the last 7 days (target: 7/7)."""
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        count = (
            self.db.query(func.count(Session.id))
            .filter(
                Session.user_id == self.user_id,
                Session.logged_at >= seven_days_ago,
            )
            .scalar()
        ) or 0

        # 7 sessions in 7 days = 100
        return min(100.0, (count / 7.0) * 100)

    async def _feedback_sentiment_score(self) -> float:
        """0-100 derived from difficulty and enjoyment ratings.

        Low difficulty + high enjoyment = high score.
        Missing feedback = neutral 50.
        """
        recent_fb = (
            self.db.query(SessionFeedback)
            .filter(SessionFeedback.user_id == self.user_id)
            .order_by(SessionFeedback.created_at.desc())
            .limit(5)
            .all()
        )
        if not recent_fb:
            return 50.0  # neutral when no data

        difficulties = [fb.difficulty_rating for fb in recent_fb if fb.difficulty_rating is not None]
        enjoyments = [fb.enjoyment_rating for fb in recent_fb if fb.enjoyment_rating is not None]

        # Difficulty: 1 is great (100), 5 is bad (0)
        diff_score = 50.0
        if difficulties:
            avg_diff = sum(difficulties) / len(difficulties)
            diff_score = max(0, (5 - avg_diff) / 4 * 100)

        # Enjoyment: 5 is great (100), 1 is bad (0)
        enj_score = 50.0
        if enjoyments:
            avg_enj = sum(enjoyments) / len(enjoyments)
            enj_score = max(0, (avg_enj - 1) / 4 * 100)

        return (diff_score + enj_score) / 2

    async def _nudge_response_score(self) -> float:
        """0-100 based on how often the user acts on nudges.

        No nudges sent = full score (they don't need nudges).
        """
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        nudges = (
            self.db.query(Nudge)
            .filter(
                Nudge.user_id == self.user_id,
                Nudge.sent_at >= thirty_days_ago,
            )
            .all()
        )
        if not nudges:
            return 100.0  # no nudges needed = healthy

        acted_count = sum(1 for n in nudges if n.acted_on)
        total = len(nudges)

        return (acted_count / total) * 100 if total else 100.0
