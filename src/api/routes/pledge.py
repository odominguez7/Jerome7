"""POST /pledge — onboarding with strict validation and deduplication."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from src.api.models import PledgeRequest, UserResponse
from src.db.database import get_db
from src.db.models import (
    User, Streak, FitnessLevel,
    AgeBracket, Gender, UserSource, UserGoal, InviteCode, UserRole,
)
import time
from datetime import datetime, timezone

# Simple rate limiter: max 10 pledges per IP per hour
_pledge_rate: dict[str, list] = {}
_PLEDGE_RATE_LIMIT = 10


def _prune_rate_limits(rate_dict: dict, max_age: float = 7200):
    cutoff = time.time() - max_age
    to_delete = []
    for ip, timestamps in rate_dict.items():
        rate_dict[ip] = [t for t in timestamps if t > cutoff]
        if not rate_dict[ip]:
            to_delete.append(ip)
    for ip in to_delete:
        del rate_dict[ip]


def _next_jerome_number(db: Session) -> int:
    """Get the next available Jerome# (starting from 8, since 1-7 are reserved)."""
    max_num = db.query(func.max(User.jerome_number)).scalar()
    if max_num is None or max_num < 8:
        return 8
    return max_num + 1

router = APIRouter()

# Valid enum values
_VALID_SOURCES = {e.value for e in UserSource}

# Placeholder names we reject
_PLACEHOLDER_NAMES = {
    "", "test", "user", "name", "your name", "string", "null", "undefined",
    "placeholder", "example", "asdf", "asd", "abc", "xxx", "n/a", "none",
}

# Timezone → country
_TZ_COUNTRY_MAP = {
    "America/New_York": "US", "America/Chicago": "US", "America/Denver": "US",
    "America/Los_Angeles": "US", "America/Phoenix": "US", "America/Anchorage": "US",
    "America/Toronto": "CA", "America/Vancouver": "CA", "America/Montreal": "CA",
    "America/Mexico_City": "MX", "America/Bogota": "CO", "America/Sao_Paulo": "BR",
    "America/Argentina/Buenos_Aires": "AR", "America/Lima": "PE", "America/Santiago": "CL",
    "Europe/London": "GB", "Europe/Paris": "FR", "Europe/Berlin": "DE",
    "Europe/Madrid": "ES", "Europe/Rome": "IT", "Europe/Amsterdam": "NL",
    "Europe/Zurich": "CH", "Europe/Stockholm": "SE", "Europe/Oslo": "NO",
    "Europe/Dublin": "IE", "Europe/Lisbon": "PT", "Europe/Warsaw": "PL",
    "Europe/Istanbul": "TR", "Europe/Moscow": "RU",
    "Asia/Tokyo": "JP", "Asia/Seoul": "KR", "Asia/Shanghai": "CN",
    "Asia/Hong_Kong": "HK", "Asia/Singapore": "SG", "Asia/Kolkata": "IN",
    "Asia/Dubai": "AE", "Asia/Riyadh": "SA", "Asia/Jakarta": "ID",
    "Asia/Bangkok": "TH", "Asia/Manila": "PH",
    "Australia/Sydney": "AU", "Australia/Melbourne": "AU", "Australia/Perth": "AU",
    "Pacific/Auckland": "NZ", "Africa/Lagos": "NG", "Africa/Nairobi": "KE",
    "Africa/Cairo": "EG", "Africa/Johannesburg": "ZA",
}


def _country_from_timezone(tz):
    if not tz or tz == "UTC":
        return None
    return _TZ_COUNTRY_MAP.get(tz)


def _country_from_ip(request):
    """Extract country from Cloudflare CF-IPCountry header if available."""
    cf_country = request.headers.get("cf-ipcountry")
    if cf_country and cf_country != "XX" and len(cf_country) == 2:
        return cf_country.upper()
    return None


def _require_enum(enum_cls, value, field_name):
    """Return enum member or raise 422 with clear error."""
    if not value or not str(value).strip():
        raise HTTPException(
            status_code=422,
            detail=f"'{field_name}' is required. Choose one: {[e.value for e in enum_cls]}"
        )
    v = str(value).strip().lower()
    try:
        return enum_cls(v)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid '{field_name}': '{v}'. Choose one: {[e.value for e in enum_cls]}"
        )


def _find_existing_user(db, req):
    """Deduplicate across sources.
    Priority: discord_id > email > name+timezone (case-insensitive).
    """
    if req.discord_id:
        user = db.query(User).filter(User.discord_id == req.discord_id).first()
        if user:
            return user

    if req.email:
        user = db.query(User).filter(User.email == req.email).first()
        if user:
            return user

    if req.name and req.timezone:
        user = db.query(User).filter(
            func.lower(User.name) == req.name.strip().lower(),
            User.timezone == req.timezone,
        ).first()
        if user:
            return user

    return None


@router.post("/pledge", response_model=UserResponse)
def create_pledge(req: PledgeRequest, request: Request, db: Session = Depends(get_db)):
    # --- 0. Rate limit ---
    _prune_rate_limits(_pledge_rate)
    ip = request.client.host if request.client else "unknown"
    now_ts = datetime.now(timezone.utc).timestamp()
    hour_ago = now_ts - 3600
    hits = _pledge_rate.get(ip, [])
    hits = [t for t in hits if t > hour_ago]
    if len(hits) >= _PLEDGE_RATE_LIMIT:
        _pledge_rate[ip] = hits
        raise HTTPException(status_code=429, detail="Too many signups. Try again later.", headers={"Retry-After": "3600"})
    hits.append(now_ts)
    _pledge_rate[ip] = hits

    # --- 0b. Bot protection: honeypot ---
    if req.website:
        # Bot detected — return realistic-looking success but store nothing
        return UserResponse(
            user_id=str(uuid.uuid4()), name=req.name or "",
            jerome_number=_next_jerome_number(db) + 1000,
            country=None, auth_token=str(uuid.uuid4()),
        )

    # --- 0c. Bot protection: time-based ---
    if req.elapsed is not None and req.elapsed < 3000:
        # Too fast — likely bot, return realistic-looking success but store nothing
        return UserResponse(
            user_id=str(uuid.uuid4()), name=req.name or "",
            jerome_number=_next_jerome_number(db) + 1000,
            country=None, auth_token=str(uuid.uuid4()),
        )

    # --- 1. Validate name (no placeholders) ---
    name = (req.name or "").strip()
    if not name or len(name) < 2:
        raise HTTPException(status_code=422, detail="Name must be at least 2 characters.")
    if name.lower() in _PLACEHOLDER_NAMES:
        raise HTTPException(
            status_code=422,
            detail=f"'{name}' is not a valid name. Use your real name."
        )

    # --- 2. Require goal (strict), age_bracket optional ---
    goal = _require_enum(UserGoal, req.goal, "goal")
    age_bracket = None
    if req.age_bracket and str(req.age_bracket).strip():
        try:
            age_bracket = AgeBracket(str(req.age_bracket).strip().lower())
        except ValueError:
            age_bracket = None

    # --- 3. Gender: optional, defaults to "skip" ---
    gender = Gender.skip
    if req.gender and req.gender.strip():
        try:
            gender = Gender(req.gender.strip().lower())
        except ValueError:
            gender = Gender.skip

    # --- 4. Deduplicate across sources ---
    existing = _find_existing_user(db, req)
    if existing:
        if req.source and req.source in _VALID_SOURCES:
            existing.source = UserSource(req.source)
        if not existing.age_bracket:
            existing.age_bracket = age_bracket
        if not existing.goal:
            existing.goal = goal
        if not existing.gender or existing.gender == Gender.skip:
            existing.gender = gender
        # Backfill Jerome# if missing
        if not existing.jerome_number:
            existing.jerome_number = _next_jerome_number(db)
        # Backfill auth_token if missing
        if not existing.auth_token:
            existing.auth_token = str(uuid.uuid4())
        db.commit()
        return UserResponse(
            user_id=existing.id, name=existing.name,
            jerome_number=existing.jerome_number, country=existing.country,
            auth_token=existing.auth_token,
        )

    # --- 5. Resolve country: explicit > IP > timezone ---
    country = req.country
    if not country:
        country = _country_from_ip(request)
    if not country:
        country = _country_from_timezone(req.timezone)

    # --- 6. Fitness level ---
    fitness = FitnessLevel.beginner
    if req.fitness_level in [e.value for e in FitnessLevel]:
        fitness = FitnessLevel(req.fitness_level)

    # --- 7. Source ---
    source = None
    if req.source and req.source in _VALID_SOURCES:
        source = UserSource(req.source)

    # --- 8. Resolve invite code ---
    invited_by = None
    if req.invite_code:
        invite = db.query(InviteCode).filter(
            InviteCode.code == req.invite_code,
            InviteCode.used_by_id.is_(None),
        ).first()
        if invite:
            invited_by = invite.inviter_id

    # --- 9. Assign Jerome# (with retry on race condition) ---
    for _attempt in range(3):
        jerome_number = _next_jerome_number(db)

        # --- 10. Create user ---
        auth_token = str(uuid.uuid4())
        user = User(
            name=name,
            email=req.email,
            discord_id=req.discord_id,
            timezone=req.timezone,
            fitness_level=fitness,
            available_windows=req.available_windows,
            age_bracket=age_bracket,
            gender=gender,
            country=country,
            source=source,
            goal=goal,
            invited_by=invited_by,
            jerome_number=jerome_number,
            github_username=req.github_username,
            role=UserRole.member,
            auth_token=auth_token,
            fingerprint=req.fp,
        )
        db.add(user)
        try:
            db.flush()
            break
        except IntegrityError:
            db.rollback()
    else:
        raise HTTPException(status_code=503, detail="Could not assign Jerome#. Try again.")

    # Mark invite as used
    if req.invite_code and invited_by:
        invite.used_by_id = user.id
        invite.used_at = datetime.now(timezone.utc)

    streak = Streak(user_id=user.id)
    db.add(streak)
    db.commit()

    return UserResponse(
        user_id=user.id, name=user.name,
        jerome_number=user.jerome_number, country=user.country,
        auth_token=user.auth_token,
    )
