"""GET /live — real-time collective movement dashboard. The YC demo killer."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import User, Streak, Session as SessionModel

router = APIRouter()

_FLAG = {
    "US": "🇺🇸", "CA": "🇨🇦", "MX": "🇲🇽", "BR": "🇧🇷", "AR": "🇦🇷",
    "GB": "🇬🇧", "FR": "🇫🇷", "DE": "🇩🇪", "ES": "🇪🇸", "IT": "🇮🇹",
    "NL": "🇳🇱", "SE": "🇸🇪", "NO": "🇳🇴", "CH": "🇨🇭", "PT": "🇵🇹",
    "PL": "🇵🇱", "TR": "🇹🇷", "RU": "🇷🇺", "UA": "🇺🇦",
    "JP": "🇯🇵", "KR": "🇰🇷", "CN": "🇨🇳", "IN": "🇮🇳", "SG": "🇸🇬",
    "AE": "🇦🇪", "SA": "🇸🇦", "ID": "🇮🇩", "TH": "🇹🇭", "PH": "🇵🇭",
    "AU": "🇦🇺", "NZ": "🇳🇿", "NG": "🇳🇬", "KE": "🇰🇪", "ZA": "🇿🇦",
    "EG": "🇪🇬", "GH": "🇬🇭", "CO": "🇨🇴", "PE": "🇵🇪", "CL": "🇨🇱",
    "IE": "🇮🇪",
}


@router.get("/live", response_class=HTMLResponse)
def live_dashboard(db: DBSession = Depends(get_db)):
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)

    # Core numbers
    total_users = db.query(User).count()
    total_sessions = db.query(SessionModel).count()
    active_streaks = db.query(Streak).filter(Streak.current_streak > 0).count()
    showed_up_today = db.query(SessionModel).filter(
        SessionModel.logged_at >= today_start
    ).count()

    # Country counts
    countries = dict(
        db.query(User.country, func.count(User.id))
        .filter(User.country.isnot(None))
        .group_by(User.country)
        .order_by(func.count(User.id).desc())
        .all()
    )
    num_countries = len(countries)

    # Total minutes moved (7 min per session)
    total_minutes = total_sessions * 7

    # Recent activity feed (last 20 sessions)
    recent = (
        db.query(SessionModel, User)
        .join(User, SessionModel.user_id == User.id)
        .order_by(SessionModel.logged_at.desc())
        .limit(20)
        .all()
    )

    # Longest current streak
    top_streak = db.query(Streak).order_by(Streak.current_streak.desc()).first()
    longest_name = ""
    longest_val = 0
    if top_streak:
        top_user = db.query(User).filter(User.id == top_streak.user_id).first()
        if top_user:
            longest_name = top_user.name
            longest_val = top_streak.current_streak

    # Build country globe dots
    country_dots = ""
    for code, count in sorted(countries.items(), key=lambda x: x[1], reverse=True)[:15]:
        flag = _FLAG.get(code, "🌍")
        country_dots += f'<span class="globe-dot">{flag} {count}</span>'

    # Build activity feed
    feed_items = ""
    for session, user in recent:
        flag = _FLAG.get(user.country, "") if user.country else ""
        streak_obj = db.query(Streak).filter(Streak.user_id == user.id).first()
        streak_val = streak_obj.current_streak if streak_obj else 0
        ago = _time_ago(now - session.logged_at)
        feed_items += f"""
        <div class="feed-item">
          <div class="feed-left">
            <span class="feed-flag">{flag}</span>
            <span class="feed-name">{user.name}</span>
            <span class="feed-streak">Day {streak_val}</span>
          </div>
          <span class="feed-time">{ago}</span>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jerome7 — Live</title>
<meta name="description" content="{total_users} builders. {num_countries} countries. Moving right now.">
<meta property="og:title" content="Jerome7 Live — {showed_up_today} showed up today">
<meta property="og:description" content="{total_users} builders across {num_countries} countries. {total_minutes} minutes of movement.">
<meta property="og:url" content="https://jerome7.com/live">
<meta name="twitter:card" content="summary">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0d1117; color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    min-height: 100vh;
  }}
  .container {{ max-width: 720px; margin: 0 auto; padding: 40px 20px; }}

  /* Nav */
  .nav {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 60px;
  }}
  .brand {{ font-size: 11px; letter-spacing: 3px; color: #E85D04; text-decoration: none; font-weight: 700; }}
  .nav-links {{ display: flex; gap: 20px; }}
  .nav-links a {{ font-size: 11px; color: #484f58; text-decoration: none; letter-spacing: 1px; }}
  .nav-links a:hover {{ color: #E85D04; }}

  /* Hero counter */
  .hero {{ text-align: center; margin-bottom: 64px; }}
  .hero-number {{
    font-size: 96px; font-weight: 800; color: #f0f6fc;
    line-height: 1; letter-spacing: -4px;
  }}
  .hero-label {{
    font-size: 13px; color: #8b949e; margin-top: 8px;
    letter-spacing: 2px;
  }}
  .hero-sub {{
    font-size: 11px; color: #30363d; margin-top: 24px;
    letter-spacing: 1px;
  }}
  .live-badge {{
    display: inline-flex; align-items: center; gap: 6px;
    background: #161b22; border: 1px solid #21262d;
    border-radius: 100px; padding: 6px 16px;
    font-size: 10px; letter-spacing: 2px; color: #3fb950;
    margin-top: 20px;
  }}
  .live-dot {{
    width: 8px; height: 8px; border-radius: 50%;
    background: #3fb950;
    animation: pulse 2s infinite;
  }}
  @keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.3; }}
  }}

  /* Stats row */
  .stats-row {{
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 16px; margin-bottom: 48px;
  }}
  @media (max-width: 640px) {{ .stats-row {{ grid-template-columns: repeat(2, 1fr); }} }}
  .stat {{
    background: #161b22; border: 1px solid #21262d;
    border-radius: 8px; padding: 16px; text-align: center;
  }}
  .stat-val {{ font-size: 24px; font-weight: 800; color: #f0f6fc; }}
  .stat-val.orange {{ color: #E85D04; }}
  .stat-val.green {{ color: #3fb950; }}
  .stat-label {{ font-size: 9px; color: #484f58; margin-top: 4px; letter-spacing: 1px; }}

  /* Globe */
  .globe-section {{
    margin-bottom: 48px; text-align: center;
  }}
  .section-label {{
    font-size: 10px; letter-spacing: 3px; color: #E85D04;
    margin-bottom: 16px; text-transform: uppercase;
  }}
  .globe-dots {{
    display: flex; flex-wrap: wrap; justify-content: center;
    gap: 12px; padding: 16px;
    background: #161b22; border: 1px solid #21262d; border-radius: 8px;
  }}
  .globe-dot {{
    font-size: 14px; color: #8b949e;
    background: #0d1117; border: 1px solid #21262d;
    border-radius: 100px; padding: 4px 12px;
  }}

  /* Longest streak */
  .longest {{
    text-align: center; margin-bottom: 48px;
    background: #161b22; border: 1px solid #21262d;
    border-radius: 8px; padding: 24px;
  }}
  .longest-val {{ font-size: 48px; font-weight: 800; color: #E85D04; }}
  .longest-name {{ font-size: 12px; color: #8b949e; margin-top: 4px; }}

  /* Feed */
  .feed {{
    background: #161b22; border: 1px solid #21262d;
    border-radius: 8px; overflow: hidden;
  }}
  .feed-header {{
    padding: 16px 20px; border-bottom: 1px solid #21262d;
    font-size: 10px; letter-spacing: 3px; color: #E85D04;
  }}
  .feed-item {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 12px 20px; border-bottom: 1px solid #161b22;
  }}
  .feed-item:nth-child(odd) {{ background: #0d1117; }}
  .feed-left {{ display: flex; align-items: center; gap: 10px; }}
  .feed-flag {{ font-size: 16px; }}
  .feed-name {{ font-size: 12px; color: #f0f6fc; font-weight: 600; }}
  .feed-streak {{ font-size: 10px; color: #E85D04; }}
  .feed-time {{ font-size: 10px; color: #30363d; }}

  /* CTA */
  .cta {{
    text-align: center; margin-top: 48px; padding: 32px;
    background: #161b22; border: 1px solid #21262d; border-radius: 8px;
  }}
  .cta-text {{ font-size: 14px; color: #8b949e; margin-bottom: 16px; }}
  .cta-btn {{
    display: inline-block; padding: 12px 32px;
    background: #E85D04; color: #fff; font-weight: 700;
    font-size: 12px; letter-spacing: 2px; text-decoration: none;
    border-radius: 6px;
  }}
  .cta-btn:hover {{ background: #c24e03; }}
  .cta-sub {{ font-size: 10px; color: #30363d; margin-top: 12px; }}

  .footer {{
    text-align: center; margin-top: 40px; padding: 20px;
    font-size: 10px; color: #21262d;
  }}
  .footer a {{ color: #484f58; text-decoration: none; }}
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
      <a href="/agents">AGENTS</a>
    </div>
  </nav>

  <!-- Hero: showed up today -->
  <div class="hero">
    <div class="hero-number">{showed_up_today}</div>
    <div class="hero-label">SHOWED UP TODAY</div>
    <div class="hero-sub">{total_users} builders · {num_countries} countries · {total_minutes:,} minutes moved</div>
    <div class="live-badge">
      <div class="live-dot"></div>
      LIVE
    </div>
  </div>

  <!-- Stats -->
  <div class="stats-row">
    <div class="stat">
      <div class="stat-val orange">{total_users}</div>
      <div class="stat-label">BUILDERS</div>
    </div>
    <div class="stat">
      <div class="stat-val green">{active_streaks}</div>
      <div class="stat-label">ACTIVE STREAKS</div>
    </div>
    <div class="stat">
      <div class="stat-val">{total_sessions}</div>
      <div class="stat-label">TOTAL SESSIONS</div>
    </div>
    <div class="stat">
      <div class="stat-val">{num_countries}</div>
      <div class="stat-label">COUNTRIES</div>
    </div>
  </div>

  <!-- Globe -->
  <div class="globe-section">
    <div class="section-label">WHERE THEY'RE SHOWING UP</div>
    <div class="globe-dots">
      {country_dots if country_dots else '<span style="color:#484f58">Waiting for the first pledge...</span>'}
    </div>
  </div>

  <!-- Longest streak -->
  {"" if not longest_val else f'''
  <div class="longest">
    <div class="section-label">LONGEST ACTIVE STREAK</div>
    <div class="longest-val">{longest_val}</div>
    <div class="longest-name">{longest_name}</div>
  </div>
  '''}

  <!-- Live feed -->
  <div class="feed">
    <div class="feed-header">SHOWING UP NOW</div>
    {feed_items if feed_items else '<div style="padding:20px;color:#484f58;font-size:12px;text-align:center">No sessions yet. Be the first.</div>'}
  </div>

  <!-- CTA -->
  <div class="cta">
    <div class="cta-text">7 minutes. Same session for everyone on earth. Every day.</div>
    <a href="/timer" class="cta-btn">START TODAY'S SESSION</a>
    <div class="cta-sub">Free forever. Open source. No account needed.</div>
  </div>

  <div class="footer">
    <a href="/">jerome7.com</a> · <a href="/analytics">analytics</a> · <a href="https://github.com/odominguez7/Jerome7">github</a>
  </div>

</div>
<script>setTimeout(() => location.reload(), 30000);</script>
</body>
</html>"""
    return HTMLResponse(content=html)


def _time_ago(delta: timedelta) -> str:
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        m = seconds // 60
        return f"{m}m ago"
    if seconds < 86400:
        h = seconds // 3600
        return f"{h}h ago"
    d = seconds // 86400
    return f"{d}d ago"
