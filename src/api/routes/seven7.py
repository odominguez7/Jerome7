"""GET /seven7/{user_id} — today's Seven 7 session."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from src.api.models import Seven7Response, Seven7Block, EnergyCheckinRequest
from src.db.database import get_db
from src.db.models import Seven7Session, User, EnergyLevel
from src.agents.coach import CoachAgent
from src.agents.context import build_user_context

router = APIRouter()
coach = CoachAgent()


@router.get("/seven7/{user_id}", response_model=Seven7Response)
async def get_seven7(user_id: str, db: DBSession = Depends(get_db)):
    # Check if today's session already exists
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    existing = (
        db.query(Seven7Session)
        .filter(Seven7Session.user_id == user_id, Seven7Session.generated_at >= today_start)
        .first()
    )

    if existing:
        blocks = [Seven7Block(**b) for b in (existing.blocks or [])]
        return Seven7Response(
            user_id=user_id,
            generated_at=existing.generated_at,
            greeting=existing.greeting or "",
            session_title=existing.session_title or "",
            closing=existing.closing or "",
            blocks=blocks,
            total_seconds=sum(b.duration_seconds for b in blocks),
        )

    # Generate new session
    try:
        ctx = build_user_context(user_id, db)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found. Use /pledge to register first.")
    session_data = await coach.generate(ctx, db)

    blocks = [Seven7Block(**b) for b in session_data.get("blocks", [])]
    return Seven7Response(
        user_id=user_id,
        generated_at=datetime.now(timezone.utc),
        greeting=session_data.get("greeting", ""),
        session_title=session_data.get("session_title", ""),
        closing=session_data.get("closing", ""),
        blocks=blocks,
        total_seconds=sum(b.duration_seconds for b in blocks),
    )


@router.post("/seven7/{user_id}/checkin")
async def energy_checkin(user_id: str, req: EnergyCheckinRequest, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    energy = EnergyLevel(req.energy) if req.energy in [e.value for e in EnergyLevel] else None
    user.energy_today = energy
    db.commit()

    # Regenerate today's Seven 7
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    db.query(Seven7Session).filter(
        Seven7Session.user_id == user_id,
        Seven7Session.generated_at >= today_start,
    ).delete()
    db.commit()

    ctx = build_user_context(user_id, db)
    session_data = await coach.generate(ctx, db)

    blocks = [Seven7Block(**b) for b in session_data.get("blocks", [])]
    return Seven7Response(
        user_id=user_id,
        generated_at=datetime.now(timezone.utc),
        greeting=session_data.get("greeting", ""),
        session_title=session_data.get("session_title", ""),
        closing=session_data.get("closing", ""),
        blocks=blocks,
        total_seconds=sum(b.duration_seconds for b in blocks),
    )
