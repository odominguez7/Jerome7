"""GET /report — Weekly World Report for Jerome7 viral distribution."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import (
    User, Streak, Session as SessionModel, SessionFeedback,
)

router = APIRouter()


def _week_bounds() -> tuple[datetime, datetime]:
    """Return (start_of_week_monday, now) for the current ISO week."""
    now = datetime.now(timezone.utc)
    monday = now - timedelta(days=now.weekday())
    start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, now


def _country_flag(country_code: str | None) -> str:
    """Turn a 2-letter ISO country code into a flag emoji."""
    if not country_code or len(country_code) != 2:
        return "\U0001f30d"
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in country_code.upper())


def _build_report_data(db: DBSession) -> dict:
    """Compute all world report stats for the current week."""
    start, now = _week_bounds()
    week_label = start.strftime("%b %d, %Y")

    # ── Core counts ──────────────────────────────────────────────────────
    sessions_this_week = (
        db.query(SessionModel)
        .filter(SessionModel.logged_at >= start)
        .count()
    )

    unique_builders = (
        db.query(func.count(func.distinct(SessionModel.user_id)))
        .filter(SessionModel.logged_at >= start)
        .scalar()
    ) or 0

    countries_rows = (
        db.query(User.country, func.count(func.distinct(User.id)))
        .join(SessionModel, SessionModel.user_id == User.id)
        .filter(SessionModel.logged_at >= start, User.country.isnot(None))
        .group_by(User.country)
        .all()
    )
    countries_count = len(countries_rows)
    country_list = [
        {"code": c, "flag": _country_flag(c), "builders": n}
        for c, n in countries_rows
    ]

    # ── Difficulty feedback ──────────────────────────────────────────────
    hardest = (
        db.query(
            SessionFeedback.session_date,
            func.avg(SessionFeedback.difficulty_rating).label("avg_diff"),
        )
        .filter(SessionFeedback.created_at >= start)
        .group_by(SessionFeedback.session_date)
        .order_by(func.avg(SessionFeedback.difficulty_rating).desc())
        .first()
    )
    easiest = (
        db.query(
            SessionFeedback.session_date,
            func.avg(SessionFeedback.difficulty_rating).label("avg_diff"),
        )
        .filter(SessionFeedback.created_at >= start)
        .group_by(SessionFeedback.session_date)
        .order_by(func.avg(SessionFeedback.difficulty_rating).asc())
        .first()
    )

    avg_difficulty = (
        db.query(func.avg(SessionFeedback.difficulty_rating))
        .filter(SessionFeedback.created_at >= start)
        .scalar()
    )

    # ── Streaks ──────────────────────────────────────────────────────────
    longest_chain = (
        db.query(Streak.user_id, Streak.current_streak, User.name)
        .join(User, User.id == Streak.user_id)
        .order_by(Streak.current_streak.desc())
        .first()
    )

    # Chains that broke this week (streak_broken_count went up — approximate
    # by counting users whose last_session_date is before this week and
    # current_streak == 0)
    chains_broken = (
        db.query(Streak)
        .filter(
            Streak.current_streak == 0,
            Streak.last_session_date >= start.date() if start else True,
        )
        .count()
    )
    chains_survived = (
        db.query(Streak)
        .filter(Streak.current_streak > 0)
        .count()
    )

    # Most improved: biggest streak gain this week (users who logged this
    # week, ranked by current_streak descending minus what it would have
    # been without this week's sessions — approximated by sessions this week)
    most_improved_row = (
        db.query(
            User.name,
            Streak.current_streak,
            func.count(SessionModel.id).label("week_sessions"),
        )
        .join(Streak, Streak.user_id == User.id)
        .join(SessionModel, SessionModel.user_id == User.id)
        .filter(SessionModel.logged_at >= start)
        .group_by(User.id, User.name, Streak.current_streak)
        .order_by(func.count(SessionModel.id).desc())
        .first()
    )

    # ── Early birds (sessions before 6am local — approximate via UTC) ────
    early_birds = (
        db.query(func.count(SessionModel.id))
        .filter(
            SessionModel.logged_at >= start,
            func.extract("hour", SessionModel.logged_at) < 6,
        )
        .scalar()
    ) or 0

    # ── New countries this week (users created this week with new countries)
    all_countries_before = set(
        c
        for (c,) in db.query(User.country)
        .filter(User.country.isnot(None), User.created_at < start)
        .distinct()
        .all()
    )
    countries_this_week = set(
        c
        for (c,) in db.query(User.country)
        .filter(User.country.isnot(None), User.created_at >= start)
        .distinct()
        .all()
    )
    new_countries = countries_this_week - all_countries_before

    return {
        "week_of": week_label,
        "generated_at": now.isoformat(),
        "sessions_this_week": sessions_this_week,
        "unique_builders": unique_builders,
        "countries_count": countries_count,
        "countries": country_list,
        "hardest_day": {
            "date": str(hardest[0]) if hardest else None,
            "avg_difficulty": round(hardest[1], 1) if hardest else None,
        },
        "easiest_day": {
            "date": str(easiest[0]) if easiest else None,
            "avg_difficulty": round(easiest[1], 1) if easiest else None,
        },
        "avg_difficulty": round(avg_difficulty, 1) if avg_difficulty else None,
        "longest_chain": {
            "name": longest_chain[2] if longest_chain else None,
            "days": longest_chain[1] if longest_chain else 0,
        },
        "most_improved": {
            "name": most_improved_row[0] if most_improved_row else None,
            "streak": most_improved_row[1] if most_improved_row else 0,
            "sessions_this_week": most_improved_row[2] if most_improved_row else 0,
        },
        "chains_broken": chains_broken,
        "chains_survived": chains_survived,
        "highlights": {
            "early_birds": early_birds,
            "avg_difficulty": round(avg_difficulty, 1) if avg_difficulty else None,
            "new_countries": [
                {"code": c, "flag": _country_flag(c)} for c in sorted(new_countries)
            ],
        },
    }


# ── JSON endpoint ────────────────────────────────────────────────────────────

@router.get("/report/data")
def report_data(db: DBSession = Depends(get_db)):
    """JSON payload of this week's world report."""
    try:
        return _build_report_data(db)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── HTML page ────────────────────────────────────────────────────────────────

@router.get("/report", response_class=HTMLResponse)
def report_page(db: DBSession = Depends(get_db)):
    """Beautiful dark-themed HTML world report with OG meta tags."""
    try:
        d = _build_report_data(db)
    except Exception:
        d = {
            "week_of": "—", "sessions_this_week": 0, "unique_builders": 0,
            "countries_count": 0, "countries": [], "hardest_day": {},
            "easiest_day": {}, "avg_difficulty": None,
            "longest_chain": {"name": None, "days": 0},
            "most_improved": {"name": None, "streak": 0, "sessions_this_week": 0},
            "chains_broken": 0, "chains_survived": 0,
            "highlights": {"early_birds": 0, "avg_difficulty": None, "new_countries": []},
        }

    og_desc = (
        f"{d['unique_builders']} builders. {d['countries_count']} countries. "
        f"{d['sessions_this_week']} sessions. The chain continues."
    )

    # Country flags HTML
    flags_html = " ".join(c["flag"] for c in d.get("countries", []))

    new_countries_html = ""
    nc = d["highlights"].get("new_countries", [])
    if nc:
        flags = " ".join(c["flag"] for c in nc)
        new_countries_html = f"""
        <div class="highlight">
            <span class="hl-icon">\U0001f30d</span>
            <span>{len(nc)} new country{"" if len(nc)==1 else "ies"} joined: {flags}</span>
        </div>"""

    avg_diff_html = ""
    if d["highlights"].get("avg_difficulty"):
        avg_diff_html = f"""
        <div class="highlight">
            <span class="hl-icon">\U0001f4ca</span>
            <span>Average session difficulty: {d['highlights']['avg_difficulty']}/5</span>
        </div>"""

    early_html = ""
    if d["highlights"].get("early_birds", 0) > 0:
        early_html = f"""
        <div class="highlight">
            <span class="hl-icon">\u2600\ufe0f</span>
            <span>{d['highlights']['early_birds']} builder{"" if d['highlights']['early_birds']==1 else "s"} showed up before 6am UTC</span>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jerome7 World Report — Week of {d['week_of']}</title>
<meta name="robots" content="noindex, nofollow">
<meta property="og:title" content="Jerome7 World Report — Week of {d['week_of']}">
<meta property="og:description" content="{og_desc}">
<meta property="og:type" content="website">
<meta property="og:url" content="https://jerome7.com/report">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Jerome7 World Report — Week of {d['week_of']}">
<meta name="twitter:description" content="{og_desc}">
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0d1117; color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace; line-height: 1.6;
  }}
  .container {{ max-width: 640px; margin: 0 auto; padding: 60px 20px 80px; }}

  .label {{
    font-size: 10px; letter-spacing: 3px; color: #E85D04;
    margin-bottom: 8px;
  }}
  h1 {{
    font-size: clamp(24px, 6vw, 40px); font-weight: 800;
    color: #f0f6fc; margin-bottom: 4px;
  }}
  h1 span {{ color: #E85D04; }}
  .subtitle {{ font-size: 13px; color: #484f58; margin-bottom: 48px; }}

  /* stat grid */
  .stats {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 16px; margin-bottom: 48px;
  }}
  .stat {{
    background: #161b22; border: 1px solid #21262d; border-radius: 12px;
    padding: 20px; text-align: center;
  }}
  .stat-value {{
    font-size: 32px; font-weight: 800; color: #E85D04;
  }}
  .stat-label {{ font-size: 11px; color: #8b949e; margin-top: 4px; }}

  /* sections */
  .section {{ margin-bottom: 40px; }}
  .section h2 {{
    font-size: 16px; font-weight: 700; color: #f0f6fc;
    margin-bottom: 16px; display: flex; align-items: center; gap: 8px;
  }}
  .section h2 .emoji {{ font-size: 20px; }}

  .detail-row {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 12px 16px; background: #161b22; border: 1px solid #21262d;
    border-radius: 8px; margin-bottom: 8px;
  }}
  .detail-label {{ font-size: 13px; color: #8b949e; }}
  .detail-value {{ font-size: 14px; color: #f0f6fc; font-weight: 700; }}

  /* highlights */
  .highlights {{ margin-bottom: 40px; }}
  .highlight {{
    display: flex; align-items: center; gap: 10px;
    padding: 12px 16px; background: #161b22; border: 1px solid #21262d;
    border-radius: 8px; margin-bottom: 8px; font-size: 13px; color: #c9d1d9;
  }}
  .hl-icon {{ font-size: 18px; min-width: 24px; text-align: center; }}

  /* flags bar */
  .flags {{ font-size: 20px; letter-spacing: 4px; margin-bottom: 48px; }}

  /* footer */
  .footer {{
    text-align: center; padding-top: 40px; border-top: 1px solid #21262d;
  }}
  .footer-brand {{ font-size: 11px; letter-spacing: 3px; color: #E85D04; margin-bottom: 8px; }}
  .footer-text {{ font-size: 12px; color: #484f58; }}
  .footer a {{ color: #E85D04; text-decoration: none; }}
  .cta {{
    display: inline-block; margin-top: 24px; padding: 14px 40px;
    background: #E85D04; color: #fff; border-radius: 100px;
    font-family: inherit; font-size: 14px; font-weight: 700;
    text-decoration: none; letter-spacing: 1px;
  }}
  .cta:hover {{ background: #ff6b1a; }}

  @media (max-width: 480px) {{
    .container {{ padding: 40px 16px 60px; }}
    .stats {{ grid-template-columns: 1fr 1fr; }}
  }}
</style>
</head>
<body>
<div class="container">
  <div class="label">WORLD REPORT</div>
  <h1>Week of <span>{d['week_of']}</span></h1>
  <div class="subtitle">Global stats for the Jerome7 community</div>

  <!-- Big numbers -->
  <div class="stats">
    <div class="stat">
      <div class="stat-value">{d['sessions_this_week']}</div>
      <div class="stat-label">SESSIONS</div>
    </div>
    <div class="stat">
      <div class="stat-value">{d['unique_builders']}</div>
      <div class="stat-label">BUILDERS</div>
    </div>
    <div class="stat">
      <div class="stat-value">{d['countries_count']}</div>
      <div class="stat-label">COUNTRIES</div>
    </div>
    <div class="stat">
      <div class="stat-value">{d['longest_chain']['days']}</div>
      <div class="stat-label">LONGEST CHAIN</div>
    </div>
  </div>

  <!-- Flags -->
  <div class="flags">{flags_html}</div>

  <!-- Streaks & Chains -->
  <div class="section">
    <h2><span class="emoji">\U0001f525</span> Streaks &amp; Chains</h2>
    <div class="detail-row">
      <span class="detail-label">Longest active chain</span>
      <span class="detail-value">{d['longest_chain']['name'] or '—'} — {d['longest_chain']['days']}d</span>
    </div>
    <div class="detail-row">
      <span class="detail-label">Most improved builder</span>
      <span class="detail-value">{d['most_improved']['name'] or '—'} (+{d['most_improved']['sessions_this_week']} sessions)</span>
    </div>
    <div class="detail-row">
      <span class="detail-label">Chains survived</span>
      <span class="detail-value" style="color:#7ee787">{d['chains_survived']}</span>
    </div>
    <div class="detail-row">
      <span class="detail-label">Chains broken</span>
      <span class="detail-value" style="color:#f85149">{d['chains_broken']}</span>
    </div>
  </div>

  <!-- Difficulty -->
  <div class="section">
    <h2><span class="emoji">\U0001f4aa</span> Difficulty</h2>
    <div class="detail-row">
      <span class="detail-label">Hardest day</span>
      <span class="detail-value">{d['hardest_day'].get('date') or '—'} ({d['hardest_day'].get('avg_difficulty') or '—'}/5)</span>
    </div>
    <div class="detail-row">
      <span class="detail-label">Easiest day</span>
      <span class="detail-value">{d['easiest_day'].get('date') or '—'} ({d['easiest_day'].get('avg_difficulty') or '—'}/5)</span>
    </div>
  </div>

  <!-- Highlights -->
  <div class="highlights">
    <h2 style="font-size:16px;font-weight:700;color:#f0f6fc;margin-bottom:16px;display:flex;align-items:center;gap:8px;">
      <span class="emoji">\u2728</span> Highlights
    </h2>
    {early_html}
    {avg_diff_html}
    {new_countries_html}
  </div>

  <!-- Footer -->
  <div class="footer">
    <div class="footer-brand">JEROME7</div>
    <div class="footer-text">Personally funded by the founder. Open source. Built at MIT.</div>
    <div class="footer-text" style="margin-top:8px;">
      <a href="/">Home</a> · <a href="/timer">Timer</a> ·
      <a href="/leaderboard">Leaderboard</a> ·
      <a href="https://github.com/odominguez7/Jerome7">GitHub</a>
    </div>
    <a href="/timer" class="cta">SHOW UP TODAY</a>
  </div>
</div>
</body>
</html>"""
    return HTMLResponse(content=html)
