"""Shared authentication + anti-abuse utilities."""

import time
import logging
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from src.db.models import User, Session as SessionModel

logger = logging.getLogger("jerome7")

# ── Rate limiter: per-user session logging ────────────────────────────────────
_log_rate: dict[str, float] = {}  # user_id -> last_log_timestamp
_LOG_COOLDOWN = 300  # 5 minutes between sessions (nobody does 7-min wellness twice in 5 min)

# ── IP-based rate limiter for unauthenticated endpoints ──────────────────────
_ip_rate: dict[str, list[float]] = {}


def get_real_ip(request: Request) -> str:
    """Extract real client IP, respecting Cloudflare/Railway proxy headers."""
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def authenticate_user(user_id: str, request: Request, db: DBSession) -> User:
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

    # Token expiration: 90 days
    if user.token_issued_at:
        age = datetime.now(timezone.utc) - user.token_issued_at
        if age > timedelta(days=90):
            raise HTTPException(status_code=401, detail="Token expired. Please re-register.")

    # Update last_active_at
    user.last_active_at = datetime.now(timezone.utc)

    return user


def check_log_rate_limit(user_id: str):
    """Enforce per-user cooldown on session logging (1 session per 5 min)."""
    now = time.time()
    last = _log_rate.get(user_id, 0)
    if now - last < _LOG_COOLDOWN:
        wait = int(_LOG_COOLDOWN - (now - last))
        raise HTTPException(
            status_code=429,
            detail=f"You already logged a session recently. Try again in {wait}s.",
            headers={"Retry-After": str(wait)},
        )
    _log_rate[user_id] = now


def validate_session_integrity(user_id: str, duration_minutes: int, db: DBSession):
    """Reject obviously fraudulent session logs."""
    # Duration must be reasonable (5-15 min range for a 7-min session)
    if duration_minutes is not None and (duration_minutes < 5 or duration_minutes > 15):
        raise HTTPException(status_code=422, detail="Invalid session duration.")

    # Check for duplicate log today (max 3 sessions per day)
    today = datetime.now(timezone.utc).date()
    today_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    today_count = (
        db.query(SessionModel)
        .filter(SessionModel.user_id == user_id, SessionModel.logged_at >= today_start)
        .count()
    )
    if today_count >= 3:
        raise HTTPException(status_code=429, detail="Maximum 3 sessions per day.")


def check_ip_rate(ip: str, limit: int = 10, window: int = 3600) -> bool:
    """Generic IP rate limiter. Returns True if allowed, raises 429 if not."""
    now = time.time()
    cutoff = now - window
    hits = [t for t in _ip_rate.get(ip, []) if t > cutoff]
    if len(hits) >= limit:
        _ip_rate[ip] = hits
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Try again later.",
            headers={"Retry-After": str(window)},
        )
    hits.append(now)
    _ip_rate[ip] = hits

    # Prune old entries periodically
    if len(_ip_rate) > 10000:
        stale = [k for k, v in _ip_rate.items() if not v or v[-1] < cutoff]
        for k in stale:
            del _ip_rate[k]

    return True
