"""GET /milestones — achievement tracking and milestone detection for Jerome7."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import User, Session as SessionModel, Event

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Milestone thresholds ─────────────────────────────────────────────────────

USER_MILESTONES = [50, 100, 250, 500, 1000, 2500, 5000, 10000]
SESSION_MILESTONES = [100, 500, 1000, 5000, 10000, 50000]
COUNTRY_MILESTONES = [10, 25, 50, 75, 100]
STAR_MILESTONES = [10, 25, 50, 100, 250, 500, 1000]

GITHUB_REPO_API = "https://api.github.com/repos/odominguez7/Jerome7"


def _fetch_github_stars() -> int | None:
    """Fetch star count from GitHub API. Returns None on failure."""
    try:
        import httpx
        r = httpx.get(GITHUB_REPO_API, timeout=10)
        r.raise_for_status()
        return r.json().get("stargazers_count", 0)
    except Exception as e:
        logger.warning(f"GitHub API fetch failed: {e}")
        return None


def _already_fired(db: DBSession, milestone_type: str, value: int) -> bool:
    """Check if this specific milestone was already recorded as an Event."""
    return (
        db.query(Event)
        .filter(
            Event.event_type == "milestone",
            Event.payload["type"].as_string() == milestone_type,
            Event.payload["value"].as_integer() == value,
        )
        .first()
    ) is not None


def _already_fired_simple(db: DBSession, milestone_type: str, value: int) -> bool:
    """Fallback milestone check using LIKE on JSON payload (SQLite-safe)."""
    # Try exact JSON match via cast
    existing = (
        db.query(Event)
        .filter(
            Event.event_type == "milestone",
        )
        .all()
    )
    for ev in existing:
        if ev.payload and ev.payload.get("type") == milestone_type and ev.payload.get("value") == value:
            return True
    return False


def _record_milestone(db: DBSession, milestone_type: str, value: int, message: str):
    """Persist a milestone event so it doesn't fire again."""
    ev = Event(
        event_type="milestone",
        payload={"type": milestone_type, "value": value, "message": message},
    )
    db.add(ev)
    db.commit()


def _check_milestones(db: DBSession) -> list[dict]:
    """Detect any new milestones that haven't fired yet."""
    new_milestones: list[dict] = []

    # ── User count ───────────────────────────────────────────────────────
    total_users = db.query(User).count()
    for threshold in USER_MILESTONES:
        if total_users >= threshold and not _already_fired_simple(db, "users", threshold):
            msg = f"\U0001f525 {threshold} builders have joined Jerome7!"
            new_milestones.append({"type": "users", "value": threshold, "message": msg})
            _record_milestone(db, "users", threshold, msg)

    # ── Session count ────────────────────────────────────────────────────
    total_sessions = db.query(SessionModel).count()
    for threshold in SESSION_MILESTONES:
        if total_sessions >= threshold and not _already_fired_simple(db, "sessions", threshold):
            msg = f"\U0001f3cb\ufe0f {threshold} sessions completed worldwide!"
            new_milestones.append({"type": "sessions", "value": threshold, "message": msg})
            _record_milestone(db, "sessions", threshold, msg)

    # ── Country count ────────────────────────────────────────────────────
    countries_count = (
        db.query(func.count(func.distinct(User.country)))
        .filter(User.country.isnot(None))
        .scalar()
    ) or 0
    for threshold in COUNTRY_MILESTONES:
        if countries_count >= threshold and not _already_fired_simple(db, "countries", threshold):
            msg = f"\U0001f30d Jerome7 is in {threshold} countries!"
            new_milestones.append({"type": "countries", "value": threshold, "message": msg})
            _record_milestone(db, "countries", threshold, msg)

    # ── GitHub stars ─────────────────────────────────────────────────────
    stars = _fetch_github_stars()
    if stars is not None:
        for threshold in STAR_MILESTONES:
            if stars >= threshold and not _already_fired_simple(db, "stars", threshold):
                msg = f"\u2b50 {threshold} stars on GitHub!"
                new_milestones.append({"type": "stars", "value": threshold, "message": msg})
                _record_milestone(db, "stars", threshold, msg)

    return new_milestones


def _all_milestones(db: DBSession) -> list[dict]:
    """Return every milestone event ever recorded, newest first."""
    events = (
        db.query(Event)
        .filter(Event.event_type == "milestone")
        .order_by(Event.created_at.desc())
        .all()
    )
    return [
        {
            "type": ev.payload.get("type"),
            "value": ev.payload.get("value"),
            "message": ev.payload.get("message"),
            "date": ev.created_at.isoformat() if ev.created_at else None,
        }
        for ev in events
        if ev.payload
    ]


# ── JSON: check for new milestones ──────────────────────────────────────────

@router.get("/milestones/check")
def milestones_check(db: DBSession = Depends(get_db)):
    """Detect and return any newly-hit milestones since last check."""
    try:
        new = _check_milestones(db)
        return {"milestones": new}
    except Exception as e:
        logger.error(f"Milestone check failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ── HTML: full milestone timeline ────────────────────────────────────────────

@router.get("/milestones", response_class=HTMLResponse)
def milestones_page(db: DBSession = Depends(get_db)):
    """Visual timeline of every milestone Jerome7 has hit."""
    try:
        all_ms = _all_milestones(db)
    except Exception:
        all_ms = []

    # Build timeline HTML
    timeline_html = ""
    if all_ms:
        for m in all_ms:
            icon_map = {
                "users": "\U0001f525",
                "sessions": "\U0001f3cb\ufe0f",
                "countries": "\U0001f30d",
                "stars": "\u2b50",
            }
            icon = icon_map.get(m["type"], "\U0001f3af")
            date_str = ""
            if m.get("date"):
                try:
                    dt = datetime.fromisoformat(m["date"])
                    date_str = dt.strftime("%b %d, %Y")
                except Exception:
                    date_str = m["date"][:10]

            timeline_html += f"""
            <div class="ms-item">
              <div class="ms-icon">{icon}</div>
              <div class="ms-body">
                <div class="ms-msg">{m['message']}</div>
                <div class="ms-date">{date_str}</div>
              </div>
            </div>"""
    else:
        timeline_html = '<div class="ms-empty">No milestones yet. The journey is just beginning.</div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jerome7 — Milestones</title>
<meta property="og:title" content="Jerome7 Milestones">
<meta property="og:description" content="Every milestone the Jerome7 community has hit.">
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0d1117; color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace; line-height: 1.6;
  }}
  .container {{ max-width: 640px; margin: 0 auto; padding: 60px 20px 80px; }}

  .label {{ font-size: 10px; letter-spacing: 3px; color: #E85D04; margin-bottom: 8px; }}
  h1 {{ font-size: clamp(24px, 6vw, 40px); font-weight: 800; color: #f0f6fc; margin-bottom: 8px; }}
  h1 span {{ color: #E85D04; }}
  .subtitle {{ font-size: 13px; color: #484f58; margin-bottom: 48px; }}

  /* timeline */
  .timeline {{ position: relative; padding-left: 32px; }}
  .timeline::before {{
    content: ''; position: absolute; left: 11px; top: 0; bottom: 0;
    width: 2px; background: #21262d;
  }}

  .ms-item {{
    display: flex; align-items: flex-start; gap: 16px;
    margin-bottom: 24px; position: relative;
  }}
  .ms-icon {{
    font-size: 22px; min-width: 32px; text-align: center;
    position: relative; z-index: 1; background: #0d1117;
    padding: 4px 0; margin-left: -32px;
  }}
  .ms-body {{ flex: 1; }}
  .ms-msg {{
    font-size: 14px; color: #f0f6fc; font-weight: 600;
  }}
  .ms-date {{ font-size: 11px; color: #484f58; margin-top: 2px; }}
  .ms-empty {{ font-size: 14px; color: #484f58; padding: 24px 0; }}

  /* footer */
  .footer {{
    text-align: center; padding-top: 40px; border-top: 1px solid #21262d;
    margin-top: 40px;
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
</style>
</head>
<body>
<div class="container">
  <div class="label">ACHIEVEMENTS</div>
  <h1><span>Milestones</span></h1>
  <div class="subtitle">Every milestone the Jerome7 community has hit</div>

  <div class="timeline">
    {timeline_html}
  </div>

  <div class="footer">
    <div class="footer-brand">JEROME7</div>
    <div class="footer-text">
      <a href="/">Home</a> · <a href="/report">World Report</a> ·
      <a href="/leaderboard">Leaderboard</a> ·
      <a href="https://github.com/odominguez7/Jerome7">GitHub</a>
    </div>
    <a href="/timer" class="cta">SHOW UP TODAY</a>
  </div>
</div>
</body>
</html>"""
    return HTMLResponse(content=html)
