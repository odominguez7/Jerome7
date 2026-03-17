"""POST /subscribe - email capture for daily reminders + email verification."""

import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.api.auth import authenticate_user, get_real_ip, check_ip_rate
from src.api.email_utils import generate_verify_token, SITE_URL
from src.db.database import get_db
from src.db.models import EmailSubscriber, User

logger = logging.getLogger("jerome7")

router = APIRouter()

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


@router.post("/subscribe")
async def subscribe_email(request: Request, db: Session = Depends(get_db)):
    ip = get_real_ip(request)
    check_ip_rate(ip, limit=5, window=3600)

    body = await request.json()
    email = (body.get("email") or "").strip().lower()
    if not email or not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Valid email required.")

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


@router.post("/user/{user_id}/email")
async def submit_email(user_id: str, request: Request, db: Session = Depends(get_db)):
    """Submit email for verification. Stores token, returns verify URL."""
    ip = get_real_ip(request)
    check_ip_rate(ip, limit=3, window=3600)

    user = authenticate_user(user_id, request, db)

    body = await request.json()
    email = (body.get("email") or "").strip().lower()
    if not email or not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Valid email required.")

    existing = db.query(User).filter(User.email == email, User.id != user_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already in use.")

    user.email = email
    user.email_verified = False
    user.email_verify_token = None
    db.commit()

    token = generate_verify_token(user.id)
    verify_url = f"{SITE_URL}/verify?token={token}"

    return {"status": "ok", "verify_url": verify_url}
