"""GET /leaderboard — who's showing up. Global feed. Live streaks."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import User, Streak, Session as SessionModel

router = APIRouter()
logger = logging.getLogger(__name__)

# Timezone prefix → flag emoji + country name
TZ_FLAGS = {
    "America/New_York": ("🇺🇸", "USA"),
    "America/Chicago": ("🇺🇸", "USA"),
    "America/Denver": ("🇺🇸", "USA"),
    "America/Los_Angeles": ("🇺🇸", "USA"),
    "America/Phoenix": ("🇺🇸", "USA"),
    "America/Anchorage": ("🇺🇸", "USA"),
    "America/Honolulu": ("🇺🇸", "USA"),
    "America/Toronto": ("🇨🇦", "Canada"),
    "America/Vancouver": ("🇨🇦", "Canada"),
    "America/Montreal": ("🇨🇦", "Canada"),
    "America/Mexico_City": ("🇲🇽", "Mexico"),
    "America/Sao_Paulo": ("🇧🇷", "Brazil"),
    "America/Buenos_Aires": ("🇦🇷", "Argentina"),
    "America/Bogota": ("🇨🇴", "Colombia"),
    "America/Lima": ("🇵🇪", "Peru"),
    "America/Santiago": ("🇨🇱", "Chile"),
    "America/Caracas": ("🇻🇪", "Venezuela"),
    "Europe/London": ("🇬🇧", "UK"),
    "Europe/Paris": ("🇫🇷", "France"),
    "Europe/Berlin": ("🇩🇪", "Germany"),
    "Europe/Madrid": ("🇪🇸", "Spain"),
    "Europe/Rome": ("🇮🇹", "Italy"),
    "Europe/Amsterdam": ("🇳🇱", "Netherlands"),
    "Europe/Stockholm": ("🇸🇪", "Sweden"),
    "Europe/Oslo": ("🇳🇴", "Norway"),
    "Europe/Copenhagen": ("🇩🇰", "Denmark"),
    "Europe/Helsinki": ("🇫🇮", "Finland"),
    "Europe/Warsaw": ("🇵🇱", "Poland"),
    "Europe/Prague": ("🇨🇿", "Czech Republic"),
    "Europe/Vienna": ("🇦🇹", "Austria"),
    "Europe/Zurich": ("🇨🇭", "Switzerland"),
    "Europe/Brussels": ("🇧🇪", "Belgium"),
    "Europe/Lisbon": ("🇵🇹", "Portugal"),
    "Europe/Athens": ("🇬🇷", "Greece"),
    "Europe/Budapest": ("🇭🇺", "Hungary"),
    "Europe/Bucharest": ("🇷🇴", "Romania"),
    "Europe/Kiev": ("🇺🇦", "Ukraine"),
    "Europe/Moscow": ("🇷🇺", "Russia"),
    "Europe/Istanbul": ("🇹🇷", "Turkey"),
    "Asia/Tokyo": ("🇯🇵", "Japan"),
    "Asia/Seoul": ("🇰🇷", "South Korea"),
    "Asia/Shanghai": ("🇨🇳", "China"),
    "Asia/Hong_Kong": ("🇭🇰", "Hong Kong"),
    "Asia/Taipei": ("🇹🇼", "Taiwan"),
    "Asia/Singapore": ("🇸🇬", "Singapore"),
    "Asia/Bangkok": ("🇹🇭", "Thailand"),
    "Asia/Jakarta": ("🇮🇩", "Indonesia"),
    "Asia/Manila": ("🇵🇭", "Philippines"),
    "Asia/Kuala_Lumpur": ("🇲🇾", "Malaysia"),
    "Asia/Ho_Chi_Minh": ("🇻🇳", "Vietnam"),
    "Asia/Kolkata": ("🇮🇳", "India"),
    "Asia/Mumbai": ("🇮🇳", "India"),
    "Asia/Dhaka": ("🇧🇩", "Bangladesh"),
    "Asia/Karachi": ("🇵🇰", "Pakistan"),
    "Asia/Dubai": ("🇦🇪", "UAE"),
    "Asia/Riyadh": ("🇸🇦", "Saudi Arabia"),
    "Asia/Tehran": ("🇮🇷", "Iran"),
    "Asia/Jerusalem": ("🇮🇱", "Israel"),
    "Asia/Beirut": ("🇱🇧", "Lebanon"),
    "Asia/Almaty": ("🇰🇿", "Kazakhstan"),
    "Africa/Cairo": ("🇪🇬", "Egypt"),
    "Africa/Lagos": ("🇳🇬", "Nigeria"),
    "Africa/Nairobi": ("🇰🇪", "Kenya"),
    "Africa/Johannesburg": ("🇿🇦", "South Africa"),
    "Africa/Accra": ("🇬🇭", "Ghana"),
    "Africa/Casablanca": ("🇲🇦", "Morocco"),
    "Australia/Sydney": ("🇦🇺", "Australia"),
    "Australia/Melbourne": ("🇦🇺", "Australia"),
    "Australia/Brisbane": ("🇦🇺", "Australia"),
    "Australia/Perth": ("🇦🇺", "Australia"),
    "Pacific/Auckland": ("🇳🇿", "New Zealand"),
    "Pacific/Honolulu": ("🇺🇸", "USA"),
    "UTC": ("🌍", "Earth"),
}


def _get_flag(timezone: str) -> tuple[str, str]:
    """Return (flag_emoji, country_name) for a timezone."""
    if timezone in TZ_FLAGS:
        return TZ_FLAGS[timezone]
    # Try prefix match
    for tz, val in TZ_FLAGS.items():
        if timezone.startswith(tz.split("/")[0]):
            return val
    return ("🌍", "Earth")


def _time_ago(dt: datetime) -> str:
    """Human-readable time ago string."""
    if not dt:
        return ""
    diff = datetime.now(timezone.utc) - dt
    if diff.total_seconds() < 60:
        return "just now"
    elif diff.total_seconds() < 3600:
        m = int(diff.total_seconds() / 60)
        return f"{m}m ago"
    elif diff.total_seconds() < 86400:
        h = int(diff.total_seconds() / 3600)
        return f"{h}h ago"
    else:
        d = diff.days
        return f"{d}d ago"


@router.get("/leaderboard/data")
def leaderboard_data(db: DBSession = Depends(get_db)):
    """JSON endpoint for leaderboard data."""
    try:
        # Top streaks
        top_streaks = (
            db.query(Streak, User)
            .join(User, Streak.user_id == User.id)
            .filter(Streak.current_streak > 0)
            .order_by(Streak.current_streak.desc())
            .limit(20)
            .all()
        )

        # Recent sessions (last 48h)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        recent = (
            db.query(SessionModel, User)
            .join(User, SessionModel.user_id == User.id)
            .filter(SessionModel.logged_at >= cutoff)
            .order_by(SessionModel.logged_at.desc())
            .limit(30)
            .all()
        )

        # Today's count
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = (
            db.query(SessionModel)
            .filter(SessionModel.logged_at >= today_start)
            .count()
        )
    except Exception as e:
        logger.error(f"Leaderboard DB query failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Database query failed", "leaderboard": [], "feed": [], "today_count": 0},
        )

    # Country code → flag emoji for stored country codes
    _CODE_TO_FLAG = {
        "US": "\U0001f1fa\U0001f1f8", "CA": "\U0001f1e8\U0001f1e6", "MX": "\U0001f1f2\U0001f1fd", "BR": "\U0001f1e7\U0001f1f7", "AR": "\U0001f1e6\U0001f1f7",
        "CO": "\U0001f1e8\U0001f1f4", "PE": "\U0001f1f5\U0001f1ea", "CL": "\U0001f1e8\U0001f1f1", "GB": "\U0001f1ec\U0001f1e7", "FR": "\U0001f1eb\U0001f1f7",
        "DE": "\U0001f1e9\U0001f1ea", "ES": "\U0001f1ea\U0001f1f8", "IT": "\U0001f1ee\U0001f1f9", "NL": "\U0001f1f3\U0001f1f1", "SE": "\U0001f1f8\U0001f1ea",
        "NO": "\U0001f1f3\U0001f1f4", "CH": "\U0001f1e8\U0001f1ed", "IE": "\U0001f1ee\U0001f1ea", "PT": "\U0001f1f5\U0001f1f9", "PL": "\U0001f1f5\U0001f1f1",
        "TR": "\U0001f1f9\U0001f1f7", "RU": "\U0001f1f7\U0001f1fa", "JP": "\U0001f1ef\U0001f1f5", "KR": "\U0001f1f0\U0001f1f7", "CN": "\U0001f1e8\U0001f1f3",
        "HK": "\U0001f1ed\U0001f1f0", "SG": "\U0001f1f8\U0001f1ec", "IN": "\U0001f1ee\U0001f1f3", "AE": "\U0001f1e6\U0001f1ea", "SA": "\U0001f1f8\U0001f1e6",
        "ID": "\U0001f1ee\U0001f1e9", "TH": "\U0001f1f9\U0001f1ed", "PH": "\U0001f1f5\U0001f1ed", "AU": "\U0001f1e6\U0001f1fa", "NZ": "\U0001f1f3\U0001f1ff",
        "NG": "\U0001f1f3\U0001f1ec", "KE": "\U0001f1f0\U0001f1ea", "EG": "\U0001f1ea\U0001f1ec", "ZA": "\U0001f1ff\U0001f1e6",
    }

    def _resolve_flag_country(user):
        """Use stored country code if available, fall back to timezone."""
        if user.country and user.country in _CODE_TO_FLAG:
            return _CODE_TO_FLAG[user.country], user.country
        return _get_flag(user.timezone or "UTC")

    leaderboard = []
    for streak, user in top_streaks:
        flag, country = _resolve_flag_country(user)
        leaderboard.append({
            "name": user.name,
            "flag": flag,
            "country": country,
            "streak": streak.current_streak,
            "longest": streak.longest_streak,
            "total": streak.total_sessions,
        })

    feed = []
    for session, user in recent:
        flag, country = _resolve_flag_country(user)
        streak = db.query(Streak).filter(Streak.user_id == user.id).first()
        feed.append({
            "name": user.name,
            "flag": flag,
            "country": country,
            "streak": streak.current_streak if streak else 0,
            "time_ago": _time_ago(session.logged_at),
            "title": session.seven7_title or "the seven 7",
        })

    return {
        "leaderboard": leaderboard,
        "feed": feed,
        "today_count": today_count,
    }


@router.get("/leaderboard", response_class=HTMLResponse)
def leaderboard_page(db: DBSession = Depends(get_db)):
    data = leaderboard_data(db)
    if not isinstance(data, dict):
        # DB error — show empty page gracefully
        leaderboard, feed, today_count = [], [], 0
    else:
        leaderboard = data["leaderboard"]
        feed = data["feed"]
        today_count = data["today_count"]

    # Build leaderboard rows
    leaderboard_html = ""
    if leaderboard:
        for i, entry in enumerate(leaderboard):
            rank = i + 1
            rank_str = {1: "◉", 2: "◎", 3: "○"}.get(rank, str(rank))
            rank_color = {1: "#E85D04", 2: "#8b949e", 3: "#79c0ff"}.get(rank, "#484f58")
            leaderboard_html += f"""
            <div class="lb-row">
              <span class="lb-rank" style="color:{rank_color}">{rank_str}</span>
              <span class="lb-flag">{entry['flag']}</span>
              <span class="lb-name">{entry['name']}</span>
              <span class="lb-country">{entry['country']}</span>
              <span class="lb-streak">{entry['streak']}d</span>
            </div>"""
    else:
        leaderboard_html = '<div class="empty">No streaks yet. Be first.</div>'

    # Build feed rows
    feed_html = ""
    if feed:
        for entry in feed[:15]:
            feed_html += f"""
            <div class="feed-row">
              <span class="feed-flag">{entry['flag']}</span>
              <span class="feed-name">{entry['name']}</span>
              <span class="feed-streak">{entry['streak']}d</span>
              <span class="feed-time">{entry['time_ago']}</span>
            </div>"""
    else:
        feed_html = '<div class="empty">Quiet today. Be the first to show up.</div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jerome7 — Who's Showing Up</title>
<meta name="robots" content="noindex, nofollow">
<meta name="description" content="Builders showing up worldwide. Live leaderboard.">
<meta property="og:title" content="Jerome7 — Builders Showing Up Worldwide">
<meta property="og:description" content="{today_count} builders showed up today. 7 minutes. Same session. Every country.">
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0d1117; color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    min-height: 100vh; padding: 40px 20px;
  }}
  .container {{ max-width: 640px; margin: 0 auto; }}
  .nav {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 48px;
  }}
  .brand {{ font-size: 11px; letter-spacing: 3px; color: #E85D04; text-decoration: none; }}
  .nav-links {{ display: flex; gap: 16px; }}
  .nav-links a {{ font-size: 12px; color: #484f58; text-decoration: none; }}
  .nav-links a:hover {{ color: #E85D04; }}

  h1 {{ font-size: 28px; font-weight: 800; color: #f0f6fc; margin-bottom: 8px; }}
  .subtitle {{ font-size: 13px; color: #8b949e; margin-bottom: 48px; }}
  .today-count {{
    display: inline-block;
    background: #E85D04;
    color: #fff;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 4px 12px;
    border-radius: 100px;
    margin-bottom: 48px;
  }}

  .section-label {{
    font-size: 10px; letter-spacing: 3px; color: #E85D04;
    margin-bottom: 16px;
  }}

  /* Leaderboard */
  .lb-row {{
    display: flex; align-items: center; gap: 12px;
    padding: 12px 0; border-bottom: 1px solid #21262d;
  }}
  .lb-rank {{ font-size: 16px; font-weight: 800; min-width: 24px; }}
  .lb-flag {{ font-size: 20px; }}
  .lb-name {{ font-size: 14px; color: #f0f6fc; font-weight: 600; flex: 1; }}
  .lb-country {{ font-size: 11px; color: #484f58; }}
  .lb-streak {{ font-size: 14px; font-weight: 700; color: #E85D04; min-width: 40px; text-align: right; }}

  /* Feed */
  .feed-section {{ margin-top: 48px; }}
  .feed-row {{
    display: flex; align-items: center; gap: 12px;
    padding: 10px 0; border-bottom: 1px solid #21262d;
  }}
  .feed-flag {{ font-size: 18px; }}
  .feed-name {{ font-size: 13px; color: #f0f6fc; flex: 1; }}
  .feed-streak {{ font-size: 12px; color: #E85D04; font-weight: 700; min-width: 32px; }}
  .feed-time {{ font-size: 11px; color: #484f58; min-width: 60px; text-align: right; }}

  .empty {{ font-size: 13px; color: #484f58; padding: 24px 0; }}

  .back-link {{
    display: inline-block; margin-top: 48px;
    font-size: 12px; color: #484f58; text-decoration: none;
  }}
  .back-link:hover {{ color: #E85D04; }}

  .auto-refresh {{ font-size: 10px; color: #484f58; margin-top: 8px; }}
</style>
</head>
<body>
<div class="container">
  <div class="nav">
    <a href="/" class="brand">JEROME7</a>
    <div class="nav-links">
      <a href="https://discord.gg/5AZP8DbEJm">Discord</a>
      <a href="https://github.com/odominguez7/Jerome7">GitHub</a>
    </div>
  </div>

  <h1>Who's showing up.</h1>
  <div class="subtitle">Builders worldwide. 7 minutes. Every day.</div>
  <div class="today-count">{today_count} showed up today</div>

  <div class="section-label">TOP STREAKS</div>
  {leaderboard_html}

  <div class="feed-section">
    <div class="section-label">RECENT SESSIONS</div>
    {feed_html}
    <div class="auto-refresh">auto-refreshes every 60 seconds</div>
  </div>

  <a href="/" class="back-link">← back to jerome7.com</a>
</div>

<script>
  // Auto-refresh every 60 seconds
  setTimeout(() => window.location.reload(), 60000);
</script>
</body>
</html>"""
    return HTMLResponse(content=html)
