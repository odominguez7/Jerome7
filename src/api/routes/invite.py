"""Pod Chain — viral invite system. 7-day streak unlocks 1 invite code."""

import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import User, Streak, InviteCode

router = APIRouter()

_FLAG = {
    "US": "\U0001f1fa\U0001f1f8", "CA": "\U0001f1e8\U0001f1e6", "BR": "\U0001f1e7\U0001f1f7",
    "GB": "\U0001f1ec\U0001f1e7", "DE": "\U0001f1e9\U0001f1ea", "FR": "\U0001f1eb\U0001f1f7",
    "JP": "\U0001f1ef\U0001f1f5", "KR": "\U0001f1f0\U0001f1f7", "IN": "\U0001f1ee\U0001f1f3",
    "AU": "\U0001f1e6\U0001f1fa", "NG": "\U0001f1f3\U0001f1ec", "KE": "\U0001f1f0\U0001f1ea",
    "MX": "\U0001f1f2\U0001f1fd", "ES": "\U0001f1ea\U0001f1f8", "IT": "\U0001f1ee\U0001f1f9",
    "ZA": "\U0001f1ff\U0001f1e6",
}

MIN_STREAK_FOR_INVITE = 7


def _generate_code() -> str:
    """Generate a short, readable invite code."""
    return f"j7-{secrets.token_urlsafe(6)}"


@router.post("/invite/{user_id}")
def create_invite(user_id: str, db: DBSession = Depends(get_db)):
    """Generate an invite code. Requires 7-day streak. 1 unused code at a time."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    streak = db.query(Streak).filter(Streak.user_id == user_id).first()
    if not streak or streak.current_streak < MIN_STREAK_FOR_INVITE:
        raise HTTPException(
            status_code=403,
            detail=f"Need a {MIN_STREAK_FOR_INVITE}-day streak to unlock invites. "
                   f"Current: {streak.current_streak if streak else 0} days.",
        )

    # Check if they already have an unused code
    existing = (
        db.query(InviteCode)
        .filter(InviteCode.inviter_id == user_id, InviteCode.used_by_id.is_(None))
        .first()
    )
    if existing:
        return {
            "code": existing.code,
            "url": f"https://jerome7.com/join/{existing.code}",
            "status": "already_generated",
        }

    code = _generate_code()
    invite = InviteCode(code=code, inviter_id=user_id)
    db.add(invite)
    db.commit()

    return {
        "code": code,
        "url": f"https://jerome7.com/join/{code}",
        "status": "created",
        "message": f"{user.name} earned an invite code with a {streak.current_streak}-day streak.",
    }


@router.get("/invite/{user_id}/status")
def invite_status(user_id: str, db: DBSession = Depends(get_db)):
    """Check invite eligibility and history."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    streak = db.query(Streak).filter(Streak.user_id == user_id).first()
    current = streak.current_streak if streak else 0

    codes = db.query(InviteCode).filter(InviteCode.inviter_id == user_id).all()
    total_invited = sum(1 for c in codes if c.used_by_id)
    unused = [c.code for c in codes if not c.used_by_id]

    return {
        "eligible": current >= MIN_STREAK_FOR_INVITE,
        "current_streak": current,
        "required_streak": MIN_STREAK_FOR_INVITE,
        "days_until_eligible": max(MIN_STREAK_FOR_INVITE - current, 0),
        "total_invited": total_invited,
        "unused_codes": unused,
    }


@router.get("/join/{code}", response_class=HTMLResponse)
def join_page(code: str, db: DBSession = Depends(get_db)):
    """Landing page for invited users — shows inviter's name, streak, and CTA."""
    invite = db.query(InviteCode).filter(InviteCode.code == code).first()

    if not invite:
        raise HTTPException(status_code=404, detail="Invalid invite code.")

    if invite.used_by_id:
        raise HTTPException(status_code=410, detail="This invite has already been used.")

    inviter = db.query(User).filter(User.id == invite.inviter_id).first()
    streak = db.query(Streak).filter(Streak.user_id == invite.inviter_id).first()

    inviter_name = inviter.name if inviter else "Someone"
    inviter_streak = streak.current_streak if streak else 0
    inviter_country = inviter.country if inviter else None
    flag = _FLAG.get(inviter_country, "\U0001f30d") if inviter_country else "\U0001f30d"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jerome7 — {inviter_name} invited you</title>
<meta name="description" content="{inviter_name} wants you to join Jerome7. 7 minutes a day. Free forever.">
<meta property="og:title" content="{inviter_name} invited you to Jerome7">
<meta property="og:description" content="7 minutes a day. Same session for everyone on earth. {inviter_name} is on a {inviter_streak}-day streak.">
<meta property="og:url" content="https://jerome7.com/join/{code}">
<meta name="twitter:card" content="summary">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0d1117; color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
  }}
  .card {{
    max-width: 480px; width: 100%; margin: 40px 20px;
    text-align: center;
  }}
  .brand {{
    font-size: 11px; letter-spacing: 3px; color: #E85D04;
    font-weight: 700; margin-bottom: 48px; display: block;
  }}
  .invite-from {{
    font-size: 12px; color: #484f58; letter-spacing: 1px;
    margin-bottom: 8px;
  }}
  .inviter-name {{
    font-size: 36px; font-weight: 800; color: #f0f6fc;
    line-height: 1.2; margin-bottom: 8px;
  }}
  .inviter-streak {{
    font-size: 14px; color: #E85D04; font-weight: 600;
    margin-bottom: 40px;
  }}
  .pitch {{
    font-size: 13px; color: #8b949e; line-height: 1.8;
    margin-bottom: 40px;
  }}
  .pitch strong {{ color: #f0f6fc; }}
  .cta-btn {{
    display: inline-block; padding: 16px 48px;
    background: #E85D04; color: #fff; font-weight: 700;
    font-size: 13px; letter-spacing: 2px; text-decoration: none;
    border-radius: 6px; margin-bottom: 16px;
  }}
  .cta-btn:hover {{ background: #c24e03; }}
  .cta-sub {{
    font-size: 10px; color: #30363d; letter-spacing: 1px;
  }}
  .chain-note {{
    margin-top: 40px; font-size: 11px; color: #484f58;
    line-height: 1.6;
  }}
  .chain-note strong {{ color: #E85D04; }}
</style>
</head>
<body>
<div class="card">
  <span class="brand">JEROME7</span>
  <div class="invite-from">YOU'VE BEEN INVITED BY</div>
  <div class="inviter-name">{flag} {inviter_name}</div>
  <div class="inviter-streak">{inviter_streak}-day streak</div>

  <div class="pitch">
    <strong>7 minutes a day.</strong> Same session for everyone on earth.<br>
    Bodyweight only. Zero equipment. No account needed.<br>
    Just show up.
  </div>

  <a href="/timer?invite={code}" class="cta-btn">START YOUR FIRST SESSION</a>
  <div class="cta-sub">Free forever. Open source.</div>

  <div class="chain-note">
    When you hit a <strong>7-day streak</strong>, you'll unlock<br>
    your own invite to pass on. The chain continues.
  </div>
</div>
</body>
</html>"""

    return HTMLResponse(content=html)
