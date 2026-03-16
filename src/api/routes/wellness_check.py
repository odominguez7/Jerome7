"""Wellness check API — used by GitHub Actions to gate PR merges."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session as DBSession

from src.agents.session_types import today_session_type
from src.db.database import get_db
from src.db.models import Session as SessionModel, Streak, User

router = APIRouter(prefix="/api/wellness-check", tags=["wellness-check"])

HEADERS = {"Cache-Control": "no-cache, no-store, must-revalidate"}


def _today_start() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _build_response(user: User, streak: Streak | None, db: DBSession) -> JSONResponse:
    jn = user.jerome_number
    current_streak = streak.current_streak if streak else 0
    session_type = today_session_type()

    completed = (
        db.query(SessionModel)
        .filter(
            SessionModel.user_id == user.id,
            SessionModel.logged_at >= _today_start(),
        )
        .first()
        is not None
    )

    if completed:
        return JSONResponse(
            content={
                "completed": True,
                "streak": current_streak,
                "jerome_number": jn,
                "session_type": session_type,
                "message": f"Jerome{jn} showed up. Day {current_streak}.",
            },
            headers=HEADERS,
        )

    return JSONResponse(
        content={
            "completed": False,
            "streak": current_streak,
            "jerome_number": jn,
            "session_type": session_type,
            "message": f"Jerome{jn} hasn't shown up yet today.",
            "start_url": "https://jerome7.com/timer",
        },
        headers=HEADERS,
    )


def _not_found() -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": "Jerome not found", "join_url": "https://jerome7.com"},
        headers=HEADERS,
    )


@router.get("/{jerome_number}")
def wellness_check_by_number(jerome_number: int, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.jerome_number == jerome_number).first()
    if not user:
        return _not_found()
    streak = db.query(Streak).filter(Streak.user_id == user.id).first()
    return _build_response(user, streak, db)


@router.get("/github/{github_username}")
def wellness_check_by_github(github_username: str, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.github_username == github_username).first()
    if not user:
        return _not_found()
    streak = db.query(Streak).filter(Streak.user_id == user.id).first()
    return _build_response(user, streak, db)
