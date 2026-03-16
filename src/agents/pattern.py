"""Pattern Agent — analyzes user behavior to generate personalized insights."""

import logging
from collections import Counter
from datetime import datetime, date, timedelta, timezone

from sqlalchemy.orm import Session as DBSession

from src.db.database import SessionLocal
from src.db.models import Session as SessionModel, Streak

logger = logging.getLogger(__name__)


class PatternAgent:
    """Analyzes a user's session history and streak data to produce insights."""

    def analyze(self, user_id: str) -> dict:
        """Return a PatternInsight dict for the given user."""
        db: DBSession = SessionLocal()
        try:
            return self._analyze(user_id, db)
        finally:
            db.close()

    def _analyze(self, user_id: str, db: DBSession) -> dict:
        now = datetime.now(timezone.utc)
        today = date.today()
        thirty_days_ago = now - timedelta(days=30)

        # --- Sessions ---
        sessions = (
            db.query(SessionModel)
            .filter(SessionModel.user_id == user_id)
            .order_by(SessionModel.logged_at.desc())
            .all()
        )
        total_sessions = len(sessions)

        if total_sessions == 0:
            logger.info("pattern.no_sessions user_id=%s", user_id)
            return self._empty_insight(user_id)

        # --- Streak record ---
        streak = db.query(Streak).filter(Streak.user_id == user_id).first()
        current_streak = streak.current_streak if streak else 0
        longest_streak = streak.longest_streak if streak else 0
        last_session_date = streak.last_session_date if streak else None

        # --- Days since last session ---
        if last_session_date:
            days_since_last = (today - last_session_date).days
        else:
            # Fall back to most recent session logged_at
            days_since_last = (now - sessions[0].logged_at).days

        # --- Completion rate (active days in last 30) ---
        recent_sessions = [
            s for s in sessions
            if s.logged_at and s.logged_at >= thirty_days_ago
        ]
        active_dates = {s.logged_at.date() for s in recent_sessions if s.logged_at}
        completion_rate = round(len(active_dates) / 30 * 100, 1)

        # --- Preferred time (most common hour) ---
        hours = [s.logged_at.hour for s in sessions if s.logged_at]
        preferred_time = Counter(hours).most_common(1)[0][0] if hours else None

        # --- Streak status ---
        streak_status = self._calc_streak_status(
            total_sessions, current_streak, days_since_last
        )

        # --- Favorite type (from seven7_title) ---
        titles = [s.seven7_title for s in sessions if s.seven7_title]
        favorite_type = Counter(titles).most_common(1)[0][0] if titles else None

        # --- Consistency score (0-100) ---
        consistency_score = self._calc_consistency(
            completion_rate, current_streak, total_sessions
        )

        insight = {
            "user_id": user_id,
            "total_sessions": total_sessions,
            "completion_rate": completion_rate,
            "preferred_time": preferred_time,
            "streak_status": streak_status,
            "days_since_last": days_since_last,
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "favorite_type": favorite_type,
            "consistency_score": consistency_score,
        }
        logger.info(
            "pattern.analyzed user_id=%s total=%d streak=%d score=%d",
            user_id, total_sessions, current_streak, consistency_score,
        )
        return insight

    # ------------------------------------------------------------------

    @staticmethod
    def _calc_streak_status(
        total_sessions: int, current_streak: int, days_since_last: int
    ) -> str:
        if total_sessions < 3:
            return "new"
        if days_since_last == 0 and current_streak <= 1:
            return "returned"
        if days_since_last >= 2:
            return "at_risk"
        if current_streak > 0:
            return "building"
        return "returned"

    @staticmethod
    def _calc_consistency(
        completion_rate: float, current_streak: int, total_sessions: int
    ) -> int:
        """Weighted score: 50% completion rate, 30% streak bonus, 20% volume."""
        rate_score = min(completion_rate, 100) * 0.5
        streak_score = min(current_streak / 30, 1.0) * 30
        volume_score = min(total_sessions / 60, 1.0) * 20
        return int(round(rate_score + streak_score + volume_score))

    @staticmethod
    def _empty_insight(user_id: str) -> dict:
        return {
            "user_id": user_id,
            "total_sessions": 0,
            "completion_rate": 0.0,
            "preferred_time": None,
            "streak_status": "new",
            "days_since_last": None,
            "current_streak": 0,
            "longest_streak": 0,
            "favorite_type": None,
            "consistency_score": 0,
        }
