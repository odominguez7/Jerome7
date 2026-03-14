"""GET/POST /pod — pod management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from src.api.models import PodResponse, PodMemberInfo
from src.db.database import get_db
from src.db.models import User, Pod, PodMember, Streak
from src.agents.community import CommunityMatcherAgent
from src.agents.context import build_user_context

router = APIRouter()


@router.get("/pod/{user_id}", response_model=PodResponse)
def get_pod(user_id: str, db: DBSession = Depends(get_db)):
    membership = (
        db.query(PodMember)
        .filter(PodMember.user_id == user_id, PodMember.status == "active")
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="No active pod")

    pod = db.query(Pod).filter(Pod.id == membership.pod_id).first()
    if not pod:
        raise HTTPException(status_code=404, detail="Pod not found")

    members = db.query(PodMember).filter(PodMember.pod_id == pod.id).all()
    member_infos = []
    for m in members:
        user = db.query(User).filter(User.id == m.user_id).first()
        streak = db.query(Streak).filter(Streak.user_id == m.user_id).first()
        if user:
            member_infos.append(PodMemberInfo(
                name=user.name,
                current_streak=streak.current_streak if streak else 0,
                last_active=user.last_active_at,
            ))

    return PodResponse(
        pod_id=pod.id,
        pod_name=pod.name,
        members=member_infos,
    )


def _build_pod_response(pod: Pod, db: DBSession) -> PodResponse:
    """Build a PodResponse from a Pod object."""
    members = db.query(PodMember).filter(PodMember.pod_id == pod.id).all()
    member_infos = []
    for m in members:
        user = db.query(User).filter(User.id == m.user_id).first()
        streak = db.query(Streak).filter(Streak.user_id == m.user_id).first()
        if user:
            member_infos.append(PodMemberInfo(
                name=user.name,
                current_streak=streak.current_streak if streak else 0,
                last_active=user.last_active_at,
            ))
    return PodResponse(pod_id=pod.id, pod_name=pod.name, members=member_infos)


@router.post("/pod/{user_id}/match")
def match_pod(user_id: str, db: DBSession = Depends(get_db)):
    # If user already has an active pod, return it
    membership = (
        db.query(PodMember)
        .filter(PodMember.user_id == user_id, PodMember.status == "active")
        .first()
    )
    if membership:
        pod = db.query(Pod).filter(Pod.id == membership.pod_id).first()
        if pod:
            return _build_pod_response(pod, db)

    # Build context and try to find a match
    ctx = build_user_context(user_id, db)
    agent = CommunityMatcherAgent()
    match = agent.find_pod(ctx, db)

    if not match:
        return {"message": "No matches yet — we'll match you when more builders join"}

    # Create the pod
    pod = agent.form_pod(match.proposed_members, db)
    return _build_pod_response(pod, db)
