"""GET /daily — today's universal Seven7 session for everyone."""

from datetime import datetime

from fastapi import APIRouter

from src.agents.coach import CoachAgent

router = APIRouter()
coach = CoachAgent()

# Cache: one session per day
_daily_cache: dict = {"date": None, "session": None}


@router.get("/daily")
async def get_daily():
    today = datetime.utcnow().strftime("%Y-%m-%d")

    if _daily_cache["date"] == today and _daily_cache["session"]:
        return _daily_cache["session"]

    session = await coach.generate_daily()
    _daily_cache["date"] = today
    _daily_cache["session"] = session
    return session
