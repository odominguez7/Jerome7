"""POST /log — session logging + feedback + status endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from src.api.models import LogSessionRequest, SessionResponse, FeedbackRequest, FeedbackResponse
from src.db.database import get_db
from src.db.models import Session, SessionFeedback, Streak, User
from src.agents.streak import StreakAgent

router = APIRouter()
streak_agent = StreakAgent()


def _authenticate_user(user_id: str, request: Request, db: DBSession) -> User:
    """Validate Bearer token and return the user, or raise 401/404."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")

    token = auth_header[7:]  # strip "Bearer "
    if not user.auth_token or token != user.auth_token:
        raise HTTPException(status_code=401, detail="Invalid auth token.")

    return user


@router.post("/log/{user_id}", response_model=SessionResponse)
def log_session(user_id: str, req: LogSessionRequest, request: Request, db: DBSession = Depends(get_db)):
    _authenticate_user(user_id, request, db)

    session = Session(
        user_id=user_id,
        seven7_title=req.seven7_title,
        blocks_completed=req.blocks_completed,
        duration_minutes=req.duration_minutes,
        note=req.note,
    )
    db.add(session)
    db.commit()

    update = streak_agent.update_streak(user_id, datetime.now(timezone.utc), db)

    return SessionResponse(
        session_id=session.id,
        streak_updated=True,
        new_streak=update.new,
        milestone_reached=update.milestone_reached,
    )


@router.post("/log/{user_id}/feedback", response_model=FeedbackResponse)
def log_feedback(user_id: str, req: FeedbackRequest, request: Request, db: DBSession = Depends(get_db)):
    _authenticate_user(user_id, request, db)

    fb = SessionFeedback(
        user_id=user_id,
        difficulty_rating=req.difficulty,
        enjoyment_rating=req.enjoyment,
        body_note=req.body_note,
        completed_blocks=req.completed_blocks,
    )
    db.add(fb)
    db.commit()

    return FeedbackResponse(feedback_id=fb.id, stored=True)


@router.get("/status/{user_id}")
def user_status(user_id: str, db: DBSession = Depends(get_db)):
    """Check if user has logged today + current streak. Used by agent nudges."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "User not found"}

    today = datetime.now(timezone.utc).date()
    logged_today = (
        db.query(Session)
        .filter(Session.user_id == user_id)
        .filter(Session.logged_at >= datetime(today.year, today.month, today.day))
        .first()
    ) is not None

    streak = db.query(Streak).filter(Streak.user_id == user_id).first()
    current_streak = streak.current_streak if streak else 0
    return {
        "user_id": user_id,
        "name": user.name,
        "logged_today": logged_today,
        "current_streak": current_streak,
        "at_risk": not logged_today and current_streak > 0,
        "nudge": not logged_today,
    }
