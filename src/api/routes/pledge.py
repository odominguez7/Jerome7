"""POST /pledge — onboarding with strict validation and deduplication."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.api.models import PledgeRequest, UserResponse
from src.db.database import get_db
from src.db.models import (
    User, Streak, FitnessLevel,
    AgeBracket, Gender, UserSource, UserGoal,
)

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
    # --- 1. Validate name (no placeholders) ---
    name = (req.name or "").strip()
    if not name or len(name) < 2:
        raise HTTPException(status_code=422, detail="Name must be at least 2 characters.")
    if name.lower() in _PLACEHOLDER_NAMES:
        raise HTTPException(
            status_code=422,
            detail=f"'{name}' is not a valid name. Use your real name."
        )

    # --- 2. Require goal and age_bracket (strict) ---
    goal = _require_enum(UserGoal, req.goal, "goal")
    age_bracket = _require_enum(AgeBracket, req.age_bracket, "age_bracket")

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
        db.commit()
        return UserResponse(user_id=existing.id, name=existing.name, country=existing.country)

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

    # --- 8. Create user ---
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
    )
    db.add(user)
    db.flush()

    streak = Streak(user_id=user.id)
    db.add(streak)
    db.commit()

    return UserResponse(user_id=user.id, name=user.name, country=user.country)
