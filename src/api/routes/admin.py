"""Admin dashboard — password-protected metrics page."""

import os
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import func, distinct, cast, Date
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import User, Session as SessionModel, Streak

router = APIRouter()

ADMIN_KEY = os.getenv("ADMIN_API_KEY", "")


def _check_key(key: str | None) -> bool:
    return bool(ADMIN_KEY) and key == ADMIN_KEY


@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(key: str = Query(None), db: Session = Depends(get_db)):
    if not _check_key(key):
        return HTMLResponse(
            "<h1 style='color:#E85D04;font-family:monospace;background:#0d1117;margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center'>401 — Unauthorized</h1>",
            status_code=401,
        )

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    thirty_ago = now - timedelta(days=30)

    # ── Overview cards ──
    total_users = db.query(func.count(User.id)).scalar() or 0
    verified_users = db.query(func.count(User.id)).filter(User.email.isnot(None), User.email != "").scalar() or 0
    sessions_today = db.query(func.count(SessionModel.id)).filter(SessionModel.logged_at >= today_start).scalar() or 0
    active_week = db.query(func.count(distinct(SessionModel.user_id))).filter(SessionModel.logged_at >= week_ago).scalar() or 0

    # ── Growth chart (last 30 days signups grouped by date) ──
    signup_rows = (
        db.query(
            cast(User.created_at, Date).label("day"),
            func.count(User.id).label("cnt"),
        )
        .filter(User.created_at >= thirty_ago)
        .group_by(cast(User.created_at, Date))
        .order_by(cast(User.created_at, Date))
        .all()
    )
    # Build full 30-day array
    signup_map = {str(r.day): r.cnt for r in signup_rows}
    growth_labels = []
    growth_values = []
    cumulative = db.query(func.count(User.id)).filter(User.created_at < thirty_ago).scalar() or 0
    for i in range(30):
        d = (thirty_ago + timedelta(days=i)).strftime("%Y-%m-%d")
        cumulative += signup_map.get(d, 0)
        growth_labels.append(d[5:])  # MM-DD
        growth_values.append(cumulative)

    # ── Retention ──
    def retention_rate(day_n: int) -> float:
        cutoff = now - timedelta(days=day_n)
        eligible = db.query(func.count(User.id)).filter(User.created_at <= cutoff).scalar() or 0
        if eligible == 0:
            return 0.0
        returned = (
            db.query(func.count(distinct(SessionModel.user_id)))
            .join(User, SessionModel.user_id == User.id)
            .filter(
                User.created_at <= cutoff,
                SessionModel.logged_at >= User.created_at + timedelta(days=day_n),
            )
            .scalar() or 0
        )
        return round(returned / eligible * 100, 1)

    retention = {
        1: retention_rate(1),
        7: retention_rate(7),
        14: retention_rate(14),
        30: retention_rate(30),
    }

    # ── DAU last 14 days ──
    dau_rows = (
        db.query(
            cast(SessionModel.logged_at, Date).label("day"),
            func.count(distinct(SessionModel.user_id)).label("cnt"),
        )
        .filter(SessionModel.logged_at >= now - timedelta(days=14))
        .group_by(cast(SessionModel.logged_at, Date))
        .order_by(cast(SessionModel.logged_at, Date))
        .all()
    )
    dau_map = {str(r.day): r.cnt for r in dau_rows}
    dau_labels = []
    dau_values = []
    for i in range(14):
        d = (now - timedelta(days=13) + timedelta(days=i)).strftime("%Y-%m-%d")
        dau_labels.append(d[5:])
        dau_values.append(dau_map.get(d, 0))

    # ── Recent signups (last 20) ──
    recent_users = (
        db.query(User)
        .order_by(User.created_at.desc())
        .limit(20)
        .all()
    )
    recent_rows_html = ""
    for u in recent_users:
        sess_count = db.query(func.count(SessionModel.id)).filter(SessionModel.user_id == u.id).scalar() or 0
        ago = _relative_time(u.created_at, now) if u.created_at else "—"
        jnum = f"Jerome{u.jerome_number}" if u.jerome_number else "—"
        goal = u.goal.value if u.goal else "—"
        country = u.country or "—"
        name = _esc(u.name or "—")
        recent_rows_html += f"<tr><td>{jnum}</td><td>{name}</td><td>{goal}</td><td>{country}</td><td>{ago}</td><td>{sess_count}</td></tr>\n"

    # ── Top users by sessions ──
    top_users_q = (
        db.query(
            User.jerome_number,
            User.name,
            func.count(SessionModel.id).label("sess"),
        )
        .join(SessionModel, SessionModel.user_id == User.id)
        .group_by(User.id)
        .order_by(func.count(SessionModel.id).desc())
        .limit(10)
        .all()
    )
    top_rows_html = ""
    for row in top_users_q:
        jnum = f"Jerome{row.jerome_number}" if row.jerome_number else "—"
        name = _esc(row.name or "—")
        streak_obj = db.query(Streak).filter(Streak.user_id == db.query(User.id).filter(User.name == row.name).limit(1).scalar_subquery()).first()
        cur_streak = streak_obj.current_streak if streak_obj else 0
        last_active = streak_obj.last_session_date if streak_obj else "—"
        top_rows_html += f"<tr><td>{jnum}</td><td>{name}</td><td>{row.sess}</td><td>{cur_streak}</td><td>{last_active}</td></tr>\n"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<meta name="theme-color" content="#0d1117">
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&display=swap">
<title>Jerome7 — Admin</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0d1117; color: #c9d1d9; font-family: 'JetBrains Mono', monospace; padding: 24px; }}
  h1 {{ color: #E85D04; font-size: 1.6rem; margin-bottom: 8px; }}
  h2 {{ color: #E85D04; font-size: 1.1rem; margin: 32px 0 12px; }}
  .subtitle {{ color: #484f58; font-size: 0.75rem; margin-bottom: 24px; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 8px; }}
  .card {{ background: #161b22; border: 1px solid #21262d; border-radius: 12px; padding: 20px; }}
  .card .label {{ color: #484f58; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; }}
  .card .value {{ color: #E85D04; font-size: 2rem; font-weight: 800; margin-top: 4px; }}
  canvas {{ background: #161b22; border: 1px solid #21262d; border-radius: 12px; width: 100%; max-width: 900px; }}
  table {{ width: 100%; border-collapse: collapse; background: #161b22; border: 1px solid #21262d; border-radius: 12px; overflow: hidden; font-size: 0.78rem; }}
  th {{ background: #1c2128; color: #E85D04; text-align: left; padding: 10px 12px; font-weight: 700; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.5px; }}
  td {{ padding: 8px 12px; border-top: 1px solid #21262d; }}
  tr:hover td {{ background: #1c2128; }}
  .ret-green {{ color: #3fb950; font-weight: 700; }}
  .ret-yellow {{ color: #d29922; font-weight: 700; }}
  .ret-red {{ color: #f85149; font-weight: 700; }}
  .section {{ margin-bottom: 16px; }}
</style>
</head>
<body>

<h1>JEROME7 ADMIN</h1>
<div class="subtitle">Generated {now.strftime("%Y-%m-%d %H:%M UTC")}</div>

<div class="cards">
  <div class="card"><div class="label">Total Users</div><div class="value">{total_users}</div></div>
  <div class="card"><div class="label">Verified (Email)</div><div class="value">{verified_users}</div></div>
  <div class="card"><div class="label">Sessions Today</div><div class="value">{sessions_today}</div></div>
  <div class="card"><div class="label">Active This Week</div><div class="value">{active_week}</div></div>
</div>

<h2>Signups — Cumulative (30 days)</h2>
<div class="section"><canvas id="growthChart" height="220"></canvas></div>

<h2>Retention</h2>
<table style="max-width:500px">
  <tr><th>Day</th><th>Rate</th></tr>
  {"".join(_retention_row(d, retention[d]) for d in [1, 7, 14, 30])}
</table>

<h2>Daily Active Users (14 days)</h2>
<div class="section"><canvas id="dauChart" height="200"></canvas></div>

<h2>Recent Signups</h2>
<table>
  <tr><th>Jerome#</th><th>Name</th><th>Goal</th><th>Country</th><th>Signed Up</th><th>Sessions</th></tr>
  {recent_rows_html}
</table>

<h2>Top Users</h2>
<table>
  <tr><th>Jerome#</th><th>Name</th><th>Sessions</th><th>Streak</th><th>Last Active</th></tr>
  {top_rows_html}
</table>

<script>
// ── Growth chart ──
(function() {{
  const labels = {growth_labels};
  const values = {growth_values};
  const c = document.getElementById('growthChart');
  const ctx = c.getContext('2d');
  const W = c.width = c.offsetWidth;
  const H = c.height = 220;
  const pad = {{l:50, r:20, t:20, b:30}};
  const gw = W - pad.l - pad.r;
  const gh = H - pad.t - pad.b;
  const maxV = Math.max(...values, 1);

  ctx.fillStyle = '#161b22';
  ctx.fillRect(0, 0, W, H);

  // grid lines
  ctx.strokeStyle = '#21262d';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {{
    const y = pad.t + gh - (gh * i / 4);
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke();
    ctx.fillStyle = '#484f58'; ctx.font = '10px JetBrains Mono';
    ctx.textAlign = 'right';
    ctx.fillText(Math.round(maxV * i / 4), pad.l - 6, y + 4);
  }}

  // line
  ctx.strokeStyle = '#E85D04';
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  for (let i = 0; i < values.length; i++) {{
    const x = pad.l + (gw * i / (values.length - 1));
    const y = pad.t + gh - (gh * values[i] / maxV);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }}
  ctx.stroke();

  // x-labels
  ctx.fillStyle = '#484f58'; ctx.font = '9px JetBrains Mono'; ctx.textAlign = 'center';
  for (let i = 0; i < labels.length; i += 5) {{
    const x = pad.l + (gw * i / (labels.length - 1));
    ctx.fillText(labels[i], x, H - 6);
  }}
}})();

// ── DAU bar chart ──
(function() {{
  const labels = {dau_labels};
  const values = {dau_values};
  const c = document.getElementById('dauChart');
  const ctx = c.getContext('2d');
  const W = c.width = c.offsetWidth;
  const H = c.height = 200;
  const pad = {{l:50, r:20, t:20, b:30}};
  const gw = W - pad.l - pad.r;
  const gh = H - pad.t - pad.b;
  const maxV = Math.max(...values, 1);
  const bw = gw / values.length * 0.7;

  ctx.fillStyle = '#161b22';
  ctx.fillRect(0, 0, W, H);

  // grid
  ctx.strokeStyle = '#21262d'; ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {{
    const y = pad.t + gh - (gh * i / 4);
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke();
    ctx.fillStyle = '#484f58'; ctx.font = '10px JetBrains Mono'; ctx.textAlign = 'right';
    ctx.fillText(Math.round(maxV * i / 4), pad.l - 6, y + 4);
  }}

  // bars
  for (let i = 0; i < values.length; i++) {{
    const x = pad.l + (gw * i / values.length) + (gw / values.length - bw) / 2;
    const bh = (values[i] / maxV) * gh;
    const y = pad.t + gh - bh;
    ctx.fillStyle = '#E85D04';
    ctx.fillRect(x, y, bw, bh);
  }}

  // x-labels
  ctx.fillStyle = '#484f58'; ctx.font = '9px JetBrains Mono'; ctx.textAlign = 'center';
  for (let i = 0; i < labels.length; i += 2) {{
    const x = pad.l + (gw * i / values.length) + (gw / values.length) / 2;
    ctx.fillText(labels[i], x, H - 6);
  }}
}})();
</script>

</body>
</html>"""

    return HTMLResponse(html)


def _retention_row(day: int, rate: float) -> str:
    cls = "ret-green" if rate > 50 else ("ret-yellow" if rate > 25 else "ret-red")
    return f'<tr><td>Day {day}</td><td class="{cls}">{rate}%</td></tr>\n'


def _relative_time(dt: datetime | None, now: datetime) -> str:
    if not dt:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    secs = int(diff.total_seconds())
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{secs // 60}m ago"
    if secs < 86400:
        return f"{secs // 3600}h ago"
    return f"{secs // 86400}d ago"


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
