"""POST /subscribe — email capture for daily reminders."""

import re
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.db.database import get_db
from src.db.models import EmailSubscriber

router = APIRouter()

# Rate limit: 5 per IP per hour
_sub_rate: dict[str, list] = {}
_SUB_RATE_LIMIT = 5


def _prune_rate_limits(rate_dict: dict, max_age: float = 7200):
    cutoff = time.time() - max_age
    stale = [ip for ip, ts in rate_dict.items() if not ts or ts[-1] < cutoff]
    for ip in stale:
        del rate_dict[ip]

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


@router.post("/subscribe")
async def subscribe_email(request: Request, db: Session = Depends(get_db)):
    # Rate limit
    _prune_rate_limits(_sub_rate)
    ip = request.client.host if request.client else "unknown"
    now_ts = datetime.now(timezone.utc).timestamp()
    hour_ago = now_ts - 3600
    hits = _sub_rate.get(ip, [])
    hits = [t for t in hits if t > hour_ago]
    if len(hits) >= _SUB_RATE_LIMIT:
        _sub_rate[ip] = hits
        raise HTTPException(status_code=429, detail="Too many requests. Try again later.")
    hits.append(now_ts)
    _sub_rate[ip] = hits

    body = await request.json()
    email = (body.get("email") or "").strip().lower()
    if not email or not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Valid email required.")

    # Check existing
    existing = db.query(EmailSubscriber).filter(EmailSubscriber.email == email).first()
    if existing:
        if existing.unsubscribed:
            existing.unsubscribed = False
            existing.subscribed_at = datetime.now(timezone.utc)
            db.commit()
            return {"message": "Welcome back. See you tomorrow."}
        return {"message": "You're already subscribed. See you tomorrow."}

    sub = EmailSubscriber(email=email)
    db.add(sub)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"message": "You're already subscribed. See you tomorrow."}

    return {"message": "You're in. See you tomorrow."}
