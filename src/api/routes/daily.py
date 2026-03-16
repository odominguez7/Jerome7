"""GET /daily — today's universal Seven7 session for everyone."""

from datetime import datetime, timezone

from fastapi import APIRouter

from src.agents.coach import CoachAgent
from src.agents.session_types import today_session_type

router = APIRouter()
coach = CoachAgent()

# Cache: one session per day
_daily_cache: dict = {"date": None, "session": None}
_wellness_cache: dict = {"date": None, "session": None}


@router.get("/daily")
async def get_daily():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if _daily_cache["date"] == today and _daily_cache["session"]:
        return _daily_cache["session"]

    session = await coach.generate_daily()
    _daily_cache["date"] = today
    _daily_cache["session"] = session
    return session


@router.get("/daily/wellness")
async def get_daily_wellness():
    """Today's rotating wellness session (breathwork/meditation/reflection/preparation)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if _wellness_cache["date"] == today and _wellness_cache["session"]:
        return _wellness_cache["session"]

    session_type = today_session_type()
    session = await coach.generate_wellness(session_type)
    _wellness_cache["date"] = today
    _wellness_cache["session"] = session
    return session


@router.get("/daily/type")
async def get_daily_type():
    """Return today's session type without generating the full session."""
    return {"session_type": today_session_type(), "date": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
