"""GET /stats — public community stats for dynamic badges and embeds."""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import User, Streak, Session as SessionModel

router = APIRouter()

# In-memory cache: avoids 5 DB queries on every hit
_stats_cache: dict = {"data": None, "ts": 0}
_STATS_TTL = 60  # seconds


@router.get("/stats")
def public_stats(db: DBSession = Depends(get_db)):
    """Public stats JSON — cached for 60s to protect DB under load."""
    now_ts = time.time()
    if _stats_cache["data"] and (now_ts - _stats_cache["ts"]) < _STATS_TTL:
        return JSONResponse(
            content=_stats_cache["data"],
            headers={"Cache-Control": "public, max-age=60"},
        )

    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

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

    result = {
        "total_jeromes": total_jeromes,
        "total_sessions": total_sessions,
        "active_streaks": active_streaks,
        "sessions_today": sessions_today,
        "countries": countries,
        "longest_streak": top_streak.current_streak if top_streak else 0,
        "minutes_of_wellness": total_sessions * 7,
    }
    _stats_cache["data"] = result
    _stats_cache["ts"] = now_ts

    return JSONResponse(
        content=result,
        headers={"Cache-Control": "public, max-age=60"},
    )
