"""GET /streak/{user_id} — streak endpoint (auth required)."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from src.api.models import StreakResponse
from src.db.database import get_db
from src.db.models import User, Streak
from src.agents.streak import StreakAgent, MILESTONES

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


@router.get("/streak/{user_id}", response_model=StreakResponse)
def get_streak(user_id: str, request: Request, db: DBSession = Depends(get_db)):
    user = _authenticate_user(user_id, request, db)

    streak = db.query(Streak).filter(Streak.user_id == user_id).first()
    if not streak:
        raise HTTPException(status_code=404, detail="No streak data")

    chain = streak_agent.get_chain(user_id, db)

    # Calculate next milestone
    next_milestone = 7
    for m in MILESTONES:
        if streak.current_streak < m:
            next_milestone = m
            break

    # Saves remaining
    saves = 1
    if streak.last_save_date:
        from datetime import date
        if (date.today() - streak.last_save_date).days < 30:
            saves = 0

    return StreakResponse(
        user_id=user_id,
        username=user.name,
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        total_sessions=streak.total_sessions,
        last_session_date=streak.last_session_date,
        streak_broken_count=streak.streak_broken_count,
        saves_remaining=saves,
        next_milestone=next_milestone,
        chain=chain,
    )


@router.post("/streak/{user_id}/save")
def use_save(user_id: str, request: Request, db: DBSession = Depends(get_db)):
    _authenticate_user(user_id, request, db)

    saved = streak_agent.use_save(user_id, db)
    return {"saved": saved}
