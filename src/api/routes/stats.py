"""GET /stats — public community stats for dynamic badges and embeds."""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import User, Streak, Session as SessionModel

router = APIRouter()


@router.get("/stats")
def public_stats(db: DBSession = Depends(get_db)):
    """Public stats JSON — used by shields.io dynamic badges in README."""
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)

    total_jeromes = db.query(User).count()
    total_sessions = db.query(SessionModel).count()
    active_streaks = db.query(Streak).filter(Streak.current_streak > 0).count()
    sessions_today = db.query(SessionModel).filter(
        SessionModel.logged_at >= today_start
    ).count()
    countries = (
        db.query(func.count(func.distinct(User.country)))
        .filter(User.country.isnot(None))
        .scalar()
    ) or 0
    top_streak = db.query(Streak).order_by(Streak.current_streak.desc()).first()

    return {
        "total_jeromes": total_jeromes,
        "total_sessions": total_sessions,
        "active_streaks": active_streaks,
        "sessions_today": sessions_today,
        "countries": countries,
        "longest_streak": top_streak.current_streak if top_streak else 0,
        "minutes_of_wellness": total_sessions * 7,
    }
