"""POST /log — session logging endpoint."""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from src.api.models import LogSessionRequest, SessionResponse
from src.db.database import get_db
from src.db.models import Session
from src.agents.streak import StreakAgent

router = APIRouter()
streak_agent = StreakAgent()


@router.post("/log/{user_id}", response_model=SessionResponse)
def log_session(user_id: str, req: LogSessionRequest, db: DBSession = Depends(get_db)):
    session = Session(
        user_id=user_id,
        seven7_title=req.seven7_title,
        blocks_completed=req.blocks_completed,
        duration_minutes=req.duration_minutes,
        note=req.note,
    )
    db.add(session)
    db.commit()

    update = streak_agent.update_streak(user_id, datetime.utcnow(), db)

    return SessionResponse(
        session_id=session.id,
        streak_updated=True,
        new_streak=update.new,
        milestone_reached=update.milestone_reached,
    )
