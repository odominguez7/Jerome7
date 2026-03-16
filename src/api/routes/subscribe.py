"""POST /subscribe — email capture for daily reminders + email verification."""

import re
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.db.database import get_db
from src.db.models import EmailSubscriber, User

router = APIRouter()

# Rate limit: 5 per IP per hour
_sub_rate: dict[str, list] = {}
_SUB_RATE_LIMIT = 5


def _prune_rate_limits(rate_dict: dict, max_age: float = 7200):
    cutoff = time.time() - max_age
    to_delete = []
    for ip, timestamps in rate_dict.items():
        rate_dict[ip] = [t for t in timestamps if t > cutoff]
        if not rate_dict[ip]:
            to_delete.append(ip)
    for ip in to_delete:
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
        raise HTTPException(status_code=429, detail="Too many requests. Try again later.", headers={"Retry-After": "3600"})
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


# ── Email verification for Jerome# identity ──

# Rate limit: 3 per IP per hour
_email_rate: dict[str, list] = {}
_EMAIL_RATE_LIMIT = 3


def _authenticate_user(user_id: str, request: Request, db: Session) -> User:
    """Validate Bearer token and return the user, or raise 401/404."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")

    token = auth_header[7:]
    if not user.auth_token or token != user.auth_token:
        raise HTTPException(status_code=401, detail="Invalid auth token.")

    return user


@router.post("/user/{user_id}/email")
async def submit_email(user_id: str, request: Request, db: Session = Depends(get_db)):
    """Submit email for verification. Stores token, returns verify URL."""
    # Rate limit
    _prune_rate_limits(_email_rate)
    ip = request.client.host if request.client else "unknown"
    now_ts = datetime.now(timezone.utc).timestamp()
    hour_ago = now_ts - 3600
    hits = _email_rate.get(ip, [])
    hits = [t for t in hits if t > hour_ago]
    if len(hits) >= _EMAIL_RATE_LIMIT:
        _email_rate[ip] = hits
        raise HTTPException(status_code=429, detail="Too many requests. Try again later.", headers={"Retry-After": "3600"})
    hits.append(now_ts)
    _email_rate[ip] = hits

    # Auth
    user = _authenticate_user(user_id, request, db)

    # Parse body
    body = await request.json()
    email = (body.get("email") or "").strip().lower()
    if not email or not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Valid email required.")

    # Check if email is already taken by another user
    existing = db.query(User).filter(User.email == email, User.id != user_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already in use.")

    # Generate verify token and store
    verify_token = str(uuid.uuid4())
    user.email = email
    user.email_verified = False
    user.email_verify_token = verify_token
    db.commit()

    return {"status": "ok", "verify_url": f"/verify/{verify_token}"}


@router.get("/verify/{token}", response_class=HTMLResponse)
async def verify_email(token: str, db: Session = Depends(get_db)):
    """Verify email via token link."""
    user = db.query(User).filter(User.email_verify_token == token).first()

    if user:
        user.email_verified = True
        user.email_verify_token = None
        db.commit()
        jerome_label = f"Jerome#{user.jerome_number}" if user.jerome_number else user.name
        message = f"Email verified! You're {jerome_label}. Welcome to the community."
        color = "#3fb950"
    else:
        message = "Invalid or expired verification link."
        color = "#f85149"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jerome7 | Email Verification</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0d1117; color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
    padding: 20px;
  }}
  .card {{
    max-width: 480px; width: 100%; text-align: center;
    background: #161b22; border: 1px solid #30363d;
    border-radius: 16px; padding: 48px 32px;
  }}
  .brand {{ font-size: 10px; letter-spacing: 3px; color: #E85D04; margin-bottom: 24px; }}
  .message {{ font-size: 18px; font-weight: 700; color: {color}; margin-bottom: 16px; line-height: 1.4; }}
  .sub {{ font-size: 13px; color: #8b949e; margin-bottom: 32px; }}
  a.btn {{
    display: inline-block; padding: 14px 40px;
    background: #E85D04; color: #fff; border-radius: 100px;
    text-decoration: none; font-family: inherit;
    font-size: 14px; font-weight: 700; letter-spacing: 1px;
  }}
  a.btn:hover {{ background: #ff6b1a; }}
</style>
</head>
<body>
<div class="card">
  <div class="brand">JEROME7</div>
  <div class="message">{message}</div>
  <div class="sub">{"You're part of something real." if user else "Try requesting a new verification link."}</div>
  <a class="btn" href="/timer">START SESSION</a>
</div>
</body>
</html>"""
    return HTMLResponse(content=html)
