"""POST /pledge — onboarding endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.models import PledgeRequest, UserResponse
from src.db.database import get_db
from src.db.models import User, Streak, FitnessLevel

router = APIRouter()


@router.post("/pledge", response_model=UserResponse)
def create_pledge(req: PledgeRequest, db: Session = Depends(get_db)):
    # Check for existing user by discord_id or email
    if req.discord_id:
        existing = db.query(User).filter(User.discord_id == req.discord_id).first()
        if existing:
            return UserResponse(user_id=existing.id, name=existing.name)
    if req.email:
        existing = db.query(User).filter(User.email == req.email).first()
        if existing:
            return UserResponse(user_id=existing.id, name=existing.name)

    fitness = FitnessLevel(req.fitness_level) if req.fitness_level in [e.value for e in FitnessLevel] else FitnessLevel.beginner

    user = User(
        name=req.name,
        email=req.email,
        discord_id=req.discord_id,
        timezone=req.timezone,
        fitness_level=fitness,
        available_windows=req.available_windows,
    )
    db.add(user)
    db.flush()

    streak = Streak(user_id=user.id)
    db.add(streak)
    db.commit()

    return UserResponse(user_id=user.id, name=user.name)
