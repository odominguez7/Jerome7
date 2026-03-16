"""GitHub README badge endpoint — shows Jerome7 streak as SVG."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import User, Streak

router = APIRouter()


def _badge_svg(label: str, value: str, value_bg: str = "#E85D04") -> str:
    label_w = len(label) * 7.5 + 16
    value_w = len(value) * 7.5 + 16
    total_w = label_w + value_w
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="28">
  <clipPath id="r"><rect width="{total_w}" height="28" rx="3"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_w}" height="28" fill="#161b22"/>
    <rect x="{label_w}" width="{value_w}" height="28" fill="{value_bg}"/>
  </g>
  <g fill="#fff" font-family="monospace" font-size="12" text-anchor="middle">
    <text x="{label_w / 2}" y="18">{label}</text>
    <text x="{label_w + value_w / 2}" y="18">{value}</text>
  </g>
</svg>"""


@router.get("/badge/{jerome_number}.svg")
def badge(jerome_number: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.jerome_number == jerome_number).first()
    if not user:
        svg = _badge_svg("JEROME7", "join jerome7", "#555")
    else:
        streak = db.query(Streak).filter(Streak.user_id == user.id).first()
        days = streak.current_streak if streak else 0
        if days > 0:
            svg = _badge_svg("JEROME7", f"\U0001f525 {days} days")
        else:
            svg = _badge_svg("JEROME7", "start today")
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )
