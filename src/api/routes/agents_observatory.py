"""GET /agents — Agent Observatory. Live dashboard of Jerome7's 5 AI agents."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import func, extract
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import (
    User, Streak, Session as SessionModel, Seven7Session,
    Nudge, Pod, PodMember, SessionFeedback,
)

router = APIRouter()


def _time_ago(delta: timedelta) -> str:
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


@router.get("/agents", response_class=HTMLResponse)
def agents_observatory(db: DBSession = Depends(get_db)):
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    week_ago = now - timedelta(days=7)
    day_ago = now - timedelta(hours=24)

    # ── COACH AGENT data ──
    total_sessions_generated = db.query(Seven7Session).count()
    avg_difficulty = db.query(func.avg(SessionFeedback.difficulty_rating)).scalar() or 0
    latest_session = (
        db.query(Seven7Session)
        .order_by(Seven7Session.generated_at.desc())
        .first()
    )
    coach_last_time = latest_session.generated_at if latest_session else None
    coach_active = coach_last_time and (now - coach_last_time).total_seconds() < 3600

    # ── NUDGE AGENT data ──
    total_nudges = db.query(Nudge).count()
    nudges_24h = db.query(Nudge).filter(Nudge.sent_at >= day_ago).count()
    # Users who have an active streak but haven't logged today
    users_with_streaks = (
        db.query(Streak.user_id)
        .filter(Streak.current_streak > 0)
        .subquery()
    )
    users_logged_today = (
        db.query(SessionModel.user_id)
        .filter(SessionModel.logged_at >= today_start)
        .distinct()
        .subquery()
    )
    at_risk = (
        db.query(func.count())
        .select_from(users_with_streaks)
        .filter(~users_with_streaks.c.user_id.in_(
            db.query(users_logged_today.c.user_id)
        ))
        .scalar()
    ) or 0
    nudge_acted = db.query(Nudge).filter(Nudge.acted_on.is_(True)).count()
    nudge_accuracy = round(nudge_acted / max(total_nudges, 1) * 100)
    latest_nudge = db.query(Nudge).order_by(Nudge.sent_at.desc()).first()
    nudge_active = latest_nudge and (now - latest_nudge.sent_at).total_seconds() < 3600

    # ── STREAK AGENT data ──
    active_streaks = db.query(Streak).filter(Streak.current_streak > 0).count()
    longest_active = (
        db.query(Streak)
        .filter(Streak.current_streak > 0)
        .order_by(Streak.current_streak.desc())
        .first()
    )
    longest_val = longest_active.current_streak if longest_active else 0
    # Chains broken this week (streak_broken_count changed recently — approximate with last_session_date)
    chains_broken_today = (
        db.query(Streak)
        .filter(
            Streak.current_streak == 0,
            Streak.last_session_date is not None,
            Streak.total_sessions > 0,
        )
        .count()
    )
    chains_survived_today = (
        db.query(Streak)
        .filter(
            Streak.current_streak > 0,
            Streak.last_session_date == now.date(),
        )
        .count()
    )
    total_breaks = db.query(func.sum(Streak.streak_broken_count)).scalar() or 0
    streak_active = chains_survived_today > 0 or chains_broken_today > 0

    # ── COMMUNITY AGENT data ──
    total_pods = db.query(Pod).count()
    total_pod_members = db.query(PodMember).count()
    pods_this_week = db.query(Pod).filter(Pod.created_at >= week_ago).count()
    latest_pod = db.query(Pod).order_by(Pod.created_at.desc()).first()
    community_active = latest_pod and (now - latest_pod.created_at).total_seconds() < 86400

    # ── SCHEDULER AGENT data ──
    total_users = db.query(User).count()
    # Most popular session hour
    popular_hour_row = (
        db.query(
            extract("hour", SessionModel.logged_at).label("h"),
            func.count().label("c"),
        )
        .group_by("h")
        .order_by(func.count().desc())
        .first()
    )
    peak_hour = int(popular_hour_row.h) if popular_hour_row else 9
    peak_label = f"{peak_hour:02d}:00 UTC"
    # Timezone distribution (top 5)
    tz_dist = (
        db.query(User.timezone, func.count().label("c"))
        .group_by(User.timezone)
        .order_by(func.count().desc())
        .limit(5)
        .all()
    )
    scheduler_active = total_users > 0

    # ── Build live event feed from recent real activity ──
    events = []

    # Recent sessions
    recent_sessions = (
        db.query(SessionModel, User)
        .join(User, SessionModel.user_id == User.id)
        .order_by(SessionModel.logged_at.desc())
        .limit(5)
        .all()
    )
    for sess, user in recent_sessions:
        streak_obj = db.query(Streak).filter(Streak.user_id == user.id).first()
        s_val = streak_obj.current_streak if streak_obj else 0
        ago = _time_ago(now - sess.logged_at)
        if s_val >= 7:
            events.append((sess.logged_at, f'<span class="ev-icon">&#x1F525;</span> Streak: @{user.name} hit day {s_val}! Chain unbroken.'))
        events.append((sess.logged_at, f'<span class="ev-icon">&#x1F9E0;</span> Coach generated session #{total_sessions_generated} for @{user.name}'))

    # Recent nudges
    recent_nudges = (
        db.query(Nudge, User)
        .join(User, Nudge.user_id == User.id)
        .order_by(Nudge.sent_at.desc())
        .limit(3)
        .all()
    )
    for nudge, user in recent_nudges:
        events.append((nudge.sent_at, f'<span class="ev-icon">&#x1F514;</span> Nudge predicted @{user.name} might skip &mdash; sending reminder'))

    # Recent pods
    recent_pods = (
        db.query(Pod)
        .order_by(Pod.created_at.desc())
        .limit(2)
        .all()
    )
    for pod in recent_pods:
        members = db.query(PodMember, User).join(User, PodMember.user_id == User.id).filter(PodMember.pod_id == pod.id).limit(2).all()
        names = [u.name for _, u in members]
        if len(names) >= 2:
            events.append((pod.created_at, f'<span class="ev-icon">&#x1F465;</span> Community: matched @{names[0]} with @{names[1]} in Pod \'{pod.name}\''))

    # Sort by time desc, take 10
    events.sort(key=lambda x: x[0], reverse=True)
    events = events[:10]

    feed_html = ""
    for ts, msg in events:
        ago = _time_ago(now - ts)
        feed_html += f"""
        <div class="ev-row">
          <span class="ev-time">{ago}</span>
          <span class="ev-msg">{msg}</span>
        </div>"""

    if not feed_html:
        feed_html = '<div class="ev-row" style="color:#484f58;justify-content:center;">Waiting for first activity...</div>'

    # ── Timezone distribution HTML ──
    tz_html = ""
    for tz, count in tz_dist:
        tz_html += f'<span class="tz-tag">{tz} ({count})</span>'
    if not tz_html:
        tz_html = '<span class="tz-tag">UTC (default)</span>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agent Observatory &mdash; Jerome7</title>
<meta name="description" content="Watch Jerome7's 5 AI agents work in real-time.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0f1419; color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    min-height: 100vh;
  }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 40px 20px; }}

  /* Nav */
  .nav {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 48px;
  }}
  .brand {{ font-size: 11px; letter-spacing: 3px; color: #E85D04; text-decoration: none; font-weight: 700; }}
  .nav-links {{ display: flex; gap: 20px; }}
  .nav-links a {{ font-size: 11px; color: #484f58; text-decoration: none; letter-spacing: 1px; }}
  .nav-links a:hover {{ color: #E85D04; }}
  .nav-links a.active {{ color: #E85D04; }}

  /* Header */
  .page-header {{ text-align: center; margin-bottom: 56px; }}
  .page-header h1 {{
    font-size: 14px; letter-spacing: 6px; color: #E85D04;
    text-transform: uppercase; font-weight: 800; margin-bottom: 12px;
  }}
  .page-header p {{
    font-size: 12px; color: #484f58; letter-spacing: 1px;
  }}
  .header-live {{
    display: inline-flex; align-items: center; gap: 8px;
    margin-top: 16px; font-size: 10px; color: #3fb950; letter-spacing: 2px;
  }}
  .header-live .dot {{
    width: 8px; height: 8px; border-radius: 50%; background: #3fb950;
    animation: pulse 2s infinite;
  }}
  @keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.3; }}
  }}
  @keyframes agent-pulse {{
    0% {{ box-shadow: 0 0 0 0 rgba(232, 93, 4, 0.4); }}
    70% {{ box-shadow: 0 0 0 12px rgba(232, 93, 4, 0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(232, 93, 4, 0); }}
  }}

  /* Agent grid */
  .agent-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(310px, 1fr));
    gap: 20px; margin-bottom: 48px;
  }}
  .agent-card {{
    background: #161b22; border: 1px solid #21262d;
    border-radius: 12px; padding: 24px;
    position: relative; transition: border-color 0.3s;
  }}
  .agent-card:hover {{ border-color: #30363d; }}
  .agent-card.recently-active {{
    animation: agent-pulse 2.5s infinite;
  }}
  .agent-top {{
    display: flex; align-items: center; gap: 12px; margin-bottom: 16px;
  }}
  .agent-icon {{ font-size: 28px; }}
  .agent-name {{
    font-size: 13px; font-weight: 700; color: #f0f6fc;
    letter-spacing: 1px;
  }}
  .agent-status {{
    margin-left: auto;
    width: 10px; height: 10px; border-radius: 50%;
  }}
  .agent-status.active {{ background: #3fb950; box-shadow: 0 0 8px #3fb950; }}
  .agent-status.idle {{ background: #d29922; box-shadow: 0 0 8px #d29922; }}

  .agent-action {{
    font-size: 11px; color: #8b949e; margin-bottom: 16px;
    line-height: 1.5; min-height: 36px;
  }}

  .agent-stats {{
    display: grid; grid-template-columns: repeat(2, 1fr);
    gap: 10px;
  }}
  .ag-stat {{
    background: #0f1419; border-radius: 6px; padding: 10px;
  }}
  .ag-stat-val {{
    font-size: 20px; font-weight: 800; color: #f0f6fc; line-height: 1;
  }}
  .ag-stat-val.orange {{ color: #E85D04; }}
  .ag-stat-val.green {{ color: #3fb950; }}
  .ag-stat-val.blue {{ color: #58a6ff; }}
  .ag-stat-label {{
    font-size: 8px; color: #484f58; margin-top: 4px;
    letter-spacing: 1px; text-transform: uppercase;
  }}

  /* Event feed */
  .feed-section {{
    background: #161b22; border: 1px solid #21262d;
    border-radius: 12px; overflow: hidden;
  }}
  .feed-header {{
    padding: 16px 24px; border-bottom: 1px solid #21262d;
    display: flex; align-items: center; gap: 10px;
  }}
  .feed-title {{
    font-size: 10px; letter-spacing: 3px; color: #E85D04;
    text-transform: uppercase;
  }}
  .feed-live {{
    width: 6px; height: 6px; border-radius: 50%; background: #3fb950;
    animation: pulse 2s infinite;
  }}
  .ev-row {{
    display: flex; align-items: center; gap: 12px;
    padding: 10px 24px; border-bottom: 1px solid #0f1419;
    font-size: 11px;
  }}
  .ev-row:nth-child(odd) {{ background: #0f1419; }}
  .ev-time {{
    color: #30363d; min-width: 60px; font-size: 10px;
  }}
  .ev-icon {{ margin-right: 4px; }}
  .ev-msg {{ color: #8b949e; }}

  /* Timezone tags */
  .tz-tags {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }}
  .tz-tag {{
    font-size: 9px; color: #8b949e; background: #0f1419;
    border-radius: 100px; padding: 3px 10px;
    border: 1px solid #21262d;
  }}

  .footer {{
    text-align: center; margin-top: 40px; padding: 20px;
    font-size: 10px; color: #21262d;
  }}
  .footer a {{ color: #484f58; text-decoration: none; }}

  @media (max-width: 700px) {{
    .agent-grid {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>
<div class="container">

  <nav class="nav">
    <a href="/" class="brand">JEROME7</a>
    <div class="nav-links">
      <a href="/timer">TIMER</a>
      <a href="/leaderboard">LEADERBOARD</a>
      <a href="/analytics">ANALYTICS</a>
      <a href="/agents" class="active">AGENTS</a>
    </div>
  </nav>

  <div class="page-header">
    <h1>Agent Observatory</h1>
    <p>Watch Jerome7's AI agents work in real-time</p>
    <div class="header-live">
      <div class="dot"></div>
      5 autonomous agents. No human operators. Always watching.
    </div>
  </div>

  <!-- Agent Cards -->
  <div class="agent-grid">

    <!-- COACH AGENT -->
    <div class="agent-card {"recently-active" if coach_active else ""}">
      <div class="agent-top">
        <span class="agent-icon">&#x1F9E0;</span>
        <span class="agent-name">COACH AGENT</span>
        <div class="agent-status {"active" if coach_active else "idle"}"></div>
      </div>
      <div class="agent-action">
        {"Generated session at " + coach_last_time.strftime("%H:%M UTC") if coach_last_time else "Waiting for next generation cycle"}
      </div>
      <div class="agent-stats">
        <div class="ag-stat">
          <div class="ag-stat-val orange">{total_sessions_generated}</div>
          <div class="ag-stat-label">Sessions Generated</div>
        </div>
        <div class="ag-stat">
          <div class="ag-stat-val">{round(avg_difficulty, 1) if avg_difficulty else "&mdash;"}</div>
          <div class="ag-stat-label">Avg Difficulty</div>
        </div>
      </div>
    </div>

    <!-- NUDGE AGENT -->
    <div class="agent-card {"recently-active" if nudge_active else ""}">
      <div class="agent-top">
        <span class="agent-icon">&#x1F514;</span>
        <span class="agent-name">NUDGE AGENT</span>
        <div class="agent-status {"active" if nudge_active else "idle"}"></div>
      </div>
      <div class="agent-action">
        Predicted {at_risk} user{"s" if at_risk != 1 else ""} at risk of skipping today<br>
        Sent {nudges_24h} nudge{"s" if nudges_24h != 1 else ""} in the last 24h
      </div>
      <div class="agent-stats">
        <div class="ag-stat">
          <div class="ag-stat-val orange">{total_nudges}</div>
          <div class="ag-stat-label">Nudges Sent</div>
        </div>
        <div class="ag-stat">
          <div class="ag-stat-val green">{nudge_accuracy}%</div>
          <div class="ag-stat-label">Accuracy Rate</div>
        </div>
      </div>
    </div>

    <!-- STREAK AGENT -->
    <div class="agent-card {"recently-active" if streak_active else ""}">
      <div class="agent-top">
        <span class="agent-icon">&#x1F525;</span>
        <span class="agent-name">STREAK AGENT</span>
        <div class="agent-status {"active" if streak_active else "idle"}"></div>
      </div>
      <div class="agent-action">
        Watching {active_streaks} active chain{"s" if active_streaks != 1 else ""}<br>
        {chains_broken_today} broke today. {chains_survived_today} survived.
      </div>
      <div class="agent-stats">
        <div class="ag-stat">
          <div class="ag-stat-val orange">{longest_val}</div>
          <div class="ag-stat-label">Longest Active</div>
        </div>
        <div class="ag-stat">
          <div class="ag-stat-val">{active_streaks}</div>
          <div class="ag-stat-label">Active Streaks</div>
        </div>
        <div class="ag-stat">
          <div class="ag-stat-val" style="color:#f85149">{total_breaks}</div>
          <div class="ag-stat-label">Total Breaks</div>
        </div>
        <div class="ag-stat">
          <div class="ag-stat-val green">{chains_survived_today}</div>
          <div class="ag-stat-label">Survived Today</div>
        </div>
      </div>
    </div>

    <!-- COMMUNITY AGENT -->
    <div class="agent-card {"recently-active" if community_active else ""}">
      <div class="agent-top">
        <span class="agent-icon">&#x1F465;</span>
        <span class="agent-name">COMMUNITY AGENT</span>
        <div class="agent-status {"active" if community_active else "idle"}"></div>
      </div>
      <div class="agent-action">
        Matched {pods_this_week} pod{"s" if pods_this_week != 1 else ""} this week<br>
        {total_pod_members} builder{"s" if total_pod_members != 1 else ""} in pods
      </div>
      <div class="agent-stats">
        <div class="ag-stat">
          <div class="ag-stat-val orange">{total_pods}</div>
          <div class="ag-stat-label">Total Pods</div>
        </div>
        <div class="ag-stat">
          <div class="ag-stat-val green">{total_pod_members}</div>
          <div class="ag-stat-label">Pod Members</div>
        </div>
      </div>
    </div>

    <!-- SCHEDULER AGENT -->
    <div class="agent-card {"recently-active" if scheduler_active else ""}">
      <div class="agent-top">
        <span class="agent-icon">&#x1F4C5;</span>
        <span class="agent-name">SCHEDULER AGENT</span>
        <div class="agent-status {"active" if scheduler_active else "idle"}"></div>
      </div>
      <div class="agent-action">
        Learning patterns from {total_users} user{"s" if total_users != 1 else ""}<br>
        Peak session time: {peak_label}
      </div>
      <div class="agent-stats">
        <div class="ag-stat">
          <div class="ag-stat-val orange">{total_users}</div>
          <div class="ag-stat-label">Users Tracked</div>
        </div>
        <div class="ag-stat">
          <div class="ag-stat-val blue">{peak_label}</div>
          <div class="ag-stat-label">Peak Hour</div>
        </div>
      </div>
      <div class="tz-tags" style="margin-top:12px;">
        {tz_html}
      </div>
    </div>

  </div>

  <!-- Live Event Feed -->
  <div class="feed-section">
    <div class="feed-header">
      <div class="feed-live"></div>
      <span class="feed-title">Live Agent Activity</span>
    </div>
    {feed_html}
  </div>

  <div class="footer">
    <a href="/">jerome7.com</a> &middot; <a href="/live">live</a> &middot; <a href="/analytics">analytics</a> &middot; <a href="https://github.com/odominguez7/Jerome7">github</a>
  </div>

</div>
<script>setTimeout(() => location.reload(), 15000);</script>
</body>
</html>"""
    return HTMLResponse(content=html)
