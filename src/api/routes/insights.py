"""GET /api/insights/{jerome_number} — pattern insights endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import User
from src.agents.pattern import PatternAgent

router = APIRouter()
pattern_agent = PatternAgent()


@router.get("/api/insights/{jerome_number}")
def get_insights(jerome_number: int, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.jerome_number == jerome_number).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    insight = pattern_agent.analyze(user.id)

    return JSONResponse(
        content=insight,
        headers={"Cache-Control": "no-cache"},
    )
