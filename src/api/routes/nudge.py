"""GET /nudge/at-risk — find users whose streaks are at risk today."""

import os
from datetime import datetime, date, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import User, Streak, Nudge
from src.agents.nudge import NudgeAgent
from src.agents.context import build_user_context

router = APIRouter()
nudge_agent = NudgeAgent()


def _check_admin_key(request: Request) -> None:
    """Require X-Admin-Key header matching ADMIN_API_KEY env var."""
    admin_key = os.getenv("ADMIN_API_KEY")
    if not admin_key:
        raise HTTPException(status_code=503, detail="Not configured")
    provided = request.headers.get("x-admin-key", "")
    if provided != admin_key:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/nudge/at-risk")
async def get_at_risk_users(request: Request, db: DBSession = Depends(get_db)):
    """Return users with active streaks who haven't logged today."""
    _check_admin_key(request)
    today = date.today()

    # Get all users with active streaks
    streaks = (
        db.query(Streak)
        .filter(Streak.current_streak > 0)
        .all()
    )

    at_risk = []
    for streak in streaks:
        # Skip if they already logged today
        if streak.last_session_date == today:
            continue

        user = db.query(User).filter(User.id == streak.user_id).first()
        if not user or not user.discord_id:
            continue

        # Don't nudge if we nudged in the last 4 hours
        last_nudge = (
            db.query(Nudge)
            .filter(Nudge.user_id == user.id)
            .order_by(Nudge.sent_at.desc())
            .first()
        )
        if last_nudge and last_nudge.sent_at:
            if datetime.now(timezone.utc) - last_nudge.sent_at < timedelta(hours=4):
                continue

        # Generate nudge message
        nudge_data = {
            "subject": f"Day {streak.current_streak + 1} is waiting",
            "body": f"{user.name}, your streak is at {streak.current_streak} days. Your Seven 7 is ready.",
            "cta": "Type `/seven7` in the server.",
        }

        # Try AI-generated nudge
        try:
            ctx = build_user_context(user.id, db)
            if nudge_agent.should_nudge(ctx):
                nudge_msg = await nudge_agent.generate_nudge(ctx)
                nudge_data = {
                    "subject": nudge_msg.subject,
                    "body": nudge_msg.body,
                    "cta": nudge_msg.cta,
                }
        except Exception:
            pass  # Fall back to default nudge

        # Record the nudge
        db.add(Nudge(
            user_id=user.id,
            channel="discord_dm",
            message_text=f"{nudge_data['subject']}: {nudge_data['body']}",
        ))
        db.commit()

        at_risk.append({
            "user_id": user.id,
            "discord_id": user.discord_id,
            "name": user.name,
            "current_streak": streak.current_streak,
            "nudge": nudge_data,
        })

    return {"users": at_risk}
