"""GET /analytics — aggregate intelligence layer for Jerome7."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import User, Streak, Session as SessionModel, SessionFeedback

router = APIRouter()


@router.get("/analytics/overview")
def analytics_overview(db: DBSession = Depends(get_db)):
    """Global stats — total users, sessions, active streaks, countries."""
    total_users = db.query(User).count()
    total_sessions = db.query(SessionModel).count()
    active_streaks = db.query(Streak).filter(Streak.current_streak > 0).count()

    # Sessions in last 24h / 7d / 30d
    now = datetime.utcnow()
    sessions_24h = db.query(SessionModel).filter(
        SessionModel.logged_at >= now - timedelta(hours=24)
    ).count()
    sessions_7d = db.query(SessionModel).filter(
        SessionModel.logged_at >= now - timedelta(days=7)
    ).count()
    sessions_30d = db.query(SessionModel).filter(
        SessionModel.logged_at >= now - timedelta(days=30)
    ).count()

    # Country distribution
    countries = (
        db.query(User.country, func.count(User.id))
        .filter(User.country.isnot(None))
        .group_by(User.country)
        .order_by(func.count(User.id).desc())
        .all()
    )

    # Source distribution
    sources = (
        db.query(User.source, func.count(User.id))
        .filter(User.source.isnot(None))
        .group_by(User.source)
        .order_by(func.count(User.id).desc())
        .all()
    )

    # Age bracket distribution
    age_brackets = (
        db.query(User.age_bracket, func.count(User.id))
        .filter(User.age_bracket.isnot(None))
        .group_by(User.age_bracket)
        .order_by(func.count(User.id).desc())
        .all()
    )

    # Goal distribution
    goals = (
        db.query(User.goal, func.count(User.id))
        .filter(User.goal.isnot(None))
        .group_by(User.goal)
        .order_by(func.count(User.id).desc())
        .all()
    )

    # Average difficulty from feedback (last 30 days)
    avg_difficulty = (
        db.query(func.avg(SessionFeedback.difficulty_rating))
        .filter(SessionFeedback.created_at >= now - timedelta(days=30))
        .scalar()
    )

    # Streak distribution buckets
    streak_buckets = {
        "1-3": db.query(Streak).filter(Streak.current_streak.between(1, 3)).count(),
        "4-7": db.query(Streak).filter(Streak.current_streak.between(4, 7)).count(),
        "8-14": db.query(Streak).filter(Streak.current_streak.between(8, 14)).count(),
        "15-30": db.query(Streak).filter(Streak.current_streak.between(15, 30)).count(),
        "31+": db.query(Streak).filter(Streak.current_streak >= 31).count(),
    }

    return {
        "total_users": total_users,
        "total_sessions": total_sessions,
        "active_streaks": active_streaks,
        "sessions": {
            "last_24h": sessions_24h,
            "last_7d": sessions_7d,
            "last_30d": sessions_30d,
        },
        "demographics": {
            "countries": {c: n for c, n in countries},
            "sources": {str(s): n for s, n in sources},
            "age_brackets": {str(a): n for a, n in age_brackets},
            "goals": {str(g): n for g, n in goals},
        },
        "avg_difficulty_30d": round(avg_difficulty, 1) if avg_difficulty else None,
        "streak_distribution": streak_buckets,
    }


@router.get("/analytics/retention")
def analytics_retention(db: DBSession = Depends(get_db)):
    """Retention metrics — who keeps showing up."""
    now = datetime.utcnow()

    # Users who signed up in last 30 days
    new_users_30d = db.query(User).filter(
        User.created_at >= now - timedelta(days=30)
    ).count()

    # Of those, how many logged at least 1 session
    new_user_ids = [
        u.id for u in db.query(User.id).filter(
            User.created_at >= now - timedelta(days=30)
        ).all()
    ]
    activated = 0
    retained_7d = 0
    if new_user_ids:
        activated = (
            db.query(func.count(func.distinct(SessionModel.user_id)))
            .filter(SessionModel.user_id.in_(new_user_ids))
            .scalar()
        )
        # Retained = logged a session in the last 7 days
        retained_7d = (
            db.query(func.count(func.distinct(SessionModel.user_id)))
            .filter(
                SessionModel.user_id.in_(new_user_ids),
                SessionModel.logged_at >= now - timedelta(days=7),
            )
            .scalar()
        )

    # Nudge effectiveness: users who were nudged and then logged
    # (simplified: count users with at_risk who still have active streaks)
    total_with_streaks = db.query(Streak).filter(Streak.current_streak >= 7).count()

    return {
        "new_users_30d": new_users_30d,
        "activated": activated,
        "activation_rate": round(activated / max(new_users_30d, 1) * 100, 1),
        "retained_7d": retained_7d,
        "retention_rate_7d": round(retained_7d / max(new_users_30d, 1) * 100, 1),
        "users_with_7d_streak": total_with_streaks,
    }
