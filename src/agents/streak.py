"""Streak Agent — consistency tracking with soul.

Streak rules (these are the product soul):
  - Broken only after 3 consecutive missed days, not 1.
  - One save per 30 days (travel, illness, emergency).
  - Longest streak never resets — it is the permanent personal record.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from src.agents.context import UserContext, MILESTONES
from src.db.models import Streak


@dataclass
class StreakUpdate:
    previous: int
    new: int
    milestone_reached: Optional[int] = None
    broken: bool = False


@dataclass
class StreakRisk:
    at_risk: bool
    hours_remaining: int = 0
    last_window_today: Optional[str] = None


class StreakAgent:

    def update_streak(self, user_id: str, logged_at, db: DBSession) -> StreakUpdate:
        """Update streak after a session is logged."""
        streak = db.query(Streak).filter(Streak.user_id == user_id).first()
        if not streak:
            streak = Streak(user_id=user_id, current_streak=0, longest_streak=0,
                            total_sessions=0, streak_broken_count=0, saves_used=0)
            db.add(streak)
            db.flush()

        today = date.today()
        previous = streak.current_streak

        if streak.last_session_date == today:
            # Duplicate log today — no change
            return StreakUpdate(previous=previous, new=previous)

        if streak.last_session_date is None:
            # First ever session
            streak.current_streak = 1
        elif streak.last_session_date == today - timedelta(days=1):
            # Consecutive day — increment
            streak.current_streak += 1
        elif streak.last_session_date == today - timedelta(days=2):
            # 2 days ago — still safe (not broken yet)
            streak.current_streak += 1
        elif streak.last_session_date and (today - streak.last_session_date).days >= 3:
            # 3+ days — streak broken, reset to 1
            streak.current_streak = 1
            streak.streak_broken_count += 1
        else:
            streak.current_streak += 1

        streak.last_session_date = today
        streak.total_sessions += 1

        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak

        db.commit()

        milestone = self.check_milestones_value(streak.current_streak)

        return StreakUpdate(
            previous=previous,
            new=streak.current_streak,
            milestone_reached=milestone,
            broken=previous > 0 and streak.current_streak == 1 and previous != 1,
        )

    def assess_risk(self, ctx: UserContext) -> StreakRisk:
        """Assess whether the user's streak is at risk today."""
        if ctx.current_streak == 0:
            return StreakRisk(at_risk=False)

        # If they already logged today, no risk
        if ctx.sessions_last_7_days and ctx.sessions_last_7_days[0].get("date") == date.today().isoformat():
            return StreakRisk(at_risk=False)

        from datetime import datetime
        now = datetime.utcnow()
        hours_left = max(0, 24 - now.hour)

        at_risk = hours_left < 6  # at risk if less than 6 hours left in day
        return StreakRisk(at_risk=at_risk, hours_remaining=hours_left)

    def check_milestones(self, ctx: UserContext) -> Optional[int]:
        """Return the milestone just hit, or None."""
        return self.check_milestones_value(ctx.current_streak)

    def check_milestones_value(self, current_streak: int) -> Optional[int]:
        """Check if current streak value hits a milestone."""
        if current_streak in MILESTONES:
            return current_streak
        return None

    def use_save(self, user_id: str, db: DBSession) -> bool:
        """Use a streak save. Max 1 per 30 days."""
        streak = db.query(Streak).filter(Streak.user_id == user_id).first()
        if not streak:
            return False

        today = date.today()
        if streak.last_save_date and (today - streak.last_save_date).days < 30:
            return False

        streak.saves_used += 1
        streak.last_save_date = today
        # Extend the last_session_date to today so streak doesn't break
        streak.last_session_date = today
        db.commit()
        return True

    def get_chain(self, user_id: str, db: DBSession, days: int = 30) -> list[str]:
        """Get visual chain data for the last N days."""
        from src.db.models import Session
        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)
        sessions = (
            db.query(Session)
            .filter(Session.user_id == user_id, Session.logged_at >= cutoff)
            .all()
        )
        session_dates = {s.logged_at.date() for s in sessions if s.logged_at}

        chain = []
        for i in range(days - 1, -1, -1):
            d = date.today() - timedelta(days=i)
            chain.append("filled" if d in session_dates else "empty")
        return chain
