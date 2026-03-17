"""GET /graph/{jerome_number}.svg -- wellness contribution graph for GitHub profiles."""

from datetime import date, timedelta, datetime, timezone

from fastapi import APIRouter, Depends, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session as DBSession

from src.api.meta import head_meta, nav_html
from src.db.database import get_db
from src.db.models import User, Streak, Session

router = APIRouter()

# ── Config ───────────────────────────────────────────────────────────────────
_WEEKS = 20  # 20 weeks = ~140 days
_CELL = 11
_GAP = 3
_ROWS = 7
_LEFT_PAD = 36  # room for day labels
_TOP_PAD = 36
_BOTTOM_PAD = 40

_COLOR_EMPTY = "#161b22"
_COLOR_BG = "#0d1117"
_COLOR_BORDER = "#21262d"
_COLOR_TEXT = "#484f58"
_COLOR_TEXT_LIGHT = "#8b949e"
_COLOR_ACCENT = "#E85D04"

# Intensity scale (like GitHub's green scale)
_INTENSITY = [
    "#161b22",  # 0: empty
    "#E85D04",  # 1: showed up (single session)
]

_DAY_LABELS = ["Mon", "", "Wed", "", "Fri", "", ""]


def _build_graph_svg(
    jerome_number: int,
    current_streak: int,
    longest_streak: int,
    total_sessions: int,
    session_dates: set[date],
) -> str:
    today = date.today()
    start = today - timedelta(days=today.weekday(), weeks=_WEEKS - 1)

    grid_w = _WEEKS * (_CELL + _GAP) - _GAP
    width = _LEFT_PAD + grid_w + 12
    grid_h = _ROWS * (_CELL + _GAP) - _GAP
    height = _TOP_PAD + grid_h + _BOTTOM_PAD

    # Day labels
    day_labels = []
    for i, label in enumerate(_DAY_LABELS):
        if label:
            y = _TOP_PAD + i * (_CELL + _GAP) + _CELL - 2
            day_labels.append(
                f'<text x="{_LEFT_PAD - 6}" y="{y}" fill="{_COLOR_TEXT}" '
                f'font-size="9" text-anchor="end">{label}</text>'
            )

    # Month labels
    month_labels = []
    last_month = -1
    for week in range(_WEEKS):
        d = start + timedelta(weeks=week)
        if d.month != last_month:
            last_month = d.month
            x = _LEFT_PAD + week * (_CELL + _GAP)
            month_labels.append(
                f'<text x="{x}" y="{_TOP_PAD - 8}" fill="{_COLOR_TEXT}" '
                f'font-size="9">{d.strftime("%b")}</text>'
            )

    # Grid cells
    cells = []
    active_days = 0
    for week in range(_WEEKS):
        for day in range(_ROWS):
            d = start + timedelta(weeks=week, days=day)
            if d > today:
                continue
            x = _LEFT_PAD + week * (_CELL + _GAP)
            y = _TOP_PAD + day * (_CELL + _GAP)
            is_today = d == today
            has_session = d in session_dates
            if has_session:
                active_days += 1

            if is_today and has_session:
                color = "#ff8c3a"
            elif is_today:
                color = "#30363d"
            elif has_session:
                color = _COLOR_ACCENT
            else:
                color = _COLOR_EMPTY

            cells.append(
                f'<rect x="{x}" y="{y}" width="{_CELL}" '
                f'height="{_CELL}" rx="2" fill="{color}">'
                f'<title>{d.isoformat()}'
                f'{" - showed up" if has_session else ""}</title></rect>'
            )

    # Stats
    stats_y = _TOP_PAD + grid_h + 20
    header_name = f"Jerome{jerome_number}" if jerome_number else "Jerome?"

    # Streak flame emoji for active streaks
    streak_display = ""
    if current_streak > 0:
        streak_display = f"{current_streak} day streak"
    else:
        streak_display = "start today"

    # Calculate consistency %
    total_possible = (_WEEKS * 7)
    consistency = round((active_days / total_possible) * 100) if total_possible > 0 else 0

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; }}
  </style>
  <rect width="{width}" height="{height}" rx="6" fill="{_COLOR_BG}" stroke="{_COLOR_BORDER}" stroke-width="1"/>

  <!-- Header -->
  <text x="{_LEFT_PAD}" y="18" fill="{_COLOR_ACCENT}" font-size="12" font-weight="700">{header_name}</text>
  <text x="{_LEFT_PAD}" y="28" fill="{_COLOR_TEXT_LIGHT}" font-size="9">i breathe before i ship</text>
  <text x="{width - 10}" y="22" fill="{_COLOR_TEXT_LIGHT}" font-size="10" text-anchor="end">{streak_display}</text>

  <!-- Month labels -->
  {"".join(month_labels)}

  <!-- Day labels -->
  {"".join(day_labels)}

  <!-- Grid -->
  {"".join(cells)}

  <!-- Footer -->
  <text x="{_LEFT_PAD}" y="{stats_y}" fill="{_COLOR_TEXT}" font-size="9">{total_sessions} sessions  |  {consistency}% consistent  |  longest: {longest_streak}d</text>
  <text x="{width - 10}" y="{stats_y}" fill="{_COLOR_TEXT}" font-size="9" text-anchor="end">jerome7.com</text>
</svg>"""
    return svg


@router.get("/graph/{jerome_number}.svg")
def wellness_graph(jerome_number: int, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.jerome_number == jerome_number).first()
    if not user:
        svg = _build_graph_svg(0, 0, 0, 0, set())
        return Response(
            content=svg,
            media_type="image/svg+xml",
            headers={"Cache-Control": "public, max-age=300"},
        )

    streak = db.query(Streak).filter(Streak.user_id == user.id).first()
    current = streak.current_streak if streak else 0
    longest = streak.longest_streak if streak else 0
    total = streak.total_sessions if streak else 0

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


@router.get("/graph", response_class=HTMLResponse)
def graph_page():
    """Public page: view your wellness contribution graph + copy snippet."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Wellness Graph | Jerome7</title>
{head_meta(title="Wellness Graph | Jerome7", description="Your wellness contribution graph. Add it to your GitHub profile.", url="https://jerome7.com/graph")}
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#0d1117; color:#e6edf3; font-family:'JetBrains Mono',monospace; min-height:100vh; }}
  .container {{ max-width:560px; margin:0 auto; padding:100px 24px 60px; text-align:center; }}
  h1 {{ font-size:22px; font-weight:700; margin-bottom:4px; letter-spacing:1px; }}
  .tagline {{ color:#E85D04; font-size:13px; margin-bottom:8px; font-style:italic; }}
  .sub {{ color:#8b949e; font-size:13px; margin-bottom:32px; line-height:1.6; }}
  .graph-preview {{ margin-bottom:24px; }}
  .graph-preview img {{ width:100%; border-radius:6px; }}
  .copy-btn {{ width:100%; padding:14px; background:#E85D04; border:none; border-radius:100px; color:#fff; font-family:inherit; font-size:14px; font-weight:700; letter-spacing:1px; cursor:pointer; margin-bottom:12px; }}
  .copy-btn:hover {{ background:#d14e00; }}
  .snippet {{ background:#161b22; border:1px solid #30363d; border-radius:6px; padding:12px 16px; font-size:11px; color:#8b949e; word-break:break-all; text-align:left; margin-bottom:24px; user-select:all; }}
  .hint {{ color:#484f58; font-size:11px; line-height:1.6; }}
  .toast {{ display:none; position:fixed; bottom:24px; left:50%; transform:translateX(-50%); background:#E85D04; color:#fff; padding:10px 24px; border-radius:100px; font-size:13px; font-weight:700; z-index:9999; }}
  .start-link {{ display:inline-block; margin-top:24px; color:#E85D04; font-size:13px; text-decoration:none; letter-spacing:1px; }}
  .start-link:hover {{ text-decoration:underline; }}
  .no-jerome {{ margin-top:32px; padding:24px; background:#161b22; border:1px solid #21262d; border-radius:12px; }}
  .no-jerome h2 {{ font-size:16px; margin-bottom:8px; }}
  .no-jerome p {{ color:#8b949e; font-size:12px; line-height:1.6; }}
</style>
</head>
<body>
{nav_html()}
<div class="container">
  <h1>WELLNESS GRAPH</h1>
  <p class="tagline">i breathe before i ship</p>
  <p class="sub">Your GitHub profile shows code contributions.<br>Now it shows you take care of yourself too.</p>

  <div class="graph-preview">
    <img id="graphImg" src="/graph/0.svg" alt="Wellness contribution graph">
  </div>

  <div id="hasJerome" style="display:none">
    <div class="snippet" id="snippet"></div>
    <button class="copy-btn" onclick="copySnippet()">COPY FOR GITHUB README</button>
    <p class="hint">One line in your README. Updated daily. Every visitor sees your streak.</p>
  </div>

  <div id="noJerome">
    <div class="no-jerome">
      <h2>Get your graph</h2>
      <p>Complete one 7-minute session.<br>Your Jerome# and graph are assigned automatically.<br>No signup. No login. Just breathe.</p>
      <a href="/timer" class="start-link">START YOUR 7 MINUTES</a>
    </div>
  </div>
</div>

<div class="toast" id="toast">copied!</div>

<script>
window.addEventListener('DOMContentLoaded', function() {{
  try {{
    const u = JSON.parse(localStorage.getItem('jerome7_user') || '{{}}');
    if (u.jeromeNumber) {{
      const num = u.jeromeNumber;
      document.getElementById('graphImg').src = '/graph/' + num + '.svg?t=' + Date.now();
      document.getElementById('snippet').textContent = '![Jerome7 Wellness](https://jerome7.com/graph/' + num + '.svg)';
      document.getElementById('hasJerome').style.display = 'block';
      document.getElementById('noJerome').style.display = 'none';
    }}
  }} catch {{}}
}});

function copySnippet() {{
  const text = document.getElementById('snippet').textContent;
  navigator.clipboard.writeText(text).then(function() {{
    const t = document.getElementById('toast');
    t.textContent = 'copied! paste in your GitHub profile README';
    t.style.display = 'block';
    setTimeout(function() {{ t.style.display = 'none'; }}, 3000);
  }});
}}
</script>
</body>
</html>"""
