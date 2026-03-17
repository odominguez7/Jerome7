"""GET /graph/{jerome_number}.svg -- wellness contribution graph for GitHub profiles."""

from datetime import date, timedelta, datetime, timezone

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import User, Streak, Session

router = APIRouter()

# ── Config ───────────────────────────────────────────────────────────────────
_WEEKS = 15  # 15 weeks = ~105 days of history
_CELL = 13
_GAP = 3
_ROWS = 7  # days per week (Mon-Sun)
_LEFT_PAD = 4
_TOP_PAD = 24
_BOTTOM_PAD = 28

_COLOR_EMPTY = "#161b22"
_COLOR_FILL = "#E85D04"
_COLOR_TODAY = "#ff8c3a"
_COLOR_BG = "#0d1117"
_COLOR_TEXT = "#484f58"
_COLOR_TEXT_LIGHT = "#8b949e"
_COLOR_ACCENT = "#E85D04"


def _build_graph_svg(
    name: str,
    jerome_number: int,
    current_streak: int,
    longest_streak: int,
    total_sessions: int,
    session_dates: set[date],
) -> str:
    today = date.today()
    # Start from the Monday of (_WEEKS) weeks ago
    start = today - timedelta(days=today.weekday(), weeks=_WEEKS - 1)

    grid_w = _WEEKS * (_CELL + _GAP) - _GAP
    width = grid_w + _LEFT_PAD * 2
    grid_h = _ROWS * (_CELL + _GAP) - _GAP
    height = _TOP_PAD + grid_h + _BOTTOM_PAD

    cells = []
    for week in range(_WEEKS):
        for day in range(_ROWS):
            d = start + timedelta(weeks=week, days=day)
            if d > today:
                continue
            x = _LEFT_PAD + week * (_CELL + _GAP)
            y = _TOP_PAD + day * (_CELL + _GAP)
            is_today = d == today
            has_session = d in session_dates
            if is_today and has_session:
                color = _COLOR_TODAY
            elif has_session:
                color = _COLOR_FILL
            else:
                color = _COLOR_EMPTY
            rx = "2"
            cells.append(
                f'<rect x="{x}" y="{y}" width="{_CELL}" '
                f'height="{_CELL}" rx="{rx}" fill="{color}">'
                f"<title>{d.isoformat()}"
                f'{" - showed up" if has_session else ""}</title></rect>"'
            )

    # Stats bar at bottom
    stats_y = _TOP_PAD + grid_h + 16
    legend_y = _TOP_PAD + grid_h + 16

    # Header
    header_name = f"Jerome{jerome_number}"
    streak_text = f"{current_streak} day streak" if current_streak > 0 else "start today"

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <style>
    text {{ font-family: -apple-system, 'Segoe UI', monospace; }}
  </style>
  <rect width="{width}" height="{height}" rx="6" fill="{_COLOR_BG}"/>

  <!-- Header -->
  <text x="{_LEFT_PAD}" y="15" fill="{_COLOR_ACCENT}" font-size="11" font-weight="700">{header_name}</text>
  <text x="{width - _LEFT_PAD}" y="15" fill="{_COLOR_TEXT_LIGHT}" font-size="10" text-anchor="end">{streak_text}</text>

  <!-- Grid -->
  {"".join(cells)}

  <!-- Footer stats -->
  <text x="{_LEFT_PAD}" y="{stats_y}" fill="{_COLOR_TEXT}" font-size="9">{total_sessions} sessions</text>
  <text x="{width - _LEFT_PAD}" y="{legend_y}" fill="{_COLOR_TEXT}" font-size="9" text-anchor="end">jerome7.com</text>
</svg>"""
    return svg


@router.get("/graph/{jerome_number}.svg")
def wellness_graph(jerome_number: int, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.jerome_number == jerome_number).first()
    if not user:
        # Render empty graph with CTA
        svg = _build_graph_svg("builder", 0, 0, 0, 0, set())
        return Response(
            content=svg,
            media_type="image/svg+xml",
            headers={"Cache-Control": "public, max-age=300"},
        )

    streak = db.query(Streak).filter(Streak.user_id == user.id).first()
    current = streak.current_streak if streak else 0
    longest = streak.longest_streak if streak else 0
    total = streak.total_sessions if streak else 0

    # Fetch session dates for the graph window
    start_date = date.today() - timedelta(weeks=_WEEKS)
    sessions = (
        db.query(Session.logged_at)
        .filter(
            Session.user_id == user.id,
            Session.logged_at >= datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc),
        )
        .all()
    )
    session_dates = set()
    for (logged_at,) in sessions:
        if logged_at:
            session_dates.add(logged_at.date())

    svg = _build_graph_svg(
        name=user.name,
        jerome_number=jerome_number,
        current_streak=current,
        longest_streak=longest,
        total_sessions=total,
        session_dates=session_dates,
    )
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )
