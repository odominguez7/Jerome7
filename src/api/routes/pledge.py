"""POST /pledge — onboarding endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.models import PledgeRequest, UserResponse
from src.db.database import get_db
from src.db.models import (
    User, Streak, FitnessLevel,
    AgeBracket, Gender, UserSource, UserGoal,
)

router = APIRouter()

# Map timezone prefix → country (covers ~90% of real users)
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


def _country_from_timezone(tz: str) -> str | None:
    """Best-effort country code from IANA timezone."""
    if not tz or tz == "UTC":
        return None
    return _TZ_COUNTRY_MAP.get(tz)


def _safe_enum(enum_cls, value):
    """Return enum member if value is valid, else None."""
    if not value:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        return None


@router.post("/pledge", response_model=UserResponse)
def create_pledge(req: PledgeRequest, db: Session = Depends(get_db)):
    # Check for existing user by discord_id or email
    if req.discord_id:
        existing = db.query(User).filter(User.discord_id == req.discord_id).first()
        if existing:
            return UserResponse(user_id=existing.id, name=existing.name, country=existing.country)
    if req.email:
        existing = db.query(User).filter(User.email == req.email).first()
        if existing:
            return UserResponse(user_id=existing.id, name=existing.name, country=existing.country)

    fitness = FitnessLevel(req.fitness_level) if req.fitness_level in [e.value for e in FitnessLevel] else FitnessLevel.beginner

    # Auto-derive country from timezone if not explicitly provided
    country = req.country or _country_from_timezone(req.timezone)

    user = User(
        name=req.name,
        email=req.email,
        discord_id=req.discord_id,
        timezone=req.timezone,
        fitness_level=fitness,
        available_windows=req.available_windows,
        age_bracket=_safe_enum(AgeBracket, req.age_bracket),
        gender=_safe_enum(Gender, req.gender),
        country=country,
        source=_safe_enum(UserSource, req.source),
        goal=_safe_enum(UserGoal, req.goal),
    )
    db.add(user)
    db.flush()

    streak = Streak(user_id=user.id)
    db.add(streak)
    db.commit()

    return UserResponse(user_id=user.id, name=user.name, country=user.country)
