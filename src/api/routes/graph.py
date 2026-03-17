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
                f'{" - showed up" if has_session else ""}</title></rect>'
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
  h1 {{ font-size:24px; font-weight:700; margin-bottom:8px; letter-spacing:1px; }}
  .sub {{ color:#8b949e; font-size:13px; margin-bottom:32px; line-height:1.6; }}
  .graph-preview {{ margin-bottom:24px; }}
  .graph-preview img {{ width:100%; border-radius:6px; border:1px solid #21262d; }}
  .num-input {{ display:flex; gap:8px; align-items:center; justify-content:center; margin-bottom:24px; }}
  .num-input label {{ color:#8b949e; font-size:13px; }}
  .num-input input {{ width:80px; padding:8px 12px; background:#161b22; border:1px solid #30363d; border-radius:6px; color:#e6edf3; font-family:inherit; font-size:14px; text-align:center; }}
  .num-input input:focus {{ outline:none; border-color:#E85D04; }}
  .copy-btn {{ width:100%; padding:14px; background:#E85D04; border:none; border-radius:100px; color:#fff; font-family:inherit; font-size:14px; font-weight:700; letter-spacing:1px; cursor:pointer; margin-bottom:12px; }}
  .copy-btn:hover {{ background:#d14e00; }}
  .snippet {{ background:#161b22; border:1px solid #30363d; border-radius:6px; padding:12px 16px; font-size:12px; color:#8b949e; word-break:break-all; text-align:left; margin-bottom:24px; }}
  .hint {{ color:#484f58; font-size:11px; line-height:1.6; }}
  .toast {{ display:none; position:fixed; bottom:24px; left:50%; transform:translateX(-50%); background:#E85D04; color:#fff; padding:10px 24px; border-radius:100px; font-size:13px; font-weight:700; z-index:9999; }}
  .start-link {{ display:inline-block; margin-top:24px; color:#E85D04; font-size:13px; text-decoration:none; }}
  .start-link:hover {{ text-decoration:underline; }}
</style>
</head>
<body>
{nav_html()}
<div class="container">
  <h1>WELLNESS GRAPH</h1>
  <p class="sub">Your GitHub profile has a code contribution graph.<br>Now it has a wellness one too.</p>

  <div class="num-input">
    <label>Your Jerome#</label>
    <input type="number" id="jnum" min="1" placeholder="7" oninput="updatePreview()">
  </div>

  <div class="graph-preview">
    <img id="graphImg" src="/graph/0.svg" alt="Wellness contribution graph">
  </div>

  <div class="snippet" id="snippet">![Jerome7](https://jerome7.com/graph/YOUR_NUMBER.svg)</div>

  <button class="copy-btn" onclick="copySnippet()">COPY FOR GITHUB README</button>

  <p class="hint">Paste this one line into your GitHub profile README.<br>Every visitor sees your wellness streak next to your code.</p>

  <a href="/timer" class="start-link">Don't have a Jerome#? Start your first session.</a>
</div>

<div class="toast" id="toast">copied!</div>

<script>
function getStoredNumber() {{
  try {{
    const u = JSON.parse(localStorage.getItem('jerome7_user') || '{{}}');
    return u.jeromeNumber || '';
  }} catch {{ return ''; }}
}}

window.addEventListener('DOMContentLoaded', function() {{
  const stored = getStoredNumber();
  if (stored) {{
    document.getElementById('jnum').value = stored;
    updatePreview();
  }}
}});

function updatePreview() {{
  const num = document.getElementById('jnum').value || 'YOUR_NUMBER';
  document.getElementById('graphImg').src = '/graph/' + (parseInt(num) || 0) + '.svg?t=' + Date.now();
  document.getElementById('snippet').textContent = '![Jerome7](https://jerome7.com/graph/' + num + '.svg)';
}}

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
