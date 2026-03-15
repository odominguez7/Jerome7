"""GET /share/templates/{user_id} — platform-specific share copy for Twitter/LinkedIn/GitHub."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import User, Streak

router = APIRouter()


@router.get("/share/templates/{user_id}")
def share_templates(user_id: str, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    streak_row = db.query(Streak).filter(Streak.user_id == user_id).first()
    current = streak_row.current_streak if streak_row else 0
    total = streak_row.total_sessions if streak_row else 0

    jerome_num = user.jerome_number or "?"

    twitter = (
        f"Day {current}. 7 minutes. \u2713\n\n"
        f"I'm Jerome{jerome_num}. @Jerome7app\n\n"
        f"https://jerome7.com/join"
    )

    linkedin = (
        f"Day {current} of showing up for 7 minutes.\n\n"
        f"Not a workout. Not a productivity hack.\n"
        f"Just 7 minutes of breathing, meditation, or reflection.\n\n"
        f"I'm part of an open-source community of builders "
        f"who believe consistency > intensity.\n\n"
        f"Jerome7 — the daily 7-minute ritual for people who build.\n\n"
        f"https://jerome7.com"
    )

    github_readme = (
        f"### Daily Practice\n"
        f"![Jerome{jerome_num}](https://jerome7.com/api/badge/{jerome_num}.svg)\n"
        f"*7 minutes. Show up. The world gets better.*"
    )

    discord = (
        f"Day {current} \U0001f525 Just finished my Jerome7 session. "
        f"Jerome{jerome_num} | {total} total sessions | jerome7.com"
    )

    return {
        "jerome_number": jerome_num,
        "current_streak": current,
        "templates": {
            "twitter": twitter,
            "linkedin": linkedin,
            "github_readme": github_readme,
            "discord": discord,
        },
        "share_urls": {
            "twitter": f"https://twitter.com/intent/tweet?text={twitter.replace(chr(10), '%0A').replace(' ', '+')}",
            "linkedin": "https://www.linkedin.com/sharing/share-offsite/?url=https://jerome7.com",
            "share_card": f"https://jerome7.com/share/{user_id}",
        },
    }
