"""POST /onboarding/{user_id} — complete the onboarding survey."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.models import OnboardingSurveyRequest, OnboardingSurveyResponse
from src.db.database import get_db
from src.db.models import User, OnboardingSurvey, ExperienceLevel

router = APIRouter()


@router.post("/onboarding/{user_id}", response_model=OnboardingSurveyResponse)
def submit_onboarding(user_id: str, req: OnboardingSurveyRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Check for existing survey
    existing = db.query(OnboardingSurvey).filter(OnboardingSurvey.user_id == user_id).first()
    if existing:
        # Update existing survey
        if req.role:
            existing.role = req.role
        if req.experience_level:
            existing.experience_level = _parse_experience(req.experience_level)
        if req.primary_goal:
            existing.primary_goal = req.primary_goal
        if req.preferred_time:
            existing.preferred_time = req.preferred_time
        if req.burnout_level is not None:
            existing.burnout_level = req.burnout_level
        if req.how_heard:
            existing.how_heard = req.how_heard
        user.onboarding_complete = True
        db.commit()
        return OnboardingSurveyResponse(
            survey_id=existing.id,
            jerome_number=user.jerome_number,
            onboarding_complete=True,
        )

    # Create new survey
    exp = _parse_experience(req.experience_level)
    survey = OnboardingSurvey(
        user_id=user_id,
        role=req.role,
        experience_level=exp,
        primary_goal=req.primary_goal,
        preferred_time=req.preferred_time,
        burnout_level=req.burnout_level,
        how_heard=req.how_heard,
    )
    db.add(survey)
    user.onboarding_complete = True
    db.commit()

    return OnboardingSurveyResponse(
        survey_id=survey.id,
        jerome_number=user.jerome_number,
        onboarding_complete=True,
    )


def _parse_experience(val):
    if not val:
        return None
    try:
        return ExperienceLevel(val.strip().lower())
    except ValueError:
        return None
